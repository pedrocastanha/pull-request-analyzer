#!/usr/bin/env python3
"""
PR Analyzer - Agent inteligente para análise de Pull Requests
Usando LangGraph + Claude + GitHub API
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
from dotenv import load_dotenv

# Adiciona o diretório src ao path
sys.path.append(str(Path(__file__).parent))

from agents.pr_analyzer import PRAnalyzerAgent
from models.pr_state import PRState, AnalysisStatus
from utils.config import Config
from utils.logger import setup_logger

# Configuração
load_dotenv()
app = typer.Typer(help="🤖 PR Analyzer - Agent inteligente para análise de Pull Requests")
console = Console()
logger = setup_logger()


def validate_env_vars():
    """Valida variáveis de ambiente necessárias"""
    required_vars = {
        "GITHUB_TOKEN": "Token do GitHub para acessar PRs",
        "ANTHROPIC_API_KEY": "Chave da API do Claude/Anthropic"
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"❌ {var}: {description}")

    if missing_vars:
        console.print("❌ [red]Variáveis de ambiente necessárias não encontradas:[/red]")
        for var in missing_vars:
            console.print(f"   {var}")
        console.print("\n💡 [yellow]Crie um arquivo .env com essas variáveis[/yellow]")
        raise typer.Exit(1)


@app.command()
def analyze(
        repo: str = typer.Argument(..., help="Repositório no formato 'owner/repo'"),
        pr_number: int = typer.Argument(..., help="Número do Pull Request"),
        output_format: str = typer.Option("rich", help="Formato de saída: rich, json, markdown"),
        save_report: bool = typer.Option(False, help="Salvar relatório em arquivo"),
        categories: str = typer.Option("all", help="Categorias a analisar: all, security, quality, performance, tests")
):
    """🔍 Analisa um Pull Request específico"""

    # Validações
    validate_env_vars()

    try:
        owner, repo_name = repo.split("/")
    except ValueError:
        console.print("❌ [red]Formato de repositório inválido. Use: owner/repo[/red]")
        raise typer.Exit(1)

    # Executa análise
    asyncio.run(run_analysis(owner, repo_name, pr_number, output_format, save_report))


async def run_analysis(
        owner: str,
        repo_name: str,
        pr_number: int,
        output_format: str,
        save_report: bool
):
    """Executa a análise do PR"""

    console.print(f"🚀 [bold blue]Iniciando análise do PR #{pr_number}[/bold blue]")
    console.print(f"📁 Repositório: {owner}/{repo_name}")

    # Cria o agent
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    analyzer = PRAnalyzerAgent(
        github_token=github_token,
        anthropic_api_key=anthropic_key
    )

    # Progress bar
    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
    ) as progress:
        task = progress.add_task("Analisando PR...", total=100)

        # Executa análise
        result = await analyzer.analyze_pr(owner, repo_name, pr_number)

        # Atualiza progress baseado no estado
        progress.update(task, completed=result.progress)

    # Exibe resultados
    display_results(result, output_format)

    # Salva relatório se solicitado
    if save_report:
        save_analysis_report(result, owner, repo_name, pr_number)


def display_results(state: PRState, format_type: str):
    """Exibe os resultados da análise"""

    if format_type == "json":
        console.print(JSON.from_data(state.dict()))
        return

    # Formato Rich (padrão)
    console.print("\n" + "=" * 80)
    console.print(f"📊 [bold green]RELATÓRIO DE ANÁLISE - PR #{state.pr_number}[/bold green]")
    console.print("=" * 80)

    # Informações básicas
    info_panel = Panel.fit(
        f"**Título:** {state.pr_title}\n"
        f"**Autor:** {state.pr_author}\n"
        f"**Status:** {state.status.value}\n"
        f"**Arquivos alterados:** {len(state.files_changed)}\n"
        f"**Adições:** {state.total_additions} | **Remoções:** {state.total_deletions}",
        title="ℹ️  Informações do PR",
        border_style="blue"
    )
    console.print(info_panel)

    # Score geral
    score_color = "green" if state.overall_score >= 7 else "yellow" if state.overall_score >= 5 else "red"
    score_panel = Panel.fit(
        f"[{score_color}]**{state.overall_score:.1f}/10**[/{score_color}]",
        title="🎯 Score Geral",
        border_style=score_color
    )
    console.print(score_panel)

    # Tabela de análises
    if state.analysis_results:
        table = Table(title="📈 Resultados por Categoria")
        table.add_column("Categoria", style="cyan")
        table.add_column("Score", justify="center")
        table.add_column("Issues", justify="center")
        table.add_column("Status", justify="center")

        for category, result in state.analysis_results.items():
            score_emoji = "🟢" if result.score >= 7 else "🟡" if result.score >= 5 else "🔴"
            table.add_row(
                category.title(),
                f"{result.score:.1f}/10",
                str(len(result.issues)),
                score_emoji
            )

        console.print(table)

    # Issues importantes
    if state.errors:
        console.print("\n❌ [red]**Erros encontrados:**[/red]")
        for error in state.errors:
            console.print(f"   • {error}")

    # Log de execução (resumido)
    if state.execution_log:
        recent_logs = state.execution_log[-5:]  # Últimas 5 entradas
        logs_text = "\n".join(recent_logs)
        log_panel = Panel(
            logs_text,
            title="📝 Log de Execução (últimas entradas)",
            border_style="dim"
        )
        console.print(log_panel)

    # Recomendação final
    if state.overall_score >= 8:
        recommendation = "✅ [green]**APROVADO** - Excelente qualidade[/green]"
    elif state.overall_score >= 6:
        recommendation = "⚠️ [yellow]**APROVADO COM RESSALVAS** - Pequenos ajustes recomendados[/yellow]"
    else:
        recommendation = "❌ [red]**NECESSITA REVISÃO** - Issues importantes encontrados[/red]"

    console.print(f"\n🎯 **Recomendação:** {recommendation}")


def save_analysis_report(state: PRState, owner: str, repo_name: str, pr_number: int):
    """Salva o relatório em arquivo"""

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Nome do arquivo
    timestamp = state.created_at.strftime("%Y%m%d_%H%M%S")
    filename = f"pr_analysis_{owner}_{repo_name}_{pr_number}_{timestamp}.json"
    filepath = reports_dir / filename

    # Salva como JSON
    with open(filepath, "w", encoding="utf-8") as f:
        import json
        json.dump(state.dict(), f, indent=2, ensure_ascii=False, default=str)

    console.print(f"💾 [green]Relatório salvo em:[/green] {filepath}")


@app.command()
def config():
    """⚙️ Configuração inicial do sistema"""

    console.print("🔧 [bold blue]Configuração do PR Analyzer[/bold blue]")

    # Verifica tokens
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    table = Table(title="Status das Configurações")
    table.add_column("Configuração", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Valor")

    # GitHub Token
    if github_token:
        masked_token = f"{github_token[:8]}...{github_token[-4:]}"
        table.add_row("GitHub Token", "✅", masked_token)
    else:
        table.add_row("GitHub Token", "❌", "Não configurado")

    # Anthropic Key
    if anthropic_key:
        masked_key = f"{anthropic_key[:8]}...{anthropic_key[-4:]}"
        table.add_row("Anthropic API Key", "✅", masked_key)
    else:
        table.add_row("Anthropic API Key", "❌", "Não configurado")

    console.print(table)

    # Instruções
    if not github_token or not anthropic_key:
        console.print("\n📝 [yellow]Para configurar, crie um arquivo .env:[/yellow]")
        console.print("""
GITHUB_TOKEN=ghp_seu_token_aqui
ANTHROPIC_API_KEY=sk-ant-seu_token_aqui
        """)


@app.command()
def test_connection():
    """🔌 Testa conexões com GitHub e Anthropic"""

    console.print("🧪 [bold blue]Testando conexões...[/bold blue]")

    validate_env_vars()

    # Testa GitHub
    try:
        from github import Github
        github = Github(os.getenv("GITHUB_TOKEN"))
        user = github.get_user()
        console.print(f"✅ GitHub: Conectado como {user.login}")
    except Exception as e:
        console.print(f"❌ GitHub: Erro - {str(e)}")

    # Testa Anthropic
    try:
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        response = llm.invoke("Teste de conexão")
        console.print("✅ Anthropic: Conectado")
    except Exception as e:
        console.print(f"❌ Anthropic: Erro - {str(e)}")


if __name__ == "__main__":
    app()
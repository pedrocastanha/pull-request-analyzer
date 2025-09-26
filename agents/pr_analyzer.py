import asyncio
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage

from ..models.pr_state import PRState, AnalysisStatus, AnalysisResult
from ..tools.github_tools import GitHubToolsManager


class PRAnalyzerAgent:
    """Agent principal para análise de Pull Requests usando LangGraph"""

    def __init__(self, github_token: str, anthropic_api_key: str):
        self.github_tools = GitHubToolsManager(github_token)
        self.llm = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            api_key=anthropic_api_key,
            temperature=0.1
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Constrói o grafo de estados do LangGraph"""

        workflow = StateGraph(PRState)

        # Define os nós do grafo
        workflow.add_node("collect_data", self._collect_pr_data)
        workflow.add_node("analyze_security", self._analyze_security)
        workflow.add_node("analyze_quality", self._analyze_code_quality)
        workflow.add_node("analyze_performance", self._analyze_performance)
        workflow.add_node("analyze_tests", self._analyze_tests)
        workflow.add_node("generate_summary", self._generate_summary)
        workflow.add_node("finalize", self._finalize_analysis)

        # Define o fluxo
        workflow.set_entry_point("collect_data")

        # Fluxo linear com verificações condicionais
        workflow.add_edge("collect_data", "analyze_security")
        workflow.add_edge("analyze_security", "analyze_quality")
        workflow.add_edge("analyze_quality", "analyze_performance")
        workflow.add_edge("analyze_performance", "analyze_tests")
        workflow.add_edge("analyze_tests", "generate_summary")
        workflow.add_edge("generate_summary", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _collect_pr_data(self, state: PRState) -> PRState:
        """Nó 1: Coleta dados básicos do PR"""
        state.update_progress("Coletando dados do GitHub", 10.0)

        try:
            state = await self.github_tools.collect_pr_data(state)
            state.status = AnalysisStatus.IN_PROGRESS
            state.update_progress("Dados coletados com sucesso", 20.0)

        except Exception as e:
            state.add_error(f"Falha na coleta de dados: {str(e)}")
            state.status = AnalysisStatus.FAILED

        return state

    async def _analyze_security(self, state: PRState) -> PRState:
        """Nó 2: Análise de segurança"""
        state.update_progress("Analisando segurança", 30.0)

        if not state.files_changed:
            state.log("Sem arquivos para análise de segurança")
            return state

        try:
            # Prepara contexto para o LLM
            security_prompt = self._build_security_prompt(state)

            # Chama o LLM
            response = await self.llm.ainvoke([HumanMessage(content=security_prompt)])

            # Processa resposta
            security_result = self._parse_security_analysis(response.content)
            state.analysis_results["security"] = security_result

            state.log(f"Análise de segurança concluída: {len(security_result.issues)} issues")
            state.update_progress("Segurança analisada", 40.0)

        except Exception as e:
            state.add_error(f"Erro na análise de segurança: {str(e)}")

        return state

    async def _analyze_code_quality(self, state: PRState) -> PRState:
        """Nó 3: Análise de qualidade de código"""
        state.update_progress("Analisando qualidade do código", 50.0)

        try:
            quality_prompt = self._build_quality_prompt(state)
            response = await self.llm.ainvoke([HumanMessage(content=quality_prompt)])

            quality_result = self._parse_quality_analysis(response.content)
            state.analysis_results["quality"] = quality_result

            state.log(f"Análise de qualidade concluída: score {quality_result.score}")
            state.update_progress("Qualidade analisada", 60.0)

        except Exception as e:
            state.add_error(f"Erro na análise de qualidade: {str(e)}")

        return state

    async def _analyze_performance(self, state: PRState) -> PRState:
        """Nó 4: Análise de performance"""
        state.update_progress("Analisando performance", 70.0)

        try:
            performance_prompt = self._build_performance_prompt(state)
            response = await self.llm.ainvoke([HumanMessage(content=performance_prompt)])

            performance_result = self._parse_performance_analysis(response.content)
            state.analysis_results["performance"] = performance_result

            state.log("Análise de performance concluída")
            state.update_progress("Performance analisada", 80.0)

        except Exception as e:
            state.add_error(f"Erro na análise de performance: {str(e)}")

        return state

    async def _analyze_tests(self, state: PRState) -> PRState:
        """Nó 5: Análise de testes"""
        state.update_progress("Analisando testes", 85.0)

        try:
            tests_prompt = self._build_tests_prompt(state)
            response = await self.llm.ainvoke([HumanMessage(content=tests_prompt)])

            tests_result = self._parse_tests_analysis(response.content)
            state.analysis_results["tests"] = tests_result

            # Estima cobertura de testes
            state.test_coverage_estimated = tests_result.score * 10  # Converte score para %

            state.log("Análise de testes concluída")
            state.update_progress("Testes analisados", 90.0)

        except Exception as e:
            state.add_error(f"Erro na análise de testes: {str(e)}")

        return state

    async def _generate_summary(self, state: PRState) -> PRState:
        """Nó 6: Gera resumo final"""
        state.update_progress("Gerando resumo final", 95.0)

        try:
            summary_prompt = self._build_summary_prompt(state)
            response = await self.llm.ainvoke([HumanMessage(content=summary_prompt)])

            # Calcula score geral
            scores = [result.score for result in state.analysis_results.values()]
            state.overall_score = sum(scores) / len(scores) if scores else 0.0

            state.log(f"Score geral: {state.overall_score:.1f}/10")

        except Exception as e:
            state.add_error(f"Erro ao gerar resumo: {str(e)}")

        return state

    async def _finalize_analysis(self, state: PRState) -> PRState:
        """Nó 7: Finaliza análise"""
        state.update_progress("Análise concluída", 100.0)
        state.status = AnalysisStatus.COMPLETED
        state.log("✅ Análise do PR concluída com sucesso!")

        return state

    def _build_security_prompt(self, state: PRState) -> str:
        """Constrói prompt para análise de segurança"""
        files_context = ""

        for file_change in state.files_changed[:10]:  # Limita a 10 arquivos
            if file_change.after_content:
                files_context += f"\n## Arquivo: {file_change.filename}\n"
                files_context += f"Status: {file_change.status}\n"
                files_context += f"```\n{file_change.after_content[:2000]}```\n"  # Limita conteúdo

        return f"""
Você é um especialista em segurança de aplicações. Analise as mudanças neste Pull Request:

**PR:** {state.pr_title}
**Repositório:** {state.repo_owner}/{state.repo_name}
**Arquivos alterados:** {len(state.files_changed)}

{files_context}

Por favor, identifique:
1. Vulnerabilidades de segurança
2. Problemas de validação de input
3. Exposição de dados sensíveis
4. Problemas de autenticação/autorização
5. Configurações inseguras

Para cada issue encontrado, forneça:
- Severidade (low, medium, high, critical)
- Descrição detalhada
- Localização (arquivo e linha se possível)
- Sugestão de correção

Responda em formato JSON estruturado.
"""

    def _build_quality_prompt(self, state: PRState) -> str:
        """Constrói prompt para análise de qualidade"""
        return f"""
Analise a qualidade do código neste PR:

**PR:** {state.pr_title}
**Arquivos:** {len(state.files_changed)} alterados

Avalie:
1. Legibilidade e clareza
2. Complexidade ciclomática
3. Duplicação de código
4. Aderência a padrões
5. Estrutura e organização
6. Documentação

Forneça um score de 0-10 e sugestões específicas de melhoria.
Responda em JSON estruturado.
"""

    def _build_performance_prompt(self, state: PRState) -> str:
        """Constrói prompt para análise de performance"""
        return f"""
Analise o impacto de performance deste PR:

**PR:** {state.pr_title}
**Mudanças:** +{state.total_additions}/-{state.total_deletions} linhas

Identifique:
1. Possíveis gargalos de performance
2. Uso ineficiente de recursos
3. Algoritmos sub-ótimos
4. Problemas de memória
5. I/O desnecessário

Score de 0-10 e sugestões de otimização.
Responda em JSON estruturado.
"""

    def _build_tests_prompt(self, state: PRState) -> str:
        """Constrói prompt para análise de testes"""
        test_files = [f for f in state.files_changed if 'test' in f.filename.lower()]

        return f"""
Analise a cobertura e qualidade dos testes neste PR:

**PR:** {state.pr_title}
**Arquivos de teste:** {len(test_files)} encontrados
**Total de arquivos:** {len(state.files_changed)}

Avalie:
1. Cobertura de código das mudanças
2. Qualidade dos casos de teste
3. Testes de edge cases
4. Testes de integração necessários
5. Mocks e fixtures adequados

Estime um score de cobertura de 0-10.
Responda em JSON estruturado.
"""

    def _build_summary_prompt(self, state: PRState) -> str:
        """Constrói prompt para resumo final"""
        results_summary = ""
        for category, result in state.analysis_results.items():
            results_summary += f"- {category.title()}: {result.score}/10 ({len(result.issues)} issues)\n"

        return f"""
Gere um resumo executivo desta análise de PR:

**PR:** {state.pr_title}
**Autor:** {state.pr_author}
**Análises realizadas:**
{results_summary}

**Erros encontrados:** {len(state.errors)}

Crie um resumo conciso destacando:
1. Principais pontos positivos
2. Issues críticos que precisam atenção
3. Recomendações prioritárias
4. Aprovação recomendada (sim/não/com ressalvas)

Mantenha o tom profissional e construtivo.
"""

    def _parse_security_analysis(self, content: str) -> AnalysisResult:
        """Parse da resposta de análise de segurança"""
        # Implementação simplificada - em produção, usar parser JSON robusto
        try:
            import json
            import re

            # Tenta extrair JSON da resposta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback para parsing baseado em texto
                data = {"score": 7.0, "issues": [], "summary": content[:200]}

            return AnalysisResult(
                category="security",
                score=data.get("score", 7.0),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                summary=data.get("summary", "Análise de segurança concluída")
            )
        except Exception:
            return AnalysisResult(
                category="security",
                score=5.0,
                summary="Erro no parsing da análise de segurança"
            )

    def _parse_quality_analysis(self, content: str) -> AnalysisResult:
        """Parse da resposta de análise de qualidade"""
        try:
            import json
            import re

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"score": 6.0, "issues": [], "summary": content[:200]}

            return AnalysisResult(
                category="quality",
                score=data.get("score", 6.0),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                summary=data.get("summary", "Análise de qualidade concluída")
            )
        except Exception:
            return AnalysisResult(
                category="quality",
                score=5.0,
                summary="Erro no parsing da análise de qualidade"
            )

    def _parse_performance_analysis(self, content: str) -> AnalysisResult:
        """Parse da resposta de análise de performance"""
        try:
            import json
            import re

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"score": 8.0, "issues": [], "summary": content[:200]}

            return AnalysisResult(
                category="performance",
                score=data.get("score", 8.0),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                summary=data.get("summary", "Análise de performance concluída")
            )
        except Exception:
            return AnalysisResult(
                category="performance",
                score=7.0,
                summary="Erro no parsing da análise de performance"
            )

    def _parse_tests_analysis(self, content: str) -> AnalysisResult:
        """Parse da resposta de análise de testes"""
        try:
            import json
            import re

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"score": 5.0, "issues": [], "summary": content[:200]}

            return AnalysisResult(
                category="tests",
                score=data.get("score", 5.0),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                summary=data.get("summary", "Análise de testes concluída")
            )
        except Exception:
            return AnalysisResult(
                category="tests",
                score=4.0,
                summary="Erro no parsing da análise de testes"
            )

    async def analyze_pr(self, repo_owner: str, repo_name: str, pr_number: int) -> PRState:
        """Método principal para analisar um PR"""
        # Cria estado inicial
        initial_state = PRState(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number
        )

        # Executa o grafo
        result = await self.graph.ainvoke(initial_state)

        return result
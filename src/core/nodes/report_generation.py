import logging
from typing import Dict

from src.core.states import HierarchicalPRAnalysisState

logger = logging.getLogger(__name__)


def generate_hierarchical_report(state: HierarchicalPRAnalysisState) -> Dict:
    logger.info("[NODE: report_generation] Generating hierarchical report")

    sections = []

    sections.append(_build_header())
    sections.append(_build_executive_summary(state))

    for module_analysis in state["module_analyses"]:
        sections.append(_build_module_section(module_analysis))

    sections.append(_build_recommendations(state))
    sections.append(_build_footer())

    report = "\n\n".join(sections)

    logger.info("[NODE: report_generation] ✓ Report generated")
    return {"final_report": report}


def _build_header() -> str:
    return """# 📊 Relatório de Análise Hierárquica de PR

> Análise por módulo com agents especializados"""


def _build_executive_summary(state: HierarchicalPRAnalysisState) -> str:
    total_files = len(state["all_files"])
    total_modules = len(state["modules"])

    security_count = 0
    logical_count = 0
    performance_count = 0
    clean_code_count = 0

    for module in state.get("module_analyses", []):
        security_count += len(module["security_analysis"].get("issues", []))
        logical_count += len(module["logical_analysis"].get("issues", []))
        performance_count += len(module["performance_analysis"].get("issues", []))
        clean_code_count += len(module["clean_code_analysis"].get("issues", []))

    total_issues = security_count + logical_count + performance_count + clean_code_count

    status_emoji = "🔴" if security_count > 0 else "🟡" if total_issues > 5 else "🟢"

    return f"""## {status_emoji} Executive Summary

        **Arquivos analisados:** {total_files}
        **Módulos analisados:** {total_modules}
        **Issues encontrados:** {total_issues}
        
        **Breakdown por Agent:**
        - 🔒 Security: {security_count} issues
        - 🧠 Logical: {logical_count} issues
        - ⚡ Performance: {performance_count} issues
        - 🎨 Clean Code: {clean_code_count} issues
        
        **Status:** {"❌ CRÍTICO - Vulnerabilidades de segurança encontradas" if security_count > 0 else "⚠️ Atenção necessária" if total_issues > 10 else "✅ Sem problemas graves"}"""


def _build_module_section(module_analysis) -> str:
    module_name = module_analysis["module_name"]
    files = module_analysis["files"]

    security = module_analysis["security_analysis"]
    logical = module_analysis["logical_analysis"]
    performance = module_analysis["performance_analysis"]
    clean_code = module_analysis["clean_code_analysis"]

    total_issues = (
        len(security.get("issues", []))
        + len(logical.get("issues", []))
        + len(performance.get("issues", []))
        + len(clean_code.get("issues", []))
    )

    icon = (
        "🔴"
        if len(security.get("issues", [])) > 0
        else "🟡" if total_issues > 3 else "🟢"
    )

    lines = [f"## {icon} Módulo: `{module_name}`", ""]
    lines.append(f"**Arquivos:** {len(files)}")
    lines.append(f"**Total de issues:** {total_issues}")
    lines.append("")

    lines.append("**Arquivos modificados:**")
    for file in files:
        lines.append(f"- `{file['path']}`")
    lines.append("")

    if security.get("issues"):
        lines.append("### 🔒 Security Issues")
        for i, issue in enumerate(security["issues"], 1):
            lines.append(
                f"{i}. **{issue.get('type', 'Security Issue')}** ({issue.get('severity', 'medium')})"
            )
            lines.append(
                f"   - File: `{issue.get('file', 'N/A')}:{issue.get('line', 'N/A')}`"
            )
            lines.append(f"   - {issue.get('description', 'No description')}")
            if issue.get("recommendation"):
                lines.append(f"   - 💡 **Fix:** {issue['recommendation']}")
        lines.append("")

    if logical.get("issues"):
        lines.append("### 🧠 Logical Issues")
        for i, issue in enumerate(logical["issues"], 1):
            lines.append(
                f"{i}. **{issue.get('type', 'Logical Issue')}** ({issue.get('severity', 'medium')})"
            )
            lines.append(
                f"   - File: `{issue.get('file', 'N/A')}:{issue.get('line', 'N/A')}`"
            )
            lines.append(f"   - {issue.get('description', 'No description')}")
            if issue.get("recommendation"):
                lines.append(f"   - 💡 **Fix:** {issue['recommendation']}")
        lines.append("")

    if performance.get("issues"):
        lines.append("### ⚡ Performance Issues")
        for i, issue in enumerate(performance["issues"], 1):
            lines.append(
                f"{i}. **{issue.get('type', 'Performance Issue')}** ({issue.get('severity', 'medium')})"
            )
            lines.append(
                f"   - File: `{issue.get('file', 'N/A')}:{issue.get('line', 'N/A')}`"
            )
            lines.append(f"   - {issue.get('description', 'No description')}")
            if issue.get("recommendation"):
                lines.append(f"   - 💡 **Fix:** {issue['recommendation']}")
        lines.append("")

    if clean_code.get("issues"):
        lines.append("### 🎨 Clean Code Issues")
        for i, issue in enumerate(clean_code["issues"], 1):
            lines.append(
                f"{i}. **{issue.get('type', 'Clean Code Issue')}** ({issue.get('severity', 'medium')})"
            )
            lines.append(
                f"   - File: `{issue.get('file', 'N/A')}:{issue.get('line', 'N/A')}`"
            )
            lines.append(f"   - {issue.get('description', 'No description')}")
            if issue.get("recommendation"):
                lines.append(f"   - 💡 **Fix:** {issue['recommendation']}")
        lines.append("")

    if total_issues == 0:
        lines.append("✅ _Nenhum problema detectado neste módulo._")
        lines.append("")

    return "\n".join(lines)


def _build_recommendations(state: HierarchicalPRAnalysisState) -> str:
    lines = ["## 💡 Recomendações", ""]

    total_security = sum(
        len(m["security_analysis"].get("issues", []))
        for m in state.get("module_analyses", [])
    )

    total_issues = sum(
        len(m["security_analysis"].get("issues", []))
        + len(m["logical_analysis"].get("issues", []))
        + len(m["performance_analysis"].get("issues", []))
        + len(m["clean_code_analysis"].get("issues", []))
        for m in state.get("module_analyses", [])
    )

    if total_security > 0:
        lines.append(
            "🚨 **PRIORIDADE ALTA:** Corrija vulnerabilidades de segurança antes do merge!"
        )
        lines.append("")

    if total_issues > 15:
        lines.append("⚠️ Grande número de issues detectados. Considere:")
        lines.append("- Revisar mudanças em lotes menores")
        lines.append("- Solicitar code review de outro desenvolvedor")
        lines.append("- Executar análise estática local antes de abrir PR")
        lines.append("")

    lines.append("**Próximos passos:**")
    lines.append("1. Priorizar correção de issues de segurança")
    lines.append("2. Revisar issues lógicos que podem causar bugs")
    lines.append("3. Otimizar performance onde necessário")
    lines.append("4. Melhorar qualidade do código gradualmente")

    return "\n".join(lines)


def _build_footer() -> str:
    return """---

_Relatório gerado por PR Analyzer - Análise Hierárquica por Módulo_"""

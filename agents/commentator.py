import logging
import json
import re
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from messages import CommentatorAgent
from settings import SharedSettings
from models.pr_state import PRState
from schemas import (
    CommentatorResult, ModuleAnalysisCommentary, ImprovementPlan, 
    CodeExample, ActionableRecommendation, LearningResource
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model=SharedSettings.GEMINI_MODEL,
    temperature=0.3,  # Temperatura um pouco mais alta para linguagem mais natural
    google_api_key=SharedSettings.GEMINI_API_KEY,
    convert_system_message_to_human=True
)

async def commentator_node(state: PRState) -> PRState:
    """Nó do agente comentador que traduz análises em linguagem clara"""
    logger.info("💬 Iniciando comentários e sugestões")
    state.update_progress("Gerando comentários", 85.0)
    
    if not state.analyzer_results:
        state.add_error("Nenhuma análise encontrada para comentar")
        return state
    
    try:
        # Constrói o contexto das análises
        analysis_context = build_analysis_context(state)
        
        # Constrói o prompt de comentário
        commentary_prompt = build_commentary_prompt(state, analysis_context)
        
        # Executa a geração de comentários
        messages = [HumanMessage(content=commentary_prompt)]
        response = await llm.ainvoke(messages)
        
        # Parse do resultado
        commentator_result = parse_commentator_response(response.content)
        state.commentator_result = commentator_result
        
        state.log("✅ Comentários gerados com sucesso")
        state.update_progress("Comentários finalizados", 95.0)
        
    except Exception as e:
        error_msg = f"Erro ao gerar comentários: {str(e)}"
        state.add_error(error_msg)
        logger.error(error_msg)
    
    return state

def build_analysis_context(state: PRState) -> str:
    """Constrói o contexto das análises para o comentador"""
    context = f"**PR: {state.pr_title}**\n"
    context += f"Repositório: {state.repo_owner}/{state.repo_name}\n"
    context += f"Arquivos modificados: {len(state.files_changed)}\n"
    context += f"Mudanças: +{state.total_additions}/-{state.total_deletions} linhas\n\n"
    
    # Adiciona informações dos módulos
    if state.separator_result:
        context += "**Módulos identificados:**\n"
        for module in state.separator_result.modules:
            context += f"- {module.name} ({module.type}): {', '.join(module.files)}\n"
        context += "\n"
    
    # Adiciona resultados das análises
    context += "**Análises realizadas:**\n"
    for i, analysis in enumerate(state.analyzer_results, 1):
        context += f"\n**Módulo {i}:**\n"
        context += f"- Score geral: {analysis.analysis.overall_score}/10\n"
        
        for category, cat_analysis in analysis.analysis.categories.items():
            context += f"- {category.title()}: {cat_analysis.score}/10\n"
            if cat_analysis.issues:
                context += f"  Problemas: {len(cat_analysis.issues)}\n"
            if cat_analysis.suggestions:
                context += f"  Sugestões: {len(cat_analysis.suggestions)}\n"
        
        if analysis.recommendations:
            context += f"- Recomendações: {len(analysis.recommendations)}\n"
            for rec in analysis.recommendations[:3]:  # Mostra apenas as 3 primeiras
                context += f"  • {rec.priority.upper()}: {rec.description[:100]}...\n"
    
    return context

def build_commentary_prompt(state: PRState, analysis_context: str) -> str:
    """Constrói o prompt para o comentador"""
    
    return f"""
Transforme esta análise técnica em comentários claros e acionáveis para desenvolvedores.

{analysis_context}

**Instruções:**
1. Traduza as análises técnicas em linguagem clara e didática
2. Forneça instruções passo-a-passo para correções
3. Explique o contexto e importância das melhorias
4. Priorize as ações por criticidade
5. Inclua exemplos de código quando relevante
6. Mantenha tom construtivo e educativo

**Foque em:**
- O que precisa ser corrigido e por quê
- Como corrigir passo a passo
- Benefícios de cada melhoria
- Recursos para aprender mais

Retorne APENAS um JSON válido seguindo a estrutura especificada no prompt do sistema.
"""

def parse_commentator_response(content: str) -> CommentatorResult:
    """Parse da resposta do agente comentador"""
    try:
        # Tenta extrair JSON da resposta
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            logger.warning("Não foi possível extrair JSON válido dos comentários")
            return create_fallback_commentary()
        
        # Parse do resumo executivo
        executive_summary = data.get("executive_summary", "Análise concluída com sucesso.")
        
        # Parse das análises dos módulos
        modules_analysis = []
        for module_data in data.get("modules_analysis", []):
            improvement_plan_data = module_data.get("improvement_plan", {})
            improvement_plan = ImprovementPlan(
                immediate_actions=improvement_plan_data.get("immediate_actions", []),
                short_term=improvement_plan_data.get("short_term", []),
                long_term=improvement_plan_data.get("long_term", [])
            )
            
            code_examples = None
            if "code_examples" in module_data:
                code_data = module_data["code_examples"]
                code_examples = CodeExample(
                    current=code_data.get("current", ""),
                    improved=code_data.get("improved", ""),
                    explanation=code_data.get("explanation", "")
                )
            
            module_analysis = ModuleAnalysisCommentary(
                module_name=module_data.get("module_name", "Módulo"),
                overall_health=module_data.get("overall_health", "needs_improvement"),
                key_issues=module_data.get("key_issues", []),
                improvement_plan=improvement_plan,
                code_examples=code_examples
            )
            modules_analysis.append(module_analysis)
        
        # Parse das recomendações acionáveis
        actionable_recommendations = []
        for rec_data in data.get("actionable_recommendations", []):
            recommendation = ActionableRecommendation(
                priority=rec_data.get("priority", "medium"),
                title=rec_data.get("title", "Recomendação"),
                description=rec_data.get("description", ""),
                steps=rec_data.get("steps", []),
                expected_benefit=rec_data.get("expected_benefit", ""),
                estimated_effort=rec_data.get("estimated_effort", "medium")
            )
            actionable_recommendations.append(recommendation)
        
        # Parse dos recursos de aprendizado
        learning_resources = []
        for resource_data in data.get("learning_resources", []):
            resource = LearningResource(
                topic=resource_data.get("topic", ""),
                resources=resource_data.get("resources", []),
                why_important=resource_data.get("why_important", "")
            )
            learning_resources.append(resource)
        
        return CommentatorResult(
            executive_summary=executive_summary,
            modules_analysis=modules_analysis,
            actionable_recommendations=actionable_recommendations,
            learning_resources=learning_resources
        )
        
    except Exception as e:
        logger.error(f"Erro ao fazer parse dos comentários: {e}")
        return create_fallback_commentary()

def create_fallback_commentary() -> CommentatorResult:
    """Cria comentários de fallback quando o parsing falha"""
    return CommentatorResult(
        executive_summary="Análise concluída. Recomenda-se revisar o código seguindo as melhores práticas de clean code.",
        modules_analysis=[
            ModuleAnalysisCommentary(
                module_name="Módulos Analisados",
                overall_health="needs_improvement",
                key_issues=["Revisão geral recomendada"],
                improvement_plan=ImprovementPlan(
                    immediate_actions=["Revisar código atual"],
                    short_term=["Implementar melhorias sugeridas"],
                    long_term=["Refatoração contínua"]
                )
            )
        ],
        actionable_recommendations=[
            ActionableRecommendation(
                priority="medium",
                title="Revisão Geral",
                description="Revisar o código seguindo as melhores práticas",
                steps=["1. Revisar estrutura do código", "2. Verificar padrões", "3. Implementar melhorias"],
                expected_benefit="Código mais limpo e maintível",
                estimated_effort="medium"
            )
        ],
        learning_resources=[
            LearningResource(
                topic="Clean Code",
                resources=["https://clean-code-developer.com/"],
                why_important="Fundamental para código maintível"
            )
        ]
    )

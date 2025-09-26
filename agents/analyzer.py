import logging
import json
import re
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from messages import AnalyzerAgent
from settings import SharedSettings
from models.pr_state import PRState
from schemas import AnalyzerResult, ModuleAnalysis, CategoryAnalysis, Recommendation, ResearchSource

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model=SharedSettings.GEMINI_MODEL,
    temperature=SharedSettings.GEMINI_TEMPERATURE,
    google_api_key=SharedSettings.GEMINI_API_KEY,
    convert_system_message_to_human=True
)

async def analyzer_node(state: PRState) -> PRState:
    """Nó do agente analisador que analisa cada módulo"""
    logger.info("🔍 Iniciando análise de código dos módulos")
    state.update_progress("Analisando módulos", 30.0)
    
    if not state.separator_result or not state.separator_result.modules:
        state.add_error("Nenhum módulo encontrado para análise")
        return state
    
    analyzer_results = []
    
    for i, module in enumerate(state.separator_result.modules):
        try:
            logger.info(f"📊 Analisando módulo {i+1}/{len(state.separator_result.modules)}: {module.name}")
            
            # Analisa o módulo
            result = await analyze_module(state, module)
            analyzer_results.append(result)
            
            progress = 30 + (i + 1) * 50 / len(state.separator_result.modules)
            state.update_progress(f"Analisando módulo {module.name}", progress)
            
        except Exception as e:
            error_msg = f"Erro ao analisar módulo {module.name}: {str(e)}"
            state.add_error(error_msg)
            logger.error(error_msg)
    
    state.analyzer_results = analyzer_results
    state.log(f"✅ Análise concluída: {len(analyzer_results)} módulos analisados")
    state.update_progress("Análise de módulos concluída", 80.0)
    
    return state

async def analyze_module(state: PRState, module) -> AnalyzerResult:
    """Analisa um módulo específico"""
    
    # Constrói o contexto dos arquivos do módulo
    module_files_context = build_module_context(state, module)
    
    # Pesquisa informações relevantes
    research_sources = await research_module_topics(module, module_files_context)
    
    # Constrói o prompt de análise
    analysis_prompt = build_analysis_prompt(state, module, module_files_context, research_sources)
    
    # Executa a análise
    messages = [HumanMessage(content=analysis_prompt)]
    response = await llm.ainvoke(messages)
    
    # Parse do resultado
    return parse_analyzer_response(response.content, module.id)

def build_module_context(state: PRState, module) -> str:
    """Constrói o contexto dos arquivos do módulo"""
    context = f"**Módulo: {module.name}**\n"
    context += f"Tipo: {module.type}\n"
    context += f"Razão: {module.reason}\n"
    context += f"Arquivos: {', '.join(module.files)}\n\n"
    
    # Encontra os arquivos do módulo no estado
    module_files = []
    for file_change in state.files_changed:
        if file_change.filename in module.files:
            module_files.append(file_change)
    
    for file_change in module_files:
        context += f"\n## {file_change.filename}\n"
        context += f"Status: {file_change.status}\n"
        context += f"Mudanças: +{file_change.additions}/-{file_change.deletions}\n"
        
        if file_change.after_content:
            context += f"Conteúdo:\n```\n{file_change.after_content}\n```\n"
        
        if file_change.patch:
            context += f"Patch:\n```\n{file_change.patch}\n```\n"
    
    return context

async def research_module_topics(module, context: str) -> List[ResearchSource]:
    """Pesquisa informações relevantes para o módulo"""
    research_sources = []
    
    try:
        # Identifica tópicos para pesquisa baseado no contexto
        research_topics = identify_research_topics(module, context)
        
        for topic in research_topics:
            try:
                # Pesquisa na documentação
                doc_result = await search_documentation_topic(topic)
                if doc_result:
                    research_sources.append(ResearchSource(
                        source="documentation",
                        query=topic,
                        findings=doc_result
                    ))
                
                # Pesquisa no Google
                google_results = await search_google_topic(topic)
                if google_results:
                    findings = format_google_findings(google_results)
                    research_sources.append(ResearchSource(
                        source="google",
                        query=topic,
                        findings=findings
                    ))
                    
            except Exception as e:
                logger.warning(f"Erro na pesquisa para tópico '{topic}': {e}")
                continue
                
    except Exception as e:
        logger.error(f"Erro na pesquisa de tópicos: {e}")
    
    return research_sources

def identify_research_topics(module, context: str) -> List[str]:
    """Identifica tópicos para pesquisa baseado no módulo"""
    topics = []
    
    # Tópicos baseados no tipo de módulo
    if module.type == "interactive":
        topics.extend([
            "clean code principles",
            "SOLID principles",
            "dependency injection patterns"
        ])
    elif module.type == "feature":
        topics.extend([
            "feature development best practices",
            "code organization patterns",
            "testing strategies"
        ])
    else:  # independent
        topics.extend([
            "single responsibility principle",
            "code quality metrics",
            "refactoring techniques"
        ])
    
    # Tópicos baseados no conteúdo dos arquivos
    if "test" in context.lower():
        topics.append("unit testing best practices")
    if "api" in context.lower():
        topics.append("API design patterns")
    if "database" in context.lower():
        topics.append("database design patterns")
    if "security" in context.lower():
        topics.append("security best practices")
    
    return topics[:3]  # Limita a 3 tópicos para não sobrecarregar

async def search_documentation_topic(topic: str) -> str:
    """Pesquisa um tópico na documentação"""
    try:
        # Usa o namespace padrão para documentação
        result = await search_informations.ainvoke({"query": topic, "namespace": "documentation"})
        return result if result else ""
    except Exception as e:
        logger.warning(f"Erro na pesquisa de documentação: {e}")
        return ""

async def search_google_topic(topic: str) -> List[Dict]:
    """Pesquisa um tópico no Google"""
    try:
        results = await search_google_informations.ainvoke({"query": f"{topic} best practices programming"})
        return results if results else []
    except Exception as e:
        logger.warning(f"Erro na pesquisa do Google: {e}")
        return []

def format_google_findings(results: List[Dict]) -> str:
    """Formata os resultados do Google para o contexto"""
    findings = []
    for result in results[:3]:  # Limita a 3 resultados
        findings.append(f"- {result.get('title', 'Sem título')}: {result.get('snippet', 'Sem descrição')}")
    return "\n".join(findings)

def build_analysis_prompt(state: PRState, module, context: str, research_sources: List[ResearchSource]) -> str:
    """Constrói o prompt de análise para o módulo"""
    
    research_context = ""
    if research_sources:
        research_context = "\n**Informações de pesquisa encontradas:**\n"
        for source in research_sources:
            research_context += f"\n- {source.source.upper()}: {source.query}\n{source.findings}\n"
    
    return f"""
Analise este módulo de código seguindo as melhores práticas de clean code e SOLID principles.

**Contexto do PR:**
- Título: {state.pr_title}
- Repositório: {state.repo_owner}/{state.repo_name}
- Total de mudanças: +{state.total_additions}/-{state.total_deletions} linhas

{context}

{research_context}

**Instruções de análise:**
1. Avalie cada categoria (segurança, qualidade, performance, arquitetura, testes)
2. Identifique problemas específicos e sugestões de melhoria
3. Considere as informações de pesquisa fornecidas
4. Seja específico sobre arquivos e linhas problemáticas
5. Priorize as recomendações por importância

Retorne APENAS um JSON válido seguindo a estrutura especificada no prompt do sistema.
"""

def parse_analyzer_response(content: str, module_id: str) -> AnalyzerResult:
    """Parse da resposta do agente analisador"""
    try:
        # Tenta extrair JSON da resposta
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            logger.warning("Não foi possível extrair JSON válido da análise")
            return create_fallback_analysis(module_id)
        
        # Parse da análise
        analysis_data = data.get("analysis", {})
        categories = {}
        
        for category_name, category_data in analysis_data.get("categories", {}).items():
            categories[category_name] = CategoryAnalysis(
                score=category_data.get("score", 5.0),
                issues=category_data.get("issues", []),
                suggestions=category_data.get("suggestions", [])
            )
        
        module_analysis = ModuleAnalysis(
            overall_score=analysis_data.get("overall_score", 5.0),
            categories=categories
        )
        
        # Parse das recomendações
        recommendations = []
        for rec_data in data.get("recommendations", []):
            recommendation = Recommendation(
                priority=rec_data.get("priority", "medium"),
                category=rec_data.get("category", "quality"),
                description=rec_data.get("description", ""),
                suggestion=rec_data.get("suggestion", ""),
                files=rec_data.get("files", []),
                lines=rec_data.get("lines")
            )
            recommendations.append(recommendation)
        
        # Parse das fontes de pesquisa
        research_sources = []
        for source_data in data.get("research_sources", []):
            source = ResearchSource(
                source=source_data.get("source", "unknown"),
                query=source_data.get("query", ""),
                findings=source_data.get("findings", "")
            )
            research_sources.append(source)
        
        return AnalyzerResult(
            module_id=module_id,
            analysis=module_analysis,
            recommendations=recommendations,
            research_sources=research_sources
        )
        
    except Exception as e:
        logger.error(f"Erro ao fazer parse da análise: {e}")
        return create_fallback_analysis(module_id)

def create_fallback_analysis(module_id: str) -> AnalyzerResult:
    """Cria análise de fallback quando o parsing falha"""
    categories = {
        "security": CategoryAnalysis(score=5.0, issues=[], suggestions=[]),
        "quality": CategoryAnalysis(score=5.0, issues=[], suggestions=[]),
        "performance": CategoryAnalysis(score=5.0, issues=[], suggestions=[]),
        "architecture": CategoryAnalysis(score=5.0, issues=[], suggestions=[]),
        "tests": CategoryAnalysis(score=5.0, issues=[], suggestions=[])
    }
    
    module_analysis = ModuleAnalysis(
        overall_score=5.0,
        categories=categories
    )
    
    return AnalyzerResult(
        module_id=module_id,
        analysis=module_analysis,
        recommendations=[],
        research_sources=[]
    )
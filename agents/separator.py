import logging
import json
import re
from typing import Dict, List, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from messages import SeparatorAgent
from settings import SharedSettings
from models.pr_state import PRState
from schemas import SeparatorResult, Module

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model=SharedSettings.GEMINI_MODEL,
    temperature=0.1,  # Baixa temperatura para análise mais consistente
    google_api_key=SharedSettings.GEMINI_API_KEY,
    convert_system_message_to_human=True
)

def build_separator_prompt(state: PRState) -> str:
    """Constrói o prompt para o agente separador"""
    
    files_context = ""
    for i, file_change in enumerate(state.files_changed, 1):
        files_context += f"\n{i}. **{file_change.filename}**\n"
        files_context += f"   - Status: {file_change.status}\n"
        files_context += f"   - Mudanças: +{file_change.additions}/-{file_change.deletions} linhas\n"
        
        if file_change.after_content:
            # Mostra apenas as primeiras linhas para análise de imports
            content_preview = file_change.after_content[:1000]
            files_context += f"   - Conteúdo (preview):\n```\n{content_preview}\n```\n"
        
        if file_change.patch:
            files_context += f"   - Patch (preview):\n```\n{file_change.patch[:500]}\n```\n"

    return f"""
Analise os arquivos modificados neste Pull Request e agrupe-os em módulos baseados em suas dependências e interações.

**PR:** {state.pr_title}
**Repositório:** {state.repo_owner}/{state.repo_name}
**Total de arquivos:** {len(state.files_changed)}

**Arquivos modificados:**
{files_context}

**Instruções:**
1. Analise as dependências entre os arquivos (imports, requires, etc.)
2. Identifique arquivos que trabalham juntos funcionalmente
3. Agrupe arquivos relacionados em módulos lógicos
4. Se um arquivo não depende de outros, ele forma um módulo independente

Retorne APENAS um JSON válido com a estrutura especificada no prompt do sistema.
"""

async def separator_node(state: PRState) -> PRState:
    """Nó do agente separador que agrupa arquivos em módulos"""
    logger.info("🔍 Iniciando análise de separação de arquivos")
    state.update_progress("Separando arquivos em módulos", 10.0)
    
    try:
        # Constrói o prompt com contexto dos arquivos
        prompt = build_separator_prompt(state)
        
        # Cria a mensagem para o LLM
        messages = [
            HumanMessage(content=prompt)
        ]
        
        # Executa a análise
        response = await llm.ainvoke(messages)
        
        # Parse do resultado JSON
        separator_result = parse_separator_response(response.content)
        state.separator_result = separator_result
        
        state.log(f"✅ Separação concluída: {len(separator_result.modules)} módulos identificados")
        state.update_progress("Arquivos separados em módulos", 20.0)
        
        # Log dos módulos encontrados
        for module in separator_result.modules:
            state.log(f"📦 Módulo '{module.name}': {len(module.files)} arquivos ({module.type})")
        
    except Exception as e:
        error_msg = f"Erro na separação de arquivos: {str(e)}"
        state.add_error(error_msg)
        logger.error(error_msg)
    
    return state

def parse_separator_response(content: str) -> SeparatorResult:
    """Parse da resposta do agente separador"""
    try:
        # Tenta extrair JSON da resposta
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            # Fallback: cria um módulo único com todos os arquivos
            logger.warning("Não foi possível extrair JSON válido, criando módulo único")
            return create_fallback_modules()
        
        # Valida e converte os dados
        modules = []
        for module_data in data.get("modules", []):
            module = Module(
                id=module_data.get("id", f"module_{len(modules) + 1}"),
                name=module_data.get("name", "Módulo sem nome"),
                files=module_data.get("files", []),
                reason=module_data.get("reason", "Agrupamento automático"),
                type=module_data.get("type", "independent")
            )
            modules.append(module)
        
        return SeparatorResult(
            modules=modules,
            summary=data.get("summary", "Separação realizada com sucesso")
        )
        
    except Exception as e:
        logger.error(f"Erro ao fazer parse da resposta: {e}")
        return create_fallback_modules()

def create_fallback_modules() -> SeparatorResult:
    """Cria módulos de fallback quando o parsing falha"""
    modules = [
        Module(
            id="module_1",
            name="Arquivos Modificados",
            files=[],
            reason="Fallback: não foi possível analisar dependências",
            type="independent"
        )
    ]
    
    return SeparatorResult(
        modules=modules,
        summary="Separação realizada com fallback devido a erro no parsing"
    )
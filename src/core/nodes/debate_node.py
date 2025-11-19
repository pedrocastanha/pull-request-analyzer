import logging
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from src.core.state import PRAnalysisState
from src.providers.llms import LLMManager
from src.providers.prompts.validator import Validator
from src.utils.json_parser import parse_llm_json_response

logger = logging.getLogger(__name__)


async def debate_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: debate] Starting debate between Reviewer and Validator")

    reviewer_analysis = state.get("reviewer_analysis")

    if not reviewer_analysis or not reviewer_analysis.get("comments"):
        logger.warning("[NODE: debate] No comments to validate")
        return {"final_comments": []}

    initial_comments = reviewer_analysis.get("comments", [])
    logger.info(f"[NODE: debate] Starting with {len(initial_comments)} comments from Reviewer")

    # Log dos comentários iniciais
    logger.info("[NODE: debate] === INITIAL COMMENTS FROM REVIEWER ===")
    for i, comment in enumerate(initial_comments, 1):
        logger.info(f"[NODE: debate] Comment #{i}:")
        logger.info(f"  File: {comment.get('file', 'N/A')}")
        logger.info(f"  Line: {comment.get('line', 'N/A')}")
        logger.info(f"  Priority: {comment.get('priority', 'N/A')}")
        logger.info(f"  Agent: {comment.get('agent_type', 'N/A')}")
        msg = comment.get('message', '')
        if len(msg) > 300:
            logger.info(f"  Message: {msg[:300]}...")
        else:
            logger.info(f"  Message: {msg}")

    logger.info("[NODE: debate] === ROUND 2: Validator analyzing comments ===")

    validator_prompt = ChatPromptTemplate.from_messages([
        ("system", Validator.SYSTEM_PROMPT),
        ("human", """Analise os seguintes comentários propostos pelo Reviewer Agent.

Seu papel neste ROUND 2 é CRITICAR impiedosamente. Descarte tudo que:
- Depende de regra de negócio
- É opinião sem impacto técnico
- Não pode ser confirmado só olhando código

Comentários para validar:
```json
{comments_json}
```

Retorne JSON no formato:
```json
{{
    "action": "critique",
    "feedback": {{
        "approved_comments": [...],
        "rejected_comments": [...],
        "suggestions_for_reviewer": [...]
    }}
}}
```
""")
    ])

    validator_llm = LLMManager.get_llm("gpt-4.1-mini")

    import json
    comments_json = json.dumps(initial_comments, indent=2)

    try:
        validator_response = await (validator_prompt | validator_llm).ainvoke({
            "comments_json": comments_json
        })

        validator_content = validator_response.content if hasattr(validator_response, 'content') else str(validator_response)
        validator_feedback = parse_llm_json_response(validator_content)

        approved_comments = validator_feedback.get("feedback", {}).get("approved_comments", [])
        rejected_comments = validator_feedback.get("feedback", {}).get("rejected_comments", [])
        suggestions = validator_feedback.get("feedback", {}).get("suggestions_for_reviewer", [])

        approved_count = len(approved_comments)
        rejected_count = len(rejected_comments)

        logger.info(f"[NODE: debate] Validator Round 2: Approved={approved_count}, Rejected={rejected_count}")

        # Log detalhado dos comentários rejeitados
        if rejected_count > 0:
            logger.info(f"[NODE: debate] === REJECTED COMMENTS DETAILS ===")
            for i, rejected in enumerate(rejected_comments, 1):
                logger.info(f"[NODE: debate] Rejected #{i}:")
                logger.info(f"  File: {rejected.get('file', 'N/A')}")
                logger.info(f"  Line: {rejected.get('line', 'N/A')}")
                logger.info(f"  Reason: {rejected.get('reason', 'N/A')}")
                original_msg = rejected.get('original_message', '')
                if len(original_msg) > 200:
                    logger.info(f"  Original: {original_msg[:200]}...")
                else:
                    logger.info(f"  Original: {original_msg}")

        # Log das sugestões
        if suggestions:
            logger.info(f"[NODE: debate] === VALIDATOR SUGGESTIONS ===")
            for i, suggestion in enumerate(suggestions, 1):
                logger.info(f"[NODE: debate] Suggestion #{i}: {suggestion}")

        if approved_count == 0:
            logger.warning("[NODE: debate] Validator rejected ALL comments!")
            logger.warning("[NODE: debate] See rejection details above")
            return {"final_comments": []}

    except Exception as e:
        logger.error(f"[NODE: debate] Error in Validator Round 2: {e}")
        return {"final_comments": initial_comments}

    logger.info("[NODE: debate] === ROUND 3: Reviewer refining based on feedback ===")

    reviewer_refine_prompt = ChatPromptTemplate.from_messages([
        ("system", """Você é o Reviewer Agent. O Validator criticou seus comentários.

Refine os comentários APROVADOS, removendo os REJEITADOS e considerando as sugestões.

IMPORTANTE:
- Mantenha apenas comentários que o Validator aprovou
- Melhore a clareza técnica baseado nas sugestões
- **MANTENHA O FORMATO COMPLETO** com todos os campos originais:
  - file, line, final_line, priority, agent_type, message
- **PRESERVE o campo `message` COMPLETO** com todas as seções:
  - Contexto, Problema, Impacto, Como resolver (com código ANTES/DEPOIS)
- NÃO simplifique ou encurte os comentários
- NÃO remova o campo Contexto ou qualquer outra seção do message
"""),
        ("human", """Feedback do Validator:
```json
{validator_feedback}
```

Comentários originais:
```json
{original_comments}
```

Retorne JSON com os comentários refinados:
```json
{{
    "comments": [...]
}}
```
""")
    ])

    try:
        reviewer_refine_response = await (reviewer_refine_prompt | validator_llm).ainvoke({
            "validator_feedback": json.dumps(validator_feedback, indent=2),
            "original_comments": comments_json
        })

        refine_content = reviewer_refine_response.content if hasattr(reviewer_refine_response, 'content') else str(reviewer_refine_response)
        refined_data = parse_llm_json_response(refine_content)
        refined_comments = refined_data.get("comments", [])

        logger.info(f"[NODE: debate] Reviewer Round 3: Refined to {len(refined_comments)} comments")

    except Exception as e:
        logger.error(f"[NODE: debate] Error in Reviewer Round 3: {e}")
        refined_comments = validator_feedback.get("feedback", {}).get("approved_comments", [])

    logger.info("[NODE: debate] === ROUND 4: Validator final decision ===")

    final_decision_prompt = ChatPromptTemplate.from_messages([
        ("system", Validator.SYSTEM_PROMPT),
        ("human", """Este é o ROUND 4 - sua DECISÃO FINAL.

O Reviewer refinou os comentários baseado no seu feedback do Round 2.

Agora você deve:
1. Fazer a decisão FINAL sobre cada comentário
2. DESCARTAR impiedosamente qualquer coisa duvidosa
3. Retornar apenas os comentários que você GARANTE serem problemas técnicos objetivos

**IMPORTANTE: PRESERVE O FORMATO COMPLETO DOS COMENTÁRIOS APROVADOS!**
- Mantenha TODOS os campos: file, line, final_line, priority, agent_type, message
- Mantenha o campo `message` COMPLETO com todas as seções:
  - Contexto, Problema, Impacto, Como resolver (incluindo código ANTES/DEPOIS)
- NÃO simplifique, NÃO encurte, NÃO remova nenhuma seção
- Apenas aprove ou rejeite, mas NÃO modifique o conteúdo dos comentários aprovados

Comentários refinados:
```json
{refined_comments}
```

Retorne JSON no formato:
```json
{{
    "action": "finalize",
    "final_comments": [...],
    "total_approved": X,
    "total_rejected": Y
}}
```
""")
    ])

    try:
        final_response = await (final_decision_prompt | validator_llm).ainvoke({
            "refined_comments": json.dumps(refined_comments, indent=2)
        })

        final_content = final_response.content if hasattr(final_response, 'content') else str(final_response)
        final_decision = parse_llm_json_response(final_content)

        final_comments = final_decision.get("final_comments", [])
        total_approved = final_decision.get("total_approved", len(final_comments))
        total_rejected = final_decision.get("total_rejected", 0)

        logger.info(f"[NODE: debate] === DEBATE COMPLETE ===")
        logger.info(f"[NODE: debate] Started with: {len(initial_comments)} comments")
        logger.info(f"[NODE: debate] Final approved: {total_approved} comments")
        logger.info(f"[NODE: debate] Final rejected: {total_rejected} comments")
        logger.info(f"[NODE: debate] Reduction: {len(initial_comments) - total_approved} comments filtered out")

        return {"final_comments": final_comments}

    except Exception as e:
        logger.error(f"[NODE: debate] Error in Validator Round 4: {e}")
        return {"final_comments": refined_comments}

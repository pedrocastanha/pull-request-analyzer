import logging
from models.pr_state import PRState

logger = logging.getLogger(__name__)

def final_response_node(state: PRState) -> dict:
    """Nó final que prepara a resposta"""
    logger.info("🏁 Finalizando análise do PR")
    
    # Atualiza o status final
    state.status = "completed"
    state.progress = 100.0
    
    # Log do resumo final
    if state.commentator_result:
        logger.info(f"📊 Resumo: {state.commentator_result.executive_summary[:100]}...")
        logger.info(f"💡 Recomendações: {len(state.commentator_result.actionable_recommendations)}")
        logger.info(f"📚 Recursos: {len(state.commentator_result.learning_resources)}")
    
    logger.info("✅ Análise completa finalizada")
    
    return {
        "status": "completed",
        "progress": 100.0,
        "final_message": "Análise do PR concluída com sucesso!"
    }


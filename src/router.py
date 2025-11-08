import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.graph import graph
from src.core.state import create_initial_state
from src.schemas import AnalyzePRResponse, AnalyzePRRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/azure/pr-analyzer", tags=["PR Analyzer"])


@router.post("/analyze", response_model=AnalyzePRResponse)
async def analyze_pr(request: AnalyzePRRequest):
    logger.info(f"[API] Received request to analyze PR #{request.pull_request_id}")

    try:
        logger.info(f"[API] Creating initial state for PR #{request.pull_request_id}")
        initial_state = create_initial_state(request.pull_request_id)

        logger.info(
            f"[API] Starting LangGraph workflow for PR #{request.pull_request_id}"
        )
        result = await graph.ainvoke(initial_state)

        if result.get("error"):
            logger.error(f"[API] Error during graph execution: {result['error']}")
            return {
                "status": "error",
                "message": "Failed to analyze PR",
                "pr_id": request.pull_request_id,
                "error": result["error"],
                "analysis": None,
            }

        reviewer_analysis = result.get("reviewer_analysis", {})
        comments = reviewer_analysis.get("comments", [])

        logger.info(
            f"[API] PR #{request.pull_request_id} analysis completed successfully. "
            f"Comments generated: {len(comments)}"
        )

        if comments:
            logger.debug(f"[API] Sample comment structure: {comments[0]}")

        try:
            response = {
                "status": "success",
                "message": "PR analysis completed successfully",
                "pr_id": request.pull_request_id,
                "comments": comments,
                "total_comments": len(comments),
                "error": None,
            }
            logger.info(f"[API] Returning response with {len(comments)} comments")
            return response
        except Exception as e:
            logger.error(f"[API] Error creating response: {str(e)}", exc_info=True)
            raise

    except Exception as e:
        logger.error(
            f"[API] Unexpected error during PR analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during PR analysis: {str(e)}",
        )

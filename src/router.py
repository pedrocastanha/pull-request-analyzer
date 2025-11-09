import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from src.core.graph import graph
from src.core.state import create_initial_state
from src.schemas import AnalyzePRResponse, AnalyzePRRequest
from src.utils.document_processor import DocumentProcessor
from src.utils.pinecone_manager import PineconeManager

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


@router.post("/add-document")
async def add_document_vector_store(
    file: UploadFile = File(...), namespace: str = Form(...)
):
    logger.info(
        f"[API] Received request to add document '{file.filename}' to namespace: {namespace}"
    )
    try:
        if not namespace:
            raise HTTPException(status_code=400, detail="Namespace is required.")

        document_processor = DocumentProcessor()
        pinecone_manager = PineconeManager(namespace)

        logger.info(f"[API] Extracting text from document: {file.filename}")
        extracted_text = await document_processor.extract_text_from_file(file)

        logger.info(f"[API] Adding document to namespace: {namespace}")
        pinecone_manager.add_documents([extracted_text])

        logger.info(f"[API] Successfully processed document '{file.filename}'")
        return {
            "status": "success",
            "message": f"Successfully processed document '{file.filename}' for namespace '{namespace}'"
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"[API] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Unexpected error in add-document route: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        )

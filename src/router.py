import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from src.core.graph import graph
from src.core.state import create_initial_state
from src.schemas import AnalyzePRResponse, AnalyzePRRequest
from src.utils.document_processor import DocumentProcessor
from src.utils.pinecone_manager import PineconeManager
from src.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/azure/pr-analyzer", tags=["PR Analyzer"])


@router.post("/analyze", response_model=AnalyzePRResponse)
async def analyze_pr(request: AnalyzePRRequest):
    logger.info(
        f"[API] Received request to analyze PR #{request.resource.pullRequestId}"
    )

    try:
        logger.info(
            f"[API] Creating initial state for PR #{request.resource.pullRequestId} (Type: {request.project_type})"
        )

        repository_id = Settings.AZURE_ERP_BACKEND_REPOSITORY_ID
        if request.project_type == "nextjs":
            repository_id = Settings.AZURE_ERP_FRONTEND_REPOSITORY_ID

        initial_state = create_initial_state(
            pr_id=request.resource.pullRequestId,
            project_type=request.project_type,
            repository_id=repository_id,
        )

        logger.info(
            f"[API] Starting LangGraph workflow for PR #{request.resource.pullRequestId}"
        )
        result = await graph.ainvoke(initial_state, {"recursion_limit": 500})

        if result.get("error"):
            logger.error(f"[API] Error during graph execution: {result['error']}")
            return AnalyzePRResponse(
                status="error",
                message="Failed to analyze PR",
                pr_id=request.resource.pullRequestId,
                error=result["error"],
                comments=[],
                total_comments=0,
            )

        published_comments = result.get("published_comments", []) or []

        logger.info(
            f"[API] PR #{request.resource.pullRequestId} analysis completed successfully. "
            f"Comments generated: {len(published_comments)}"
        )

        if published_comments:
            logger.debug(f"[API] Sample comment structure: {published_comments[0]}")

        try:
            response = AnalyzePRResponse(
                status="success",
                message="PR analysis completed successfully",
                pr_id=request.resource.pullRequestId,
                comments=published_comments,
                total_comments=len(published_comments),
                error=None,
            )
            logger.info(
                f"[API] Returning response with {len(published_comments)} comments"
            )
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


@router.post("/analyze/frontend", response_model=AnalyzePRResponse)
async def analyze_pr_frontend(request: AnalyzePRRequest):
    request.project_type = "nextjs"
    return await analyze_pr(request)


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
            "message": f"Successfully processed document '{file.filename}' for namespace '{namespace}'",
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"[API] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"[API] Unexpected error in add-document route: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="An internal server error occurred."
        )

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.utils.azure_requests import AzureManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/azure/pr-analyzer",
    tags=["PR Analyzer"]
)


class AnalyzePRRequest(BaseModel):
    pull_request_id: int = Field()


@router.post("/analyze")
async def analyze_pr(request: AnalyzePRRequest):
    logger.info(f"Received request to analyze PR: {request.pull_request_id}")
    try:
        logger.info("Starting PR analysis...")

        pr_data = AzureManager.get_pr_details(request.pull_request_id)
        if pr_data is None:
            return {
                "status": "error",
                "message": "Failed to fetch PR details from Azure DevOps",
                "pr_id": request.pull_request_id
            }

        return {
            "status": "success",
            "message": "PR analysis completed successfully",
            "pr_id": request.pull_request_id,
            "data": pr_data
        }

    except Exception as e:
        logger.error(f"Error during PR analysis: {str(e)}")
        raise
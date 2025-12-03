import json
import logging
from typing import Dict, Any, List

from src.core import PRAnalysisState
from src.providers.llms import LLMManager
from src.providers.prompts_manager import PromptManager
from src.schemas import ReviewerAnalysis, ReviewerComment
from src.providers.prompts.reviewer import Reviewer
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


async def reviewer_debate_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: reviewer_debate] Starting QA/Debate on proposed comments")

    pr_data = state.get("pr_data")
    reviewer_analysis_dict = state.get("reviewer_analysis")

    if not pr_data:
        logger.warning("[NODE: reviewer_debate] No PR data found. Skipping debate.")
        return {}

    if not reviewer_analysis_dict or "comments" not in reviewer_analysis_dict:
        logger.warning(
            "[NODE: reviewer_debate] No reviewer analysis found. Skipping debate."
        )
        return {}

    proposed_comments = reviewer_analysis_dict.get("comments", [])
    if not proposed_comments:
        logger.info("[NODE: reviewer_debate] No comments to review.")
        return {"reviewer_analysis": {"comments": []}}

    comments_by_file: Dict[str, List[Dict]] = {}
    for comment in proposed_comments:
        file_path = comment.get("file")
        if file_path:
            if file_path not in comments_by_file:
                comments_by_file[file_path] = []
            comments_by_file[file_path].append(comment)

    try:
        base_prompt = Reviewer.DEBATE_SYSTEM_PROMPT
        structured_llm = LLMManager.get_structured_llm("gpt-4.1-nano", ReviewerAnalysis)
    except Exception as e:
        logger.error(f"[NODE: reviewer_debate] Failed to init LLM: {e}")
        return {}

    validated_comments = []

    for file_path, comments in comments_by_file.items():
        file_diff_data = next(
            (f for f in pr_data.get("files", []) if f.get("path") == file_path), None
        )

        if not file_diff_data:
            logger.warning(
                f"[NODE: reviewer_debate] File {file_path} found in comments but not in PR data diffs. Skipping comments for this file."
            )
            continue

        diff_content = file_diff_data.get("diff", "(No diff content available)")

        context_str = (
            f"### FILE: {file_path}\n\n"
            f"#### DIFF (Code Changes):\n```diff\n{diff_content}\n```\n\n"
            f"#### PROPOSED COMMENTS:\n"
        )

        for i, c in enumerate(comments):
            context_str += (
                f"--- Comment #{i+1} ---\n"
                f"Line: {c.get('line')}\n"
                f"Type: {c.get('agent_type')} / {c.get('priority')}\n"
                f"Message: {c.get('message')}\n\n"
            )

        try:

            messages = [
                SystemMessage(content=base_prompt),
                HumanMessage(content=context_str),
            ]

            result: ReviewerAnalysis = await structured_llm.ainvoke(messages)

            if result and result.comments:
                logger.info(
                    f"[NODE: reviewer_debate] File {file_path}: {len(comments)} proposed -> {len(result.comments)} validated."
                )
                validated_comments.extend(result.comments)
            else:
                logger.info(
                    f"[NODE: reviewer_debate] File {file_path}: All comments rejected."
                )

        except Exception as e:
            logger.error(
                f"[NODE: reviewer_debate] Error processing file {file_path}: {e}"
            )
            continue

    logger.info(
        f"[NODE: reviewer_debate] Finished. Total comments: {len(proposed_comments)} -> {len(validated_comments)}"
    )

    return {
        "reviewer_analysis": {"comments": [c.model_dump() for c in validated_comments]}
    }

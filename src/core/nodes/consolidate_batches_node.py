import logging
from typing import Dict, Any, List

from src.core.state import PRAnalysisState

logger = logging.getLogger(__name__)


async def consolidate_batches_node(state: PRAnalysisState) -> Dict[str, Any]:
    batch_analyses = state.get("batch_analyses", [])
    total_batches = state.get("total_batches", 0)

    logger.info(
        f"[NODE: consolidate_batches] Consolidating {len(batch_analyses)} batches"
    )

    completed_batches = [b for b in batch_analyses if b.get("status") == "completed"]
    failed_batches = [b for b in batch_analyses if b.get("status") == "failed"]

    logger.info(
        f"[NODE: consolidate_batches] Completed: {len(completed_batches)}, "
        f"Failed: {len(failed_batches)}"
    )

    all_security_issues = []
    all_performance_issues = []
    all_clean_code_issues = []
    all_logical_issues = []

    for batch in completed_batches:
        security_analysis = batch.get("security_analysis", {})
        performance_analysis = batch.get("performance_analysis", {})
        clean_code_analysis = batch.get("clean_code_analysis", {})
        logical_analysis = batch.get("logical_analysis", {})

        all_security_issues.extend(security_analysis.get("issues", []))
        all_performance_issues.extend(performance_analysis.get("issues", []))
        all_clean_code_issues.extend(clean_code_analysis.get("issues", []))
        all_logical_issues.extend(logical_analysis.get("issues", []))

    unique_security_issues = _deduplicate_issues(all_security_issues)
    unique_performance_issues = _deduplicate_issues(all_performance_issues)
    unique_clean_code_issues = _deduplicate_issues(all_clean_code_issues)
    unique_logical_issues = _deduplicate_issues(all_logical_issues)

    logger.info(
        f"[NODE: consolidate_batches] Issues after deduplication - "
        f"Security: {len(unique_security_issues)}, "
        f"Performance: {len(unique_performance_issues)}, "
        f"Clean Code: {len(unique_clean_code_issues)}, "
        f"Logical: {len(unique_logical_issues)}"
    )

    consolidated = {
        "security_analysis": {"issues": unique_security_issues},
        "performance_analysis": {"issues": unique_performance_issues},
        "clean_code_analysis": {"issues": unique_clean_code_issues},
        "logical_analysis": {"issues": unique_logical_issues},
    }

    if failed_batches:
        logger.warning(
            f"[NODE: consolidate_batches] Warning: {len(failed_batches)} batch(es) failed - "
            f"indices: {[b['batch_index'] for b in failed_batches]}"
        )

    logger.info("[NODE: consolidate_batches] ✓ Consolidation complete")

    return consolidated


def _deduplicate_issues(issues: List[Dict]) -> List[Dict]:
    seen = set()
    unique_issues = []

    for issue in issues:
        key = (issue.get("file"), issue.get("line"))
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    return unique_issues

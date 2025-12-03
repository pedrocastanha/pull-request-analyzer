import logging
from typing import Dict, Any, List

from src.core.state import PRAnalysisState

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
MAX_TOKENS_PER_BATCH = 5000


def create_batches_node(state: PRAnalysisState) -> Dict[str, Any]:
    pr_data = state.get("pr_data")
    pr_id = state.get("pr_id")

    if not pr_data:
        logger.error("[NODE: create_batches] No pr_data in state")
        return {"error": ["Missing pr_data for batch creation"]}

    files = pr_data.get("files", [])
    total_files = len(files)

    logger.info(
        f"[NODE: create_batches] Creating batches for PR #{pr_id} with {total_files} files"
    )

    modules = _group_files_by_module(files)

    batches = _create_batches_from_modules(modules)

    total_batches = len(batches)

    logger.info(
        f"[NODE: create_batches] ✓ Created {total_batches} batches (batch size: {BATCH_SIZE})"
    )

    for idx, batch in enumerate(batches):
        logger.info(f"  Batch {idx + 1}: {len(batch)} files")

    return {
        "batches": batches,
        "total_batches": total_batches,
        "current_batch_index": 0,
    }


def _group_files_by_module(
    files: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    modules: Dict[str, List[Dict[str, Any]]] = {}

    for file_info in files:
        path = file_info.get("path", "")
        path_parts = path.split("/")

        if len(path_parts) == 1:
            module_name = "_root"
        elif len(path_parts) == 2:
            module_name = path_parts[0]
        else:
            if path_parts[0] == "src":
                module_name = path_parts[1]
            else:
                module_name = path_parts[0]

        if module_name not in modules:
            modules[module_name] = []

        modules[module_name].append(file_info)

    return modules


def _create_batches_from_modules(
    modules: Dict[str, List[Dict[str, Any]]],
) -> List[List[Dict[str, Any]]]:
    batches = []

    for module_name, module_files in modules.items():
        if len(module_files) <= BATCH_SIZE:
            batches.append(module_files)
        else:
            for i in range(0, len(module_files), BATCH_SIZE):
                batch = module_files[i : i + BATCH_SIZE]
                batches.append(batch)

    return batches

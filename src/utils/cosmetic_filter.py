import logging
from typing import List, Tuple, Dict, Any

from src.utils.diff_parser import DiffParser

logger = logging.getLogger(__name__)


def filter_cosmetic_only_files(files: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    filtered_files = []
    skipped_count = 0

    for file_change in files:
        diff_text = file_change.get("diff", "")
        if not diff_text:
            continue

        classification = DiffParser.classify_file_changes(diff_text)

        if not classification["is_worth_analyzing"]:
            logger.info(
                f"[COSMETIC FILTER] Ignorando arquivo com apenas mudanças cosméticas: "
                f"{file_change['path']} "
                f"({classification['summary']['cosmetic_changes']} mudanças cosméticas)"
            )
            skipped_count += 1
            continue

        if classification["summary"]["cosmetic_changes"] > 0:
            filtered_diff = DiffParser.filter_cosmetic_changes(diff_text)
            if filtered_diff:
                filtered_file = file_change.copy()
                filtered_file["diff"] = filtered_diff
                filtered_file["_cosmetic_changes_removed"] = classification["summary"]["cosmetic_changes"]
                filtered_files.append(filtered_file)
                logger.info(
                    f"[COSMETIC FILTER] Removidas {classification['summary']['cosmetic_changes']} "
                    f"mudanças cosméticas de: {file_change['path']}"
                )
            else:
                skipped_count += 1
        else:
            filtered_files.append(file_change)

    return filtered_files, skipped_count


def should_skip_file_entirely(diff_text: str) -> bool:
    if not diff_text:
        return True

    classification = DiffParser.classify_file_changes(diff_text)
    return not classification["is_worth_analyzing"]


def get_filtered_diff(diff_text: str) -> str:
    if not diff_text:
        return ""

    return DiffParser.filter_cosmetic_changes(diff_text)

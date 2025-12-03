import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def filter_invalid_line_issues(
    parsed_data: Dict[str, Any], agent_name: str
) -> Dict[str, Any]:
    if "issues" not in parsed_data:
        return parsed_data

    original_count = len(parsed_data["issues"])
    valid_issues = []

    for issue in parsed_data["issues"]:
        line = issue.get("line")

        if line is not None and isinstance(line, int) and line > 0:
            valid_issues.append(issue)
        else:
            logger.warning(
                f"[{agent_name}] Issue descartado - linha inválida: "
                f"file={issue.get('file')}, line={line}, type={issue.get('type')}"
            )

    parsed_data["issues"] = valid_issues

    if original_count > len(valid_issues):
        logger.info(
            f"[{agent_name}] Validados {len(valid_issues)} de {original_count} issues "
            f"({original_count - len(valid_issues)} descartados por linha inválida)"
        )

    return parsed_data

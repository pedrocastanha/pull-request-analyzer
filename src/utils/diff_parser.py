import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class DiffParser:
    HUNK_HEADER_PATTERN = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    @staticmethod
    def parse_diff(diff_text: str) -> Dict[str, any]:
        chunks = []
        line_map = {}

        lines = diff_text.split("\n")
        current_old_line = 0
        current_new_line = 0
        in_hunk = False

        for line in lines:
            match = DiffParser.HUNK_HEADER_PATTERN.search(line)
            if match:
                old_start = int(match.group(1))
                new_start = int(match.group(3))

                current_old_line = old_start
                current_new_line = new_start
                in_hunk = True

                chunks.append(
                    {
                        "old_start": old_start,
                        "new_start": new_start,
                        "header": line,
                        "changes": [],
                    }
                )

                logger.debug(f"Found hunk: old={old_start}, new={new_start}")
                continue

            if not in_hunk:
                continue

            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:].strip()
                if content:
                    line_map[content] = current_new_line
                    chunks[-1]["changes"].append(
                        {"type": "add", "line": current_new_line, "content": content}
                    )
                current_new_line += 1

            elif line.startswith("-") and not line.startswith("---"):
                content = line[1:].strip()
                chunks[-1]["changes"].append(
                    {"type": "remove", "line": current_old_line, "content": content}
                )
                current_old_line += 1

            elif line.startswith(" "):
                current_old_line += 1
                current_new_line += 1

        return {"chunks": chunks, "line_map": line_map, "total_chunks": len(chunks)}

    @staticmethod
    def find_line_for_code(diff_text: str, code_snippet: str) -> Optional[int]:
        parsed = DiffParser.parse_diff(diff_text)

        code_clean = code_snippet.strip()
        if code_clean in parsed["line_map"]:
            return parsed["line_map"][code_clean]

        code_partial = code_clean[:50]
        for content, line_num in parsed["line_map"].items():
            if content.startswith(code_partial):
                return line_num

        return None

    @staticmethod
    def get_changed_line_ranges(diff_text: str) -> List[Tuple[int, int]]:
        parsed = DiffParser.parse_diff(diff_text)
        ranges = []

        for chunk in parsed["chunks"]:
            if chunk["changes"]:
                lines = [c["line"] for c in chunk["changes"] if c["type"] == "add"]
                if lines:
                    ranges.append((min(lines), max(lines)))

        return ranges

    @staticmethod
    def annotate_diff_with_lines(diff_text: str) -> str:
        annotated_lines = []

        lines = diff_text.split("\n")
        current_new_line = 0
        in_hunk = False

        for line in lines:
            match = DiffParser.HUNK_HEADER_PATTERN.search(line)
            if match:
                new_start = int(match.group(3))
                current_new_line = new_start
                in_hunk = True
                annotated_lines.append(line)
                continue

            if not in_hunk:
                annotated_lines.append(line)
                continue

            if line.startswith("+") and not line.startswith("+++"):
                annotated_lines.append(f"[LINE: {current_new_line}] {line}")
                current_new_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                annotated_lines.append(line)
            elif line.startswith(" "):
                annotated_lines.append(f"[LINE: {current_new_line}] {line}")
                current_new_line += 1
            else:
                annotated_lines.append(line)

        return "\n".join(annotated_lines)

    @staticmethod
    def get_line_number_from_annotated_diff(
        code_snippet: str, annotated_diff: str
    ) -> Optional[int]:
        code_clean = code_snippet.strip()

        for line in annotated_diff.split("\n"):
            if "[LINE:" in line:
                match = re.search(r"\[LINE:\s*(\d+)\]", line)
                if match:
                    line_number = int(match.group(1))
                    line_content = (
                        line.split("]", 1)[1].strip() if "]" in line else line
                    )
                    if line_content and len(line_content) > 1:
                        line_content = (
                            line_content[1:].strip()
                            if line_content[0] in ["+", "-", " "]
                            else line_content.strip()
                        )

                    if code_clean in line_content or line_content in code_clean:
                        return line_number

        return None

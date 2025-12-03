import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extract_json_from_markdown(text: str) -> Optional[str]:
    if not text:
        return None

    markdown_pattern = r"```(?:json)?\s*\n(.*?)\n```"

    match = re.search(markdown_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text.strip()


def parse_llm_json_response(response_text: str) -> Dict[str, Any]:
    try:
        if not response_text or not response_text.strip():
            logger.info("Empty response received, returning default structure")
            return {"issues": [], "summary": "No analysis provided"}

        clean_json = extract_json_from_markdown(response_text)

        if not clean_json:
            logger.warning("No JSON content found in response")
            response_lower = response_text.lower()
            if any(
                phrase in response_lower
                for phrase in [
                    "nenhum problema",
                    "no issues",
                    "não encontrei",
                    "sem problemas",
                    "tudo ok",
                ]
            ):
                logger.info(
                    "LLM indicated no issues found, returning empty issues array"
                )
                return {"issues": [], "summary": "No issues found"}
            return {"raw_analysis": str(response_text), "format": "text"}

        result = json.loads(clean_json)
        logger.debug(
            f"Successfully parsed JSON with keys: {result.keys() if isinstance(result, dict) else type(result)}"
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {str(e)}")
        logger.debug(
            f"Problematic content (first 1000 chars): {clean_json[:1000] if clean_json else response_text[:1000]}"
        )
        logger.debug(f"Error position: line {e.lineno}, column {e.colno}")

        if clean_json:
            lines = clean_json.split("\n")
            if e.lineno <= len(lines):
                error_line = lines[e.lineno - 1]
                logger.debug(f"Error at line {e.lineno}: {error_line}")

        response_lower = (response_text or "").lower()
        if any(
            phrase in response_lower
            for phrase in [
                "nenhum problema",
                "no issues",
                "não encontrei",
                "sem problemas",
            ]
        ):
            logger.info(
                "Detected 'no issues' message in malformed JSON, returning empty issues"
            )
            return {"issues": [], "summary": "No issues found"}

        return {"raw_analysis": str(response_text), "format": "text"}
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM response: {str(e)}")
        return {"raw_analysis": str(response_text), "format": "text"}

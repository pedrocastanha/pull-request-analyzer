import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

IGNORED_EXTENSIONS = {
    "md", "txt", "json", "yaml", "yml", "toml",
    "lock", "sum", "mod",
    "png", "jpg", "jpeg", "gif", "svg", "ico",
    "pdf", "doc", "docx",
    "csv", "xml"
}

IGNORED_PATTERNS = [
    "package-lock.json",
    "yarn.lock",
    "Pipfile.lock",
    "poetry.lock",
    "go.sum",
    ".env",
    ".gitignore",
    "LICENSE",
    "README"
]


def filter_analyzable_files(files: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    analyzable = []
    ignored = []

    for file_info in files:
        file_path = file_info.get("path", "")

        extension = file_path.split(".")[-1].lower() if "." in file_path else ""

        filename = file_path.split("/")[-1]

        should_ignore = (
            extension in IGNORED_EXTENSIONS or
            any(pattern in filename for pattern in IGNORED_PATTERNS)
        )

        if should_ignore:
            ignored.append(file_info)
            logger.debug(f"[FILTER] Ignoring file: {file_path}")
        else:
            analyzable.append(file_info)

    return analyzable, ignored
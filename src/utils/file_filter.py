import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FileFilter:
    GLOBAL_IGNORE_EXTENSIONS = {
        ".md", ".markdown", ".txt",
        ".json", ".lock",
        ".properties", ".env", ".ini", ".cfg", ".conf",
        ".jasper", ".class", ".jar", ".war", ".ear",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
        ".css", ".scss", ".less", ".sass",
        ".html", ".jrxml",
        ".xml",
        ".yaml", ".yml",
        ".gradle", 
        ".gitignore", ".dockerignore",
        ".editorconfig",
    }

    GLOBAL_IGNORE_FILES = {
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "pom.xml", "build.gradle", "settings.gradle",
        "requirements.txt", "poetry.lock", "Pipfile", "Pipfile.lock",
        "Dockerfile", "docker-compose.yml",
        "LICENSE", "CONTRIBUTING.md", "README.md", "CHANGELOG.md",
    }

    @staticmethod
    def should_ignore_change_type(change_type: str) -> bool:
        """Verifica se o tipo de mudança deve ser ignorado (ex: arquivos deletados)."""
        return change_type == "deleted"

    @staticmethod
    def should_ignore_globally(file_path: str) -> bool:
        """Verifica se o arquivo deve ser ignorado globalmente."""
        filename = file_path.split("/")[-1]
        
        if filename in FileFilter.GLOBAL_IGNORE_FILES:
            return True
            
        for ext in FileFilter.GLOBAL_IGNORE_EXTENSIONS:
            if filename.endswith(ext):
                return True
                
        return False

    @staticmethod
    def filter_files_for_agent(files: List[Dict[str, Any]], agent_name: str) -> List[Dict[str, Any]]:
        """Filtra arquivos específicos para cada agente."""
        filtered_files = []
        
        for file_info in files:
            path = file_info.get("path", "")
            
            if path.endswith(".sql"):
                if agent_name == "Performance":
                    filtered_files.append(file_info)
                continue
                
            filtered_files.append(file_info)
            
        return filtered_files

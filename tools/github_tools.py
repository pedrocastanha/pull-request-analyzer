import os
import base64
from typing import List, Dict, Optional, Tuple
from github import Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository
from langchain.tools import BaseTool
from pydantic import BaseModel
import requests

from ..models.pr_state import PRState, FileChange

class GitHubToolsConfig(BaseModel):
    """Configuração para as ferramentas GitHub"""
    token: str
    max_file_size: int = 1024 * 1024  # 1MB
    max_files: int = 50

class GitHubPRTool(BaseTool):
    """Ferramenta para buscar informações básicas do PR"""
    name = "get_pr_info"
    description = "Busca informações básicas de um Pull Request"

    def __init__(self, config: GitHubToolsConfig):
        super().__init__()
        self.github = Github(config.token)
        self.config = config

    def _run(self, repo_owner: str, repo_name: str, pr_number: int) -> Dict:
        """Busca informações do PR"""
        try:
            repo = self.github.get_repo(f"{repo_owner}/{repo_name}")
            pr = repo.get_pull(pr_number)

            return {
                "title": pr.title,
                "description": pr.body or "",
                "author": pr.user.login,
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "state": pr.state,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "commits": pr.commits,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat()
            }
        except GithubException as e:
            raise Exception(f"Erro ao buscar PR: {e}")


class GitHubFileChangesTool(BaseTool):
    """Ferramenta para buscar mudanças nos arquivos do PR"""
    name = "get_pr_file_changes"
    description = "Busca todas as mudanças de arquivos em um PR"

    def __init__(self, config: GitHubToolsConfig):
        super().__init__()
        self.github = Github(config.token)
        self.config = config

    def _run(self, repo_owner: str, repo_name: str, pr_number: int) -> List[Dict]:
        """Busca mudanças nos arquivos"""
        try:
            repo = self.github.get_repo(f"{repo_owner}/{repo_name}")
            pr = repo.get_pull(pr_number)

            files_data = []
            files = pr.get_files()

            for file in files:
                if file.changes > self.config.max_files:
                    continue

                file_data = {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch if file.patch else None
                }

                try:
                    if file.status != "added":
                        before_content = self._get_file_content(
                            repo, file.filename, pr.base.sha
                        )
                        file_data["before_content"] = before_content

                    if file.status != "removed":
                        after_content = self._get_file_content(
                            repo, file.filename, pr.head.sha
                        )
                        file_data["after_content"] = after_content

                except Exception as e:
                    file_data["content_error"] = str(e)

                files_data.append(file_data)

            return files_data

        except GithubException as e:
            raise Exception(f"Erro ao buscar mudanças: {e}")

    def _get_file_content(self, repo: Repository, filename: str, sha: str) -> Optional[str]:
        """Busca conteúdo de um arquivo específico"""
        try:
            file_content = repo.get_contents(filename, ref=sha)

            if file_content.size > self.config.max_file_size:
                return f"[ARQUIVO MUITO GRANDE: {file_content.size} bytes]"

            if file_content.encoding == "base64":
                content = base64.b64decode(file_content.content).decode('utf-8')
                return content

            return file_content.decoded_content.decode('utf-8')

        except Exception:
            return None


class GitHubDiffTool(BaseTool):
    """Ferramenta para analisar diffs detalhados"""
    name = "analyze_pr_diff"
    description = "Analisa o diff completo de um PR"

    def __init__(self, config: GitHubToolsConfig):
        super().__init__()
        self.github = Github(config.token)
        self.config = config

    def _run(self, repo_owner: str, repo_name: str, pr_number: int) -> Dict:
        """Analisa o diff do PR"""
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
            headers = {
                "Authorization": f"token {self.config.token}",
                "Accept": "application/vnd.github.v3.diff"
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            diff_content = response.text

            diff_stats = self._parse_diff_stats(diff_content)

            return {
                "full_diff": diff_content,
                "stats": diff_stats
            }

        except Exception as e:
            raise Exception(f"Erro ao analisar diff: {e}")

    def _parse_diff_stats(self, diff_content: str) -> Dict:
        """Parse básico de estatísticas do diff"""
        lines = diff_content.split('\n')

        stats = {
            "files_changed": 0,
            "additions": 0,
            "deletions": 0,
            "files": []
        }

        current_file = None

        for line in lines:
            if line.startswith("diff --git"):
                if current_file:
                    stats["files"].append(current_file)

                parts = line.split()
                filename = parts[2][2:]
                current_file = {
                    "filename": filename,
                    "additions": 0,
                    "deletions": 0
                }
                stats["files_changed"] += 1

            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    current_file["additions"] += 1
                stats["additions"] += 1

            elif line.startswith("-") and not line.startswith("---"):
                if current_file:
                    current_file["deletions"] += 1
                stats["deletions"] += 1

        if current_file:
            stats["files"].append(current_file)

        return stats


class GitHubToolsManager:
    """Gerenciador de todas as ferramentas GitHub"""

    def __init__(self, token: str):
        self.config = GitHubToolsConfig(token=token)
        self.pr_tool = GitHubPRTool(self.config)
        self.files_tool = GitHubFileChangesTool(self.config)
        self.diff_tool = GitHubDiffTool(self.config)

    def get_all_tools(self) -> List[BaseTool]:
        return [
            self.pr_tool,
            self.files_tool,
            self.diff_tool
        ]

    async def collect_pr_data(self, state: PRState) -> PRState:
        """Coleta todos os dados necessários do PR"""
        state.log(f"Coletando dados do PR #{state.pr_number}")

        try:
            pr_info = self.pr_tool._run(
                state.repo_owner,
                state.repo_name,
                state.pr_number
            )

            state.pr_title = pr_info["title"]
            state.pr_description = pr_info["description"]
            state.pr_author = pr_info["author"]
            state.base_branch = pr_info["base_branch"]
            state.head_branch = pr_info["head_branch"]
            state.total_additions = pr_info["additions"]
            state.total_deletions = pr_info["deletions"]

            state.log(f"PR encontrado: '{state.pr_title}' por {state.pr_author}")

            files_data = self.files_tool._run(
                state.repo_owner,
                state.repo_name,
                state.pr_number
            )

            for file_data in files_data:
                file_change = FileChange(**file_data)
                state.files_changed.append(file_change)

            state.log(f"Arquivos analisados: {len(state.files_changed)}")

            return state

        except Exception as e:
            state.add_error(f"Erro ao coletar dados: {str(e)}")
            return state
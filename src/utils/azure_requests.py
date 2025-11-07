import logging
import requests
from typing import Dict, List, Optional
from difflib import unified_diff
from src.settings import Settings

logger = logging.getLogger(__name__)

headers = {
        "Authorization": f"Bearer {Settings.AZURE_OAUTH_TOKEN}",
        "Content-Type": "application/json"
    }

class AzureManager:
    @staticmethod
    def get_pr_details(pr_id: int) -> Optional[Dict]:
        logger.info(f"Fetching PR #{pr_id} details from Azure DevOps")
        try:
            url = f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/pullrequests/{pr_id}/commits?api-version={Settings.AZURE_API_VERSION}"

            logger.info(f"Requesting URL: {url}")

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            commits = data.get('value', [])
            logger.info(f"Found {len(commits)} commit(s) in PR #{pr_id}")

            processed_commits = []
            for commit in commits:
                commit_id = commit.get('commitId')
                if not commit_id:
                    continue

                logger.info(f"Processing commit {commit_id[:8]} from PR #{pr_id}")
                commit_details = AzureManager.process_commit_changes(commit_id)

                if commit_details:
                    commit_details['author'] = commit.get('author', {}).get('name')
                    commit_details['comment'] = commit.get('comment')
                    commit_details['committer'] = commit.get('committer', {}).get('name')
                    processed_commits.append(commit_details)

            total_files = sum(c['summary']['total_files'] for c in processed_commits)
            total_additions = sum(c['summary']['total_additions'] for c in processed_commits)
            total_deletions = sum(c['summary']['total_deletions'] for c in processed_commits)

            result = {
                'pr_id': pr_id,
                'total_commits': len(processed_commits),
                'commits': processed_commits,
                'summary': {
                    'total_files_changed': total_files,
                    'total_additions': total_additions,
                    'total_deletions': total_deletions,
                    'total_commits': len(processed_commits)
                }
            }

            logger.info(f"✓ PR #{pr_id} processed: {len(processed_commits)} commits, "
                       f"{total_files} files, +{total_additions}/-{total_deletions}")

            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching PR #{pr_id}: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching PR #{pr_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching PR #{pr_id}: {str(e)}")
            return None

    @staticmethod
    def get_commit_changes(id: str):
        logger.info(f"Fetching commit changes from Azure DevOps")
        try:
            url = (f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/diffs/commits?api-version={Settings.AZURE_API_VERSION}&"
                   f"baseVersionType=branch&baseVersion=develop&targetVersionType=commit&targetVersion={id}&diffCommonCommit=true&$top=100")

            response = requests.get(url, headers=headers)
            data = response.json()
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error fetching commit changes: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching commit changes: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching commit changes: {str(e)}")
            return None

    @staticmethod
    def get_old_file_content(commonCommit: str, path: str) -> Optional[str]:
        logger.info(f"Fetching old file content: {path} @ {commonCommit[:8]}")
        try:
            clean_path = path.lstrip('/')
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/items"
                f"?path={clean_path}&versionType=commit&version={commonCommit}"
                f"&api-version={Settings.AZURE_API_VERSION}")

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Old file not found (might be new file): {path}")
                return None
            logger.error(f"HTTP error fetching old content: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error fetching old file content: {str(e)}")
            return None

    @staticmethod
    def get_target_file_content(commitId: str, path: str) -> Optional[str]:
        logger.info(f"Fetching target file content: {path} @ {commitId[:8]}")
        try:
            clean_path = path.lstrip('/')
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/items"
                f"?path={clean_path}&versionType=commit&version={commitId}"
                f"&api-version={Settings.AZURE_API_VERSION}")

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Target file not found (might be deleted): {path}")
                return None
            logger.error(f"HTTP error fetching target content: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error fetching target file content: {str(e)}")
            return None

    @staticmethod
    def calculate_diff(old_content: Optional[str], new_content: Optional[str], file_path: str) -> Dict:
        if old_content is None and new_content is not None:
            new_lines = new_content.splitlines(keepends=True)
            return {
                'path': file_path,
                'change_type': 'added',
                'old_lines': 0,
                'new_lines': len(new_lines),
                'diff': ''.join(f'+ {line}' for line in new_lines),
                'additions': len(new_lines),
                'deletions': 0
            }

        if old_content is not None and new_content is None:
            old_lines = old_content.splitlines(keepends=True)
            return {
                'path': file_path,
                'change_type': 'deleted',
                'old_lines': len(old_lines),
                'new_lines': 0,
                'diff': ''.join(f'- {line}' for line in old_lines),
                'additions': 0,
                'deletions': len(old_lines)
            }

        if old_content is None and new_content is None:
            logger.warning(f"Both contents are None for {file_path}")
            return {
                'path': file_path,
                'change_type': 'error',
                'old_lines': 0,
                'new_lines': 0,
                'diff': '',
                'additions': 0,
                'deletions': 0
            }

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile=f'a{file_path}',
            tofile=f'b{file_path}',
            lineterm=''
        )
        diff_text = '\n'.join(diff)

        additions = sum(1 for line in diff_text.split('\n') if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff_text.split('\n') if line.startswith('-') and not line.startswith('---'))

        return {
            'path': file_path,
            'change_type': 'modified',
            'old_lines': len(old_lines),
            'new_lines': len(new_lines),
            'diff': diff_text,
            'additions': additions,
            'deletions': deletions
        }

    @staticmethod
    def process_commit_changes(commit_id: str) -> Optional[Dict]:
        logger.info(f"Processing commit {commit_id[:8]}...")

        changes_data = AzureManager.get_commit_changes(commit_id)
        if not changes_data:
            logger.error(f"Failed to fetch changes for commit {commit_id}")
            return None

        file_changes = [
            change for change in changes_data.get('changes', [])
            if not change.get('item', {}).get('isFolder', False)
        ]

        logger.info(f"Found {len(file_changes)} file(s) changed in commit {commit_id[:8]}")

        processed_files = []
        common_commit = changes_data.get('commonCommit')
        target_commit = changes_data.get('targetCommit')

        for change in file_changes:
            item = change.get('item', {})
            file_path = item.get('path')

            if not file_path:
                logger.warning("Change without file path, skipping...")
                continue

            logger.info(f"Processing file: {file_path}")

            old_content = AzureManager.get_old_file_content(common_commit, file_path)

            new_content = AzureManager.get_target_file_content(target_commit, file_path)

            diff_result = AzureManager.calculate_diff(old_content, new_content, file_path)

            diff_result['change_type_azure'] = change.get('changeType')  # 'add', 'edit', 'delete'
            diff_result['object_id'] = item.get('objectId')

            processed_files.append(diff_result)

        total_additions = sum(f['additions'] for f in processed_files)
        total_deletions = sum(f['deletions'] for f in processed_files)
        total_files = len(processed_files)

        result = {
            'commit_id': commit_id,
            'common_commit': common_commit,
            'target_commit': target_commit,
            'files_changed': processed_files,
            'summary': {
                'total_files': total_files,
                'total_additions': total_additions,
                'total_deletions': total_deletions,
                'files_added': sum(1 for f in processed_files if f['change_type'] == 'added'),
                'files_deleted': sum(1 for f in processed_files if f['change_type'] == 'deleted'),
                'files_modified': sum(1 for f in processed_files if f['change_type'] == 'modified'),
            }
        }

        logger.info(f"✓ Commit {commit_id[:8]} processed: "
                   f"{total_files} files, +{total_additions}/-{total_deletions}")

        return result



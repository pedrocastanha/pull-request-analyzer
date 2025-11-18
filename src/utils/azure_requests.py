import logging
import requests
from typing import Dict, List, Optional, Any
from difflib import unified_diff
from src.settings import Settings

logger = logging.getLogger(__name__)

headers = {
    "Authorization": f"Bearer {Settings.AZURE_OAUTH_TOKEN}",
    "Content-Type": "application/json",
}


class AzureManager:
    @staticmethod
    def get_pr_consolidated_changes(pr_id: int) -> Optional[Dict]:
        logger.info(
            f"Fetching consolidated changes for PR #{pr_id} (branch comparison)"
        )
        try:
            pr_url = f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/pullrequests/{pr_id}?api-version={Settings.AZURE_API_VERSION}"

            logger.debug(f"Fetching PR info: {pr_url}")
            pr_response = requests.get(pr_url, headers=headers)
            pr_response.raise_for_status()
            pr_info = pr_response.json()

            source_ref = pr_info.get("sourceRefName")
            target_ref = pr_info.get("targetRefName")

            if not source_ref or not target_ref:
                logger.error(f"Missing branch references in PR #{pr_id}")
                return None

            source_branch = source_ref.replace("refs/heads/", "")
            target_branch = target_ref.replace("refs/heads/", "")

            logger.info(f"Comparing branches: {source_branch} → {target_branch}")

            diff_url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/diffs/commits?"
                f"api-version={Settings.AZURE_API_VERSION}&"
                f"baseVersionType=branch&baseVersion={target_branch}&"
                f"targetVersionType=branch&targetVersion={source_branch}&"
                f"diffCommonCommit=true&$top=1000"
            )

            logger.debug(f"Fetching branch diff: {diff_url}")
            diff_response = requests.get(diff_url, headers=headers)
            diff_response.raise_for_status()
            changes_data = diff_response.json()

            file_changes = [
                change
                for change in changes_data.get("changes", [])
                if not change.get("item", {}).get("isFolder", False)
            ]

            logger.info(f"Found {len(file_changes)} file(s) changed in PR #{pr_id}")

            processed_files = []
            common_commit = changes_data.get("commonCommit")
            target_commit = changes_data.get("targetCommit")

            for change in file_changes:
                item = change.get("item", {})
                file_path = item.get("path")

                if not file_path:
                    logger.warning("Change without file path, skipping...")
                    continue

                logger.debug(f"Processing file: {file_path}")

                old_content = AzureManager.get_old_file_content(
                    common_commit, file_path
                )
                new_content = AzureManager.get_target_file_content(
                    target_commit, file_path
                )

                diff_result = AzureManager.calculate_diff(
                    old_content, new_content, file_path
                )

                diff_result["change_type_azure"] = change.get("changeType")
                diff_result["object_id"] = item.get("objectId")

                processed_files.append(diff_result)

            total_additions = sum(f["additions"] for f in processed_files)
            total_deletions = sum(f["deletions"] for f in processed_files)
            total_files = len(processed_files)

            result = {
                "pr_id": pr_id,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "total_files": total_files,
                "total_additions": total_additions,
                "total_deletions": total_deletions,
                "files": processed_files,
            }

            logger.info(
                f"✓ PR #{pr_id} consolidated ({source_branch} → {target_branch}): "
                f"{total_files} files, +{total_additions}/-{total_deletions} lines"
            )

            return result

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error fetching PR #{pr_id}: {e.response.status_code} - {e.response.text}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching PR #{pr_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching PR #{pr_id}: {str(e)}", exc_info=True
            )
            return None

    @staticmethod
    def get_commit_changes(id: str):
        logger.debug(f"Fetching commit changes from Azure DevOps")
        try:
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/diffs/commits?api-version={Settings.AZURE_API_VERSION}&"
                f"baseVersionType=branch&baseVersion=develop&targetVersionType=commit&targetVersion={id}&diffCommonCommit=true&$top=100"
            )

            response = requests.get(url, headers=headers)
            data = response.json()
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error fetching commit changes: {e.response.status_code} - {e.response.text}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching commit changes: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching commit changes: {str(e)}")
            return None

    @staticmethod
    def get_old_file_content(commonCommit: str, path: str) -> Optional[str]:
        logger.debug(f"Fetching old file content: {path} @ {commonCommit[:8]}")
        try:
            clean_path = path.lstrip("/")
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/items"
                f"?path={clean_path}&versionType=commit&version={commonCommit}"
                f"&api-version={Settings.AZURE_API_VERSION}"
            )

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Old file not found (might be new file): {path}")
                return None
            logger.error(
                f"HTTP error fetching old content: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching old file content: {str(e)}")
            return None

    @staticmethod
    def get_target_file_content(commitId: str, path: str) -> Optional[str]:
        logger.debug(f"Fetching target file content: {path} @ {commitId[:8]}")
        try:
            clean_path = path.lstrip("/")
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/items"
                f"?path={clean_path}&versionType=commit&version={commitId}"
                f"&api-version={Settings.AZURE_API_VERSION}"
            )

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Target file not found (might be deleted): {path}")
                return None
            logger.error(
                f"HTTP error fetching target content: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching target file content: {str(e)}")
            return None

    @staticmethod
    def calculate_diff(
        old_content: Optional[str], new_content: Optional[str], file_path: str
    ) -> Dict:
        if old_content is None and new_content is not None:
            new_lines = new_content.splitlines(keepends=True)
            return {
                "path": file_path,
                "change_type": "added",
                "old_lines": 0,
                "new_lines": len(new_lines),
                "diff": "".join(f"+ {line}" for line in new_lines),
                "additions": len(new_lines),
                "deletions": 0,
            }

        if old_content is not None and new_content is None:
            old_lines = old_content.splitlines(keepends=True)
            return {
                "path": file_path,
                "change_type": "deleted",
                "old_lines": len(old_lines),
                "new_lines": 0,
                "diff": "".join(f"- {line}" for line in old_lines),
                "additions": 0,
                "deletions": len(old_lines),
            }

        if old_content is None and new_content is None:
            logger.warning(f"Both contents are None for {file_path}")
            return {
                "path": file_path,
                "change_type": "error",
                "old_lines": 0,
                "new_lines": 0,
                "diff": "",
                "additions": 0,
                "deletions": 0,
            }

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a{file_path}",
            tofile=f"b{file_path}",
            lineterm="",
        )
        diff_text = "\n".join(diff)

        additions = sum(
            1
            for line in diff_text.split("\n")
            if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1
            for line in diff_text.split("\n")
            if line.startswith("-") and not line.startswith("---")
        )

        return {
            "path": file_path,
            "change_type": "modified",
            "old_lines": len(old_lines),
            "new_lines": len(new_lines),
            "diff": diff_text,
            "additions": additions,
            "deletions": deletions,
        }

    @staticmethod
    def create_pr_thread(
        pr_id: int,
        file_path: str,
        line_number: Optional[int] = None,
        comment_text: str = "",
    ) -> Optional[Dict]:
        logger.info(f"Creating comment thread on PR #{pr_id} for file {file_path}")

        try:
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/"
                f"pullRequests/{pr_id}/threads?api-version={Settings.AZURE_API_VERSION}"
            )

            payload = {
                "comments": [
                    {
                        "content": comment_text,
                        "commentType": 1
                    }
                ],
                "status": 1,
            }

            if line_number is not None:
                payload["threadContext"] = {
                    "filePath": file_path,
                    "rightFileStart": {"line": line_number, "offset": 1},
                    "rightFileEnd": {"line": line_number, "offset": 1000}
                }

            logger.debug(f"Payload: {payload}")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            thread_data = response.json()
            thread_id = thread_data.get("id")

            logger.info(f"✓ Thread #{thread_id} created successfully on PR #{pr_id}")
            return thread_data

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error creating thread on PR #{pr_id}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error creating thread: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating thread: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def add_comment_to_thread(
        pr_id: int,
        thread_id: int,
        comment_text: str,
        parent_comment_id: Optional[int] = None,
    ) -> Optional[Dict]:
        logger.info(f"Adding comment to thread #{thread_id} on PR #{pr_id}")

        try:
            url = (
                f"{Settings.AZURE_BASE_URL}/repositories/{Settings.AZURE_REPOSITORY_ID}/"
                f"pullRequests/{pr_id}/threads/{thread_id}/comments?"
                f"api-version={Settings.AZURE_API_VERSION}"
            )

            payload = {
                "content": comment_text,
                "commentType": 1
            }

            if parent_comment_id is not None:
                payload["parentCommentId"] = parent_comment_id

            logger.debug(f"Payload: {payload}")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            comment_data = response.json()
            comment_id = comment_data.get("id")

            logger.info(
                f"✓ Comment #{comment_id} added to thread #{thread_id} on PR #{pr_id}"
            )
            return comment_data

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error adding comment to thread #{thread_id}: "
                f"{e.response.status_code} - {e.response.text}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error adding comment: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error adding comment: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def publish_analysis_comments(pr_id: int, comments: List[Dict]) -> Dict[str, Any]:
        logger.info(f"Publishing analysis comments to PR #{pr_id}")

        stats = {
            "total_comments": 0,
            "successful": 0,
            "failed": 0,
            "threads_created": [],
            "errors": []
        }

        try:
            for comment in comments:
                stats["total_comments"] += 1

                file_path = comment.get("file", "")
                line_number = comment.get("line")
                message = comment.get("message", "")

                thread_result = AzureManager.create_pr_thread(
                    pr_id=pr_id,
                    file_path=file_path,
                    line_number=line_number,
                    comment_text=message
                )

                if thread_result:
                    stats["successful"] += 1
                    stats["threads_created"].append(thread_result.get("id"))
                else:
                    stats["failed"] += 1
                    stats["errors"].append({
                        "file": file_path,
                        "line": line_number,
                        "error": "Failed to create thread"
                    })

            logger.info(
                f"✓ Published {stats['successful']}/{stats['total_comments']} comments "
                f"to PR #{pr_id}"
            )

        except Exception as e:
            logger.error(f"Error publishing comments: {str(e)}", exc_info=True)
            stats["errors"].append({"error": str(e)})

        return stats

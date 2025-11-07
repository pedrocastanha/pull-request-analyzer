import logging
import requests
from src.settings import Settings

logger = logging.getLogger(__name__)

class AzureManager:
    @staticmethod
    def get_pr_details(pr_id: int):
        logger.info(f"Fetching PR #{pr_id} details from Azure DevOps")
        try:
            headers = {
                "Authorization": f"Bearer {Settings.AZURE_OAUTH_TOKEN}",
                "Content-Type": "application/json",
                "api-version": Settings.AZURE_API_VERSION or "7.1"
            }
            url = f"{Settings.AZURE_BASE_URL}/pullrequests/{pr_id}"

            logger.info(f"Requesting URL: {url}")

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully fetched PR #{pr_id}")
            return data
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching PR #{pr_id}: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching PR #{pr_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching PR #{pr_id}: {str(e)}")
            return None

    def get_commit_changes(pr_id: int):
        https: // dev.azure.com / unifatecie / Zeus / _apis / git / repositories / 4
        f02b789 - 1
        da4 - 4
        d6f - 9
        f7f - 875625
        ec8086 / diffs / commits?api - version = 7.2 - preview
        .1 & baseVersionType = branch & baseVersion = develop & targetVersionType = commit & targetVersion = 5e658
        dadde17e1a66203e3371adf346cd6267c77 & diffCommonCommit = true &$top = 100
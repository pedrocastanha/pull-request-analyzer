import json
import logging
from typing import List, Dict, Any, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from src.settings import Settings
from src.providers.prompts.classifier import Classifier

logger = logging.getLogger(__name__)


class IssueClassifier:

    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        self.model_name = model_name
        self.llm: Optional[ChatGroq] = None

        try:
            if not Settings.GROQ_API_KEY:
                logger.warning("[CLASSIFIER] ⚠️ GROQ_API_KEY not found - classifier disabled")
                return

            self.llm = ChatGroq(
                model=model_name,
                temperature=0.0,
                groq_api_key=Settings.GROQ_API_KEY,
            )
            logger.info(f"[CLASSIFIER] ✓ Initialized with model: {model_name}")

        except Exception as e:
            logger.error(f"[CLASSIFIER] ❌ Failed to initialize Groq: {e}")
            self.llm = None

    def classify_issues(
        self,
        agent_type: str,
        issues: List[Dict[str, Any]],
        code_context: str,
    ) -> List[Dict[str, Any]]:
        if not self.llm or not issues:
            logger.warning("[CLASSIFIER] ⚠️ Classifier not available or no issues - using default category")
            for issue in issues:
                issue['category'] = 'SUGGESTION'  # Conservative default
            return issues

        try:
            logger.info(f"[CLASSIFIER] 🔍 Classifying {len(issues)} issues from {agent_type} agent...")

            user_prompt = self._build_classification_prompt(agent_type, issues, code_context)

            messages = [
                SystemMessage(content=Classifier.SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)

            classifications = self._parse_classification_response(response.content)

            classified_issues = self._apply_classifications(issues, classifications)

            problem_count = sum(1 for i in classified_issues if i.get('category') == 'PROBLEM')
            suggestion_count = sum(1 for i in classified_issues if i.get('category') == 'SUGGESTION')

            logger.info(
                f"[CLASSIFIER] ✓ Classification complete: "
                f"{problem_count} PROBLEM, {suggestion_count} SUGGESTION"
            )

            return classified_issues

        except Exception as e:
            logger.error(f"[CLASSIFIER] ❌ Classification failed: {e}")
            for issue in issues:
                issue['category'] = 'SUGGESTION'
            return issues

    def _build_classification_prompt(
        self,
        agent_type: str,
        issues: List[Dict[str, Any]],
        code_context: str,
    ) -> str:

        issues_summary = []
        for idx, issue in enumerate(issues):
            issues_summary.append(
                f"**Issue {idx}:**\n"
                f"- Type: {issue.get('type', 'Unknown')}\n"
                f"- File: {issue.get('file', 'Unknown')}\n"
                f"- Line: {issue.get('line', '?')}\n"
                f"- Description: {issue.get('description', '')}\n"
                f"- Impact: {issue.get('impact', '')}\n"
            )

        prompt = f"""
        Agent Type: **{agent_type}**
        
        Number of Issues: {len(issues)}
        
        ## Issues to Classify:
        
        {chr(10).join(issues_summary)}
        
        ## Code Context:
        
        ```
        {code_context}
        ```
        
        Please classify each issue (by index) as PROBLEM or SUGGESTION.
"""
        return prompt

    def _parse_classification_response(self, response_text: str) -> List[Dict[str, Any]]:
        try:
            response_text = response_text.strip()

            if "```json" in response_text:
                start = response_text.index("```json") + 7
                end = response_text.rindex("```")
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.index("```") + 3
                end = response_text.rindex("```")
                response_text = response_text[start:end].strip()

            data = json.loads(response_text)
            return data.get("classifications", [])

        except Exception as e:
            logger.error(f"[CLASSIFIER] ❌ Failed to parse classification response: {e}")
            return []

    def _apply_classifications(
        self,
        issues: List[Dict[str, Any]],
        classifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        category_map = {}
        for classification in classifications:
            idx = classification.get('index')
            category = classification.get('category', 'PROBLEM')
            category_map[idx] = category

        for idx, issue in enumerate(issues):
            category = category_map.get(idx, 'SUGGESTION')
            issue['category'] = category

        return issues

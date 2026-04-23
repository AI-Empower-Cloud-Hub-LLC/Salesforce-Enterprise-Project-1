from typing import Dict, Any, List
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class SearchKnowledgeBaseTool(BaseTool):
    """Searches knowledge base for relevant articles and solutions."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="SearchKnowledgeBaseTool",
            description="Searches knowledge base articles for solutions to support issues",
            category="support",
            version="1.0.0",
            required_inputs={"query": "str"},
            optional_inputs={"limit": "int", "category": "str"},
            output_schema={
                "articles": "list",
                "result_count": "int",
                "query": "str",
                "searched_at": "str",
            },
            auth_required=False,
            rate_limit_per_minute=100,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Search knowledge base for articles."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="search_knowledge_base",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            query = inputs.get("query")
            limit = inputs.get("limit", 10)
            category = inputs.get("category")

            articles = self._search_articles(query, category, limit)

            result_data = {
                "articles": articles,
                "result_count": len(articles),
                "query": query,
                "category": category,
                "searched_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Knowledge base search completed",
                query=query,
                result_count=len(articles),
            )

            return IntegrationResult(
                operation_id="search_knowledge_base",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error searching knowledge base: {str(e)}"
            logger.error("Knowledge base search failed", error=str(e))
            return IntegrationResult(
                operation_id="search_knowledge_base",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _search_articles(
        self, query: str, category: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search knowledge base articles (mock)."""
        # In production, this would perform full-text search against KB
        return [
            {
                "id": "kb_1",
                "title": "Common Issues and Solutions",
                "content": f"This article addresses: {query}",
                "category": category or "General",
                "relevance_score": 0.95,
                "updated_at": datetime.utcnow().isoformat(),
            },
        ]

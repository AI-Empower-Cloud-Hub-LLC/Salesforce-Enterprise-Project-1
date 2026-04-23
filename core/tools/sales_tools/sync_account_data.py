from typing import Dict, Any, List
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class SyncAccountDataTool(BaseTool):
    """Bidirectional sync between Salesforce and external database."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="SyncAccountDataTool",
            description="Syncs account data bidirectionally between Salesforce and external DB with conflict resolution",
            category="sales",
            version="1.0.0",
            required_inputs={"account_ids": "str", "sync_direction": "str"},
            optional_inputs={},
            output_schema={
                "synced_count": "int",
                "conflict_count": "int",
                "conflicts": "list",
                "sync_direction": "str",
                "synced_at": "str",
            },
            auth_required=True,
            rate_limit_per_minute=30,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Sync account data between systems."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="sync_account_data",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            account_ids_str = inputs.get("account_ids", "")
            sync_direction = inputs.get("sync_direction", "bidirectional")

            # Validate sync direction
            valid_directions = ["salesforce_to_db", "db_to_salesforce", "bidirectional"]
            if sync_direction not in valid_directions:
                error = f"Invalid sync direction. Must be one of: {valid_directions}"
                logger.warn("Invalid sync direction", direction=sync_direction)
                return IntegrationResult(
                    operation_id="sync_account_data",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            # Parse account IDs
            account_ids = [
                aid.strip() for aid in account_ids_str.split(",") if aid.strip()
            ]

            if not account_ids:
                account_ids = self._get_all_account_ids()

            # Perform sync
            synced_count, conflicts = self._perform_sync(
                account_ids, sync_direction
            )

            result_data = {
                "synced_count": synced_count,
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
                "sync_direction": sync_direction,
                "synced_at": datetime.utcnow().isoformat(),
                "account_ids_count": len(account_ids),
            }

            logger.info(
                "Account data sync completed",
                synced_count=synced_count,
                conflict_count=len(conflicts),
                direction=sync_direction,
            )

            return IntegrationResult(
                operation_id="sync_account_data",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error syncing account data: {str(e)}"
            logger.error("Account data sync failed", error=str(e))
            return IntegrationResult(
                operation_id="sync_account_data",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _get_all_account_ids(self) -> List[str]:
        """Get all account IDs (mock)."""
        return []

    def _perform_sync(
        self, account_ids: List[str], direction: str
    ) -> tuple[int, List[Dict[str, Any]]]:
        """Perform the sync operation (mock)."""
        # In production, this would:
        # 1. Fetch accounts from source system
        # 2. Fetch accounts from target system
        # 3. Compare timestamps
        # 4. Resolve conflicts via timestamp comparison
        # 5. Update target system
        return len(account_ids), []

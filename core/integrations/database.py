"""Database integration connector."""

from typing import Any, Dict, Optional, List
import json
from datetime import datetime
from threading import RLock

import structlog

from core.integrations.base import IntegrationBackend, IntegrationResult

logger = structlog.get_logger(__name__)


class DatabaseConnector(IntegrationBackend):
    """Database integration backend for SQL-based data sources."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize database connector.

        Args:
            name: Integration name
            config: Configuration with db_type, host, port, database, username, password, etc.
        """
        super().__init__(name, config)
        self.db_type = config.get("db_type", "postgresql").lower()
        self.host = config.get("host")
        self.port = config.get("port")
        self.database = config.get("database")
        self.username = config.get("username")
        self.password = config.get("password")
        self.pool_size = config.get("pool_size", 5)
        self.timeout = config.get("timeout", 30)

        self._connection_pool = None
        self._lock = RLock()
        self._query_count = 0
        self._last_query_time: Optional[datetime] = None

    def authenticate(self) -> bool:
        """Authenticate and initialize database connection pool."""
        try:
            self._init_connection_pool()

            if self.db_type == "postgresql":
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT version();")
                        version = cursor.fetchone()[0]
                        logger.info("postgresql_authenticated", version=version)
            elif self.db_type == "mysql":
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT VERSION();")
                        version = cursor.fetchone()[0]
                        logger.info("mysql_authenticated", version=version)
            elif self.db_type == "sqlite":
                with self._get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT sqlite_version();")
                        version = cursor.fetchone()[0]
                        logger.info("sqlite_authenticated", version=version)
            else:
                logger.error("unsupported_db_type", db_type=self.db_type)
                return False

            self._is_healthy = True
            return True

        except Exception as e:
            logger.error("database_authentication_failed", db_type=self.db_type, error=str(e))
            self._is_healthy = False
            return False

    def execute_query(
        self, query: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> IntegrationResult:
        """
        Execute query or operation against database.

        Args:
            query: Query specification with 'sql' and optionally 'params'
            context: Optional execution context

        Returns:
            IntegrationResult with operation outcome
        """
        if not self.authenticate():
            return IntegrationResult(
                success=False,
                error="Database authentication failed",
            )

        try:
            sql = query.get("sql")
            params = query.get("params", {})
            operation_type = query.get("type", "query")

            if not sql:
                return IntegrationResult(success=False, error="Missing SQL query")

            if operation_type == "query":
                return self._execute_select(sql, params)
            elif operation_type == "execute":
                return self._execute_dml(sql, params)
            elif operation_type == "bulk":
                return self._execute_bulk(query)
            else:
                return IntegrationResult(
                    success=False,
                    error=f"Unknown operation type: {operation_type}",
                )

        except Exception as e:
            logger.error("database_query_execution_failed", error=str(e))
            return IntegrationResult(
                success=False,
                error=str(e),
            )

    def _execute_select(self, sql: str, params: Dict[str, Any]) -> IntegrationResult:
        """Execute SELECT query and return results."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()

                    records = [dict(zip(columns, row)) for row in rows]

                    self._query_count += 1
                    self._last_query_time = datetime.utcnow()

                    return IntegrationResult(
                        success=True,
                        data={
                            "records": records,
                            "row_count": len(records),
                            "columns": columns,
                        },
                    )

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _execute_dml(self, sql: str, params: Dict[str, Any]) -> IntegrationResult:
        """Execute INSERT, UPDATE, or DELETE operation."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()

                    rows_affected = cursor.rowcount

                    self._query_count += 1
                    self._last_query_time = datetime.utcnow()

                    return IntegrationResult(
                        success=True,
                        data={
                            "rows_affected": rows_affected,
                            "operation": "dml",
                        },
                    )

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _execute_bulk(self, query: Dict[str, Any]) -> IntegrationResult:
        """Execute bulk operations (multiple statements)."""
        try:
            statements = query.get("statements", [])
            results = []

            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    for stmt in statements:
                        sql = stmt.get("sql")
                        params = stmt.get("params", {})
                        stmt_type = stmt.get("type", "execute")

                        try:
                            cursor.execute(sql, params)
                            if stmt_type == "query":
                                rows = cursor.fetchall()
                                results.append({
                                    "success": True,
                                    "rows": len(rows) if rows else 0,
                                })
                            else:
                                conn.commit()
                                results.append({
                                    "success": True,
                                    "rows_affected": cursor.rowcount,
                                })
                        except Exception as e:
                            results.append({
                                "success": False,
                                "error": str(e),
                            })

                self._query_count += len(statements)
                self._last_query_time = datetime.utcnow()

                return IntegrationResult(
                    success=True,
                    data={
                        "results": results,
                        "total_statements": len(statements),
                    },
                )

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def health_check(self) -> bool:
        """Check database connection availability."""
        try:
            self.authenticate()

            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if self.db_type in ["postgresql", "mysql"]:
                        cursor.execute("SELECT 1;")
                    elif self.db_type == "sqlite":
                        cursor.execute("SELECT 1;")
                    else:
                        return False

                    cursor.fetchone()

            self._is_healthy = True
            return True

        except Exception as e:
            logger.warning("database_health_check_failed", db_type=self.db_type, error=str(e))
            self._is_healthy = False
            return False

    def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        List available database resources.

        Args:
            resource_type: Type of resource ('tables', 'schemas', 'columns', etc.)

        Returns:
            List of available resources
        """
        if not self.authenticate():
            return []

        try:
            if resource_type == "tables":
                return self._list_tables()
            elif resource_type == "schemas":
                return self._list_schemas()
            elif resource_type == "columns":
                return self._list_columns()
            else:
                return []

        except Exception as e:
            logger.warning(
                "database_list_resources_failed",
                resource_type=resource_type,
                error=str(e),
            )
            return []

    def _list_tables(self) -> List[Dict[str, Any]]:
        """List all tables in database."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if self.db_type == "postgresql":
                        cursor.execute("""
                            SELECT table_name FROM information_schema.tables
                            WHERE table_schema = 'public'
                            ORDER BY table_name;
                        """)
                    elif self.db_type == "mysql":
                        cursor.execute(f"SHOW TABLES FROM {self.database};")
                    elif self.db_type == "sqlite":
                        cursor.execute("""
                            SELECT name FROM sqlite_master
                            WHERE type='table'
                            ORDER BY name;
                        """)
                    else:
                        return []

                    tables = cursor.fetchall()
                    return [
                        {
                            "name": table[0],
                            "type": "table",
                        }
                        for table in tables
                    ]

        except Exception as e:
            logger.error("database_list_tables_failed", error=str(e))
            return []

    def _list_schemas(self) -> List[Dict[str, Any]]:
        """List all schemas in database."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if self.db_type == "postgresql":
                        cursor.execute("""
                            SELECT schema_name FROM information_schema.schemata
                            WHERE schema_name NOT LIKE 'pg_%'
                            ORDER BY schema_name;
                        """)
                        schemas = cursor.fetchall()
                        return [
                            {
                                "name": schema[0],
                                "type": "schema",
                            }
                            for schema in schemas
                        ]
                    else:
                        return [{"name": self.database, "type": "database"}]

        except Exception as e:
            logger.error("database_list_schemas_failed", error=str(e))
            return []

    def _list_columns(self) -> List[Dict[str, Any]]:
        """List all columns across all tables."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if self.db_type == "postgresql":
                        cursor.execute("""
                            SELECT table_name, column_name, data_type
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                            ORDER BY table_name, ordinal_position;
                        """)
                    elif self.db_type == "mysql":
                        cursor.execute(f"""
                            SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = '{self.database}'
                            ORDER BY TABLE_NAME, ORDINAL_POSITION;
                        """)
                    elif self.db_type == "sqlite":
                        cursor.execute("""
                            SELECT m.name as table_name, p.name as column_name, p.type as data_type
                            FROM sqlite_master m, pragma_table_info(m.name) p
                            WHERE m.type='table'
                            ORDER BY m.name, p.cid;
                        """)
                    else:
                        return []

                    columns = cursor.fetchall()
                    return [
                        {
                            "table": col[0],
                            "name": col[1],
                            "type": col[2],
                        }
                        for col in columns
                    ]

        except Exception as e:
            logger.error("database_list_columns_failed", error=str(e))
            return []

    def _init_connection_pool(self) -> None:
        """Initialize database connection pool based on database type."""
        if self._connection_pool:
            return

        try:
            if self.db_type == "postgresql":
                import psycopg2.pool
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1,
                    self.pool_size,
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    connect_timeout=self.timeout,
                )
            elif self.db_type == "mysql":
                import mysql.connector
                # MySQL doesn't have a built-in pool in the standard driver
                # We create a simple connection for now
                self._connection_pool = {
                    "config": {
                        "host": self.host,
                        "port": self.port,
                        "database": self.database,
                        "user": self.username,
                        "password": self.password,
                        "connect_timeout": self.timeout,
                    }
                }
            elif self.db_type == "sqlite":
                import sqlite3
                # SQLite handles one connection per file
                self._connection_pool = {
                    "path": self.host or ":memory:",
                    "timeout": self.timeout,
                }
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")

        except Exception as e:
            logger.error("connection_pool_init_failed", db_type=self.db_type, error=str(e))
            raise

    def _get_connection(self):
        """Get a database connection from pool."""
        if not self._connection_pool:
            self._init_connection_pool()

        try:
            if self.db_type == "postgresql":
                import psycopg2
                return self._connection_pool.getconn()
            elif self.db_type == "mysql":
                import mysql.connector
                return mysql.connector.connect(**self._connection_pool["config"])
            elif self.db_type == "sqlite":
                import sqlite3
                return sqlite3.connect(self._connection_pool["path"], timeout=self._connection_pool["timeout"])
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")

        except Exception as e:
            logger.error("get_connection_failed", db_type=self.db_type, error=str(e))
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        status = super().get_status()
        status.update({
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "query_count": self._query_count,
            "last_query_time": self._last_query_time.isoformat() if self._last_query_time else None,
            "pool_size": self.pool_size,
        })
        return status

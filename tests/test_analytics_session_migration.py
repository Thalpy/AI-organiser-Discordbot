"""
Test analytics and session management migration.

This test ensures that the analytics and session management migration script
creates all necessary tables, indexes, views, and functions correctly.
"""

import re
from pathlib import Path
import pytest


def test_analytics_migration_file_exists():
    """Test that the analytics migration file exists."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    assert migration_path.exists(), "Analytics migration file does not exist"
    assert migration_path.is_file(), "Analytics migration path is not a file"


def test_session_management_tables():
    """Test that session management tables are created."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for session management tables
    session_tables = [
        "user_sessions",
        "api_keys"
    ]
    
    for table in session_tables:
        pattern = rf"CREATE TABLE.*{table}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Session table {table} not found in migration"


def test_analytics_tables():
    """Test that analytics tables are created."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for analytics tables
    analytics_tables = [
        "productivity_goals",
        "user_activity_log",
        "daily_analytics",
        "weekly_analytics",
        "api_usage_log",
        "system_metrics"
    ]
    
    for table in analytics_tables:
        pattern = rf"CREATE TABLE.*{table}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Analytics table {table} not found in migration"


def test_user_sessions_columns():
    """Test that user_sessions table has required columns."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for specific columns in user_sessions
    required_columns = [
        "session_token",
        "discord_token",
        "refresh_token",
        "expires_at",
        "last_activity",
        "ip_address",
        "user_agent",
        "device_info",
        "is_active"
    ]
    
    for column in required_columns:
        pattern = rf"{column}.*"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in user_sessions table"


def test_api_keys_columns():
    """Test that api_keys table has required columns."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for specific columns in api_keys
    required_columns = [
        "api_key_hash",
        "api_key_prefix",
        "permissions",
        "scopes",
        "rate_limit_per_minute",
        "rate_limit_per_hour",
        "rate_limit_per_day",
        "last_used_at",
        "usage_count",
        "expires_at"
    ]
    
    for column in required_columns:
        pattern = rf"{column}.*"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in api_keys table"


def test_productivity_goals_structure():
    """Test that productivity_goals table has proper structure."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for specific columns in productivity_goals
    required_columns = [
        "goal_type",
        "title",
        "target_value",
        "current_value",
        "unit",
        "period_type",
        "start_date",
        "end_date",
        "is_active",
        "is_achieved",
        "priority",
        "category"
    ]
    
    for column in required_columns:
        pattern = rf"{column}.*"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in productivity_goals table"


def test_user_activity_log_structure():
    """Test that user_activity_log table has proper structure."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for specific columns in user_activity_log
    required_columns = [
        "activity_type",
        "activity_category",
        "activity_data",
        "source",
        "source_details",
        "session_id",
        "api_key_id",
        "task_id",
        "success",
        "duration_ms"
    ]
    
    for column in required_columns:
        pattern = rf"{column}.*"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in user_activity_log table"


def test_analytics_aggregation_tables():
    """Test that analytics aggregation tables are properly structured."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for daily_analytics columns
    daily_columns = [
        "tasks_created",
        "tasks_completed",
        "tasks_cancelled",
        "total_task_time_minutes",
        "productivity_score",
        "completion_rate",
        "on_time_completion_rate"
    ]
    
    for column in daily_columns:
        pattern = rf"{column}.*"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in daily_analytics table"
    
    # Check for weekly_analytics columns
    weekly_columns = [
        "year",
        "week",
        "week_start_date",
        "avg_productivity_score",
        "avg_completion_rate",
        "goals_achieved",
        "streak_days"
    ]
    
    for column in weekly_columns:
        pattern = rf"{column}.*"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in weekly_analytics table"


def test_indexes_created():
    """Test that proper indexes are created for all tables."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for key indexes
    expected_indexes = [
        "idx_user_sessions_user_id",
        "idx_user_sessions_session_token",
        "idx_user_sessions_expires_at",
        "idx_api_keys_user_id",
        "idx_api_keys_api_key_hash",
        "idx_productivity_goals_user_id",
        "idx_productivity_goals_goal_type",
        "idx_user_activity_log_user_id",
        "idx_user_activity_log_activity_type",
        "idx_daily_analytics_user_id",
        "idx_daily_analytics_date",
        "idx_weekly_analytics_user_id",
        "idx_api_usage_log_api_key_id",
        "idx_system_metrics_metric_name"
    ]
    
    for index in expected_indexes:
        pattern = rf"CREATE INDEX.*{index}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Index {index} not found in migration"


def test_gin_indexes_for_json_arrays():
    """Test that GIN indexes are created for JSON and array columns."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for GIN indexes
    gin_indexes = [
        "idx_api_keys_scopes.*USING GIN",
        "idx_productivity_goals_tags.*USING GIN",
        "idx_system_metrics_tags.*USING GIN"
    ]
    
    for index_pattern in gin_indexes:
        assert re.search(index_pattern, migration_sql, re.IGNORECASE), f"GIN index pattern {index_pattern} not found"


def test_unique_constraints():
    """Test that unique constraints are properly defined."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for unique constraints
    unique_patterns = [
        r"session_token.*UNIQUE",
        r"api_key_hash.*UNIQUE",
        r"UNIQUE.*user_id.*date",  # daily_analytics
        r"UNIQUE.*user_id.*year.*week"  # weekly_analytics
    ]
    
    for pattern in unique_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Unique constraint pattern {pattern} not found"


def test_check_constraints():
    """Test that check constraints are properly defined."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for check constraints
    check_patterns = [
        r"priority.*CHECK.*>=.*1.*<=.*5",
        r"week.*CHECK.*>=.*1.*<=.*53"
    ]
    
    for pattern in check_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Check constraint pattern {pattern} not found"


def test_foreign_key_references():
    """Test that foreign key references are properly defined."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for foreign key references
    fk_patterns = [
        r"session_id.*REFERENCES.*user_sessions",
        r"api_key_id.*REFERENCES.*api_keys",
        r"task_id.*REFERENCES.*tasks"
    ]
    
    for pattern in fk_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Foreign key pattern {pattern} not found"


def test_jsonb_columns_with_defaults():
    """Test that JSONB columns have proper default values."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for JSONB columns with defaults
    jsonb_patterns = [
        r"device_info.*JSONB.*DEFAULT.*'{}'::jsonb",
        r"permissions.*JSONB.*DEFAULT.*'\[\]'::jsonb",
        r"activity_data.*JSONB.*DEFAULT.*'{}'::jsonb",
        r"metadata.*JSONB.*DEFAULT.*'{}'::jsonb",
        r"tags.*JSONB.*DEFAULT.*'{}'::jsonb"
    ]
    
    for pattern in jsonb_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"JSONB pattern {pattern} not found"


def test_array_columns_with_defaults():
    """Test that array columns have proper default values."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for array columns with defaults
    array_patterns = [
        r"scopes.*TEXT\[\].*DEFAULT.*ARRAY\[\]::TEXT\[\]",
        r"tags.*TEXT\[\].*DEFAULT.*ARRAY\[\]::TEXT\[\]"
    ]
    
    for pattern in array_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Array pattern {pattern} not found"


def test_triggers_created():
    """Test that triggers are created for updated_at columns."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for triggers
    trigger_patterns = [
        r"CREATE TRIGGER.*update_api_keys_updated_at",
        r"CREATE TRIGGER.*update_productivity_goals_updated_at",
        r"CREATE TRIGGER.*update_daily_analytics_updated_at",
        r"CREATE TRIGGER.*update_weekly_analytics_updated_at"
    ]
    
    for pattern in trigger_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Trigger pattern {pattern} not found"


def test_analytics_views_created():
    """Test that analytics views are created."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for analytics views
    analytics_views = [
        "user_productivity_summary",
        "api_usage_summary",
        "session_activity_summary",
        "goal_progress_summary"
    ]
    
    for view in analytics_views:
        pattern = rf"CREATE.*VIEW.*{view}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Analytics view {view} not found in migration"


def test_cleanup_function_created():
    """Test that cleanup function is created."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for cleanup function
    assert "CREATE OR REPLACE FUNCTION cleanup_old_analytics_data()" in migration_sql
    assert "DELETE FROM user_activity_log" in migration_sql
    assert "DELETE FROM api_usage_log" in migration_sql
    assert "DELETE FROM user_sessions" in migration_sql


def test_sample_data_insertion():
    """Test that sample data is properly inserted."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for sample data insertion
    assert "INSERT INTO productivity_goals" in migration_sql, "No sample productivity goals insertion found"
    assert "completion_rate" in migration_sql, "No completion_rate goal type found"
    assert "daily_tasks" in migration_sql, "No daily_tasks goal type found"
    assert "ON CONFLICT DO NOTHING" in migration_sql, "No conflict handling for sample data"


def test_comments_and_documentation():
    """Test that proper comments and documentation are included."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for comments
    assert "COMMENT ON TABLE" in migration_sql, "No table comments found"
    assert "COMMENT ON COLUMN" in migration_sql, "No column comments found"
    
    # Check for specific table comments
    table_comments = [
        "user_sessions",
        "api_keys",
        "productivity_goals",
        "user_activity_log",
        "daily_analytics",
        "weekly_analytics",
        "api_usage_log",
        "system_metrics"
    ]
    
    for table in table_comments:
        pattern = rf"COMMENT ON TABLE.*{table}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Comment for table {table} not found"


def test_rate_limiting_columns():
    """Test that rate limiting columns are properly defined."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for rate limiting columns in api_keys
    rate_limit_columns = [
        "rate_limit_per_minute",
        "rate_limit_per_hour", 
        "rate_limit_per_day"
    ]
    
    for column in rate_limit_columns:
        pattern = rf"{column}.*INTEGER.*DEFAULT"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Rate limit column {column} not properly defined"


def test_analytics_aggregation_logic():
    """Test that analytics views have proper aggregation logic."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for aggregation functions in views
    aggregation_patterns = [
        r"COUNT.*DISTINCT",
        r"AVG.*productivity_score",
        r"MAX.*last_active",
        r"ROUND.*",
        r"NULLIF.*COUNT"
    ]
    
    for pattern in aggregation_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Aggregation pattern {pattern} not found in views"


def test_migration_is_idempotent():
    """Test that the migration uses IF NOT EXISTS for idempotency."""
    migration_path = Path("database/migrations/003_analytics_session_management.sql")
    migration_sql = migration_path.read_text()
    
    # Check for IF NOT EXISTS usage
    assert "CREATE TABLE IF NOT EXISTS" in migration_sql, "No IF NOT EXISTS for table creation"
    assert "CREATE INDEX IF NOT EXISTS" in migration_sql, "No IF NOT EXISTS for index creation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
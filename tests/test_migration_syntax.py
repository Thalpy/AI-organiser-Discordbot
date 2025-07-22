"""
Test database migration SQL syntax and structure.

This test validates the SQL migration script without requiring a database connection.
"""

import re
from pathlib import Path
import pytest


def test_migration_file_exists():
    """Test that the migration file exists."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    assert migration_path.exists(), "Migration file does not exist"
    assert migration_path.is_file(), "Migration path is not a file"


def test_migration_sql_syntax():
    """Test basic SQL syntax in the migration file."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for basic SQL keywords
    assert "CREATE TABLE" in migration_sql, "No CREATE TABLE statements found"
    assert "CREATE INDEX" in migration_sql, "No CREATE INDEX statements found"
    assert ("CREATE VIEW" in migration_sql or "CREATE OR REPLACE VIEW" in migration_sql), "No CREATE VIEW statements found"
    
    # Check for proper semicolon termination
    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
    non_comment_statements = [stmt for stmt in statements if not stmt.startswith('--')]
    
    # Should have multiple SQL statements
    assert len(non_comment_statements) > 10, "Too few SQL statements in migration"


def test_required_tables_defined():
    """Test that all required tables are defined in the migration."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    required_tables = [
        "task_assignments",
        "task_messages",
        "task_templates", 
        "recurring_tasks",
        "template_permissions",
        "task_activity_log"
    ]
    
    for table in required_tables:
        pattern = rf"CREATE TABLE.*{table}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Table {table} not found in migration"


def test_required_indexes_defined():
    """Test that required indexes are defined in the migration."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    required_indexes = [
        "idx_task_assignments_task_id",
        "idx_task_assignments_assigned_user_id",
        "idx_task_messages_task_id",
        "idx_task_messages_user_id",
        "idx_task_templates_created_by_user_id",
        "idx_recurring_tasks_user_id"
    ]
    
    for index in required_indexes:
        pattern = rf"CREATE INDEX.*{index}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Index {index} not found in migration"


def test_required_views_defined():
    """Test that required views are defined in the migration."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_sql = migration_path.read_text()
    
    required_views = [
        "task_collaboration_summary",
        "active_recurring_tasks"
    ]
    
    for view in required_views:
        pattern = rf"CREATE.*VIEW.*{view}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"View {view} not found in migration"


def test_foreign_key_constraints():
    """Test that foreign key constraints are properly defined."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for REFERENCES keywords indicating foreign keys
    fk_patterns = [
        r"task_id.*REFERENCES.*tasks",
        r"template_id.*REFERENCES.*task_templates",
        r"parent_message_id.*REFERENCES.*task_messages"
    ]
    
    for pattern in fk_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Foreign key pattern {pattern} not found"


def test_check_constraints():
    """Test that check constraints are properly defined."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for CHECK constraints
    check_patterns = [
        r"status.*CHECK.*assigned.*accepted.*declined.*completed",
        r"message_type.*CHECK.*comment.*status_update.*system",
        r"default_priority.*CHECK.*low.*normal.*high.*urgent"
    ]
    
    for pattern in check_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Check constraint pattern {pattern} not found"


def test_trigger_functions():
    """Test that trigger functions are defined."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for trigger function
    assert "CREATE OR REPLACE FUNCTION update_updated_at_column()" in migration_sql
    assert "CREATE TRIGGER" in migration_sql
    assert "update_updated_at_column()" in migration_sql


def test_jsonb_columns():
    """Test that JSONB columns are properly defined."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for JSONB columns
    jsonb_patterns = [
        r"template_data.*JSONB",
        r"recurrence_pattern.*JSONB", 
        r"metadata.*JSONB",
        r"activity_data.*JSONB"
    ]
    
    for pattern in jsonb_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"JSONB pattern {pattern} not found"


def test_timestamp_columns():
    """Test that timestamp columns are properly defined."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for timestamp columns with timezone
    timestamp_patterns = [
        r"created_at.*TIMESTAMP WITH TIME ZONE.*DEFAULT CURRENT_TIMESTAMP",
        r"updated_at.*TIMESTAMP WITH TIME ZONE.*DEFAULT CURRENT_TIMESTAMP",
        r"assigned_at.*TIMESTAMP WITH TIME ZONE",
        r"completed_at.*TIMESTAMP WITH TIME ZONE"
    ]
    
    for pattern in timestamp_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Timestamp pattern {pattern} not found"


def test_unique_constraints():
    """Test that unique constraints are properly defined."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for unique constraints
    unique_patterns = [
        r"UNIQUE.*task_id.*assigned_user_id",
        r"UNIQUE.*template_id.*user_id"
    ]
    
    for pattern in unique_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Unique constraint pattern {pattern} not found"


def test_comments_and_documentation():
    """Test that the migration includes proper comments and documentation."""
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Check for comments
    assert "COMMENT ON TABLE" in migration_sql, "No table comments found"
    assert "COMMENT ON COLUMN" in migration_sql, "No column comments found"
    
    # Check for header comments
    assert "Migration:" in migration_sql, "No migration header found"
    assert "Description:" in migration_sql, "No description found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Test enhanced tables migration for existing table modifications.

This test ensures that the enhanced tables migration script correctly
adds new columns and tables to existing structures.
"""

import re
from pathlib import Path
import pytest


def test_enhanced_migration_file_exists():
    """Test that the enhanced migration file exists."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    assert migration_path.exists(), "Enhanced migration file does not exist"
    assert migration_path.is_file(), "Enhanced migration path is not a file"


def test_tasks_table_enhancements():
    """Test that tasks table gets proper enhancements."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for ALTER TABLE tasks statements
    assert "ALTER TABLE tasks" in migration_sql, "No ALTER TABLE tasks found"
    
    # Check for specific new columns
    required_columns = [
        "is_collaborative",
        "created_by_user_id", 
        "collaboration_notes",
        "completion_percentage",
        "template_id",
        "recurring_task_id",
        "assigned_users",
        "metadata",
        "tags"
    ]
    
    for column in required_columns:
        pattern = rf"ADD COLUMN.*{column}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in tasks table enhancement"


def test_notification_preferences_enhancements():
    """Test that notification_preferences table gets proper enhancements."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for ALTER TABLE notification_preferences statements
    assert "ALTER TABLE notification_preferences" in migration_sql, "No ALTER TABLE notification_preferences found"
    
    # Check for specific new columns
    required_columns = [
        "email_notifications",
        "web_push_notifications",
        "email_address",
        "push_endpoint",
        "notification_channels",
        "quiet_hours_enabled",
        "notification_frequency",
        "digest_enabled"
    ]
    
    for column in required_columns:
        pattern = rf"ADD COLUMN.*{column}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in notification_preferences enhancement"


def test_user_preferences_enhancements():
    """Test that user_preferences table gets proper enhancements."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for ALTER TABLE user_preferences statements
    assert "ALTER TABLE user_preferences" in migration_sql, "No ALTER TABLE user_preferences found"
    
    # Check for specific new columns
    required_columns = [
        "theme",
        "language",
        "date_format",
        "time_format",
        "calendar_integration_enabled",
        "productivity_goals",
        "ui_preferences"
    ]
    
    for column in required_columns:
        pattern = rf"ADD COLUMN.*{column}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Column {column} not found in user_preferences enhancement"


def test_new_tables_created():
    """Test that new tables are created in the migration."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for new tables
    new_tables = [
        "user_profiles",
        "calendar_integrations",
        "notification_history",
        "task_dependencies"
    ]
    
    for table in new_tables:
        pattern = rf"CREATE TABLE.*{table}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"New table {table} not found in migration"


def test_enhanced_views_created():
    """Test that enhanced views are created."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for enhanced views
    enhanced_views = [
        "enhanced_task_summary",
        "user_activity_summary",
        "notification_delivery_stats"
    ]
    
    for view in enhanced_views:
        pattern = rf"CREATE.*VIEW.*{view}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Enhanced view {view} not found in migration"


def test_indexes_for_new_columns():
    """Test that indexes are created for new columns."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for indexes on new columns
    expected_indexes = [
        "idx_tasks_is_collaborative",
        "idx_tasks_created_by_user_id",
        "idx_tasks_completion_percentage",
        "idx_notification_preferences_email_notifications",
        "idx_user_preferences_theme",
        "idx_user_profiles_display_name",
        "idx_calendar_integrations_user_id",
        "idx_notification_history_user_id"
    ]
    
    for index in expected_indexes:
        pattern = rf"CREATE INDEX.*{index}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Index {index} not found in migration"


def test_gin_indexes_for_arrays():
    """Test that GIN indexes are created for array columns."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for GIN indexes on array columns
    gin_indexes = [
        "idx_tasks_assigned_users.*USING GIN",
        "idx_tasks_tags.*USING GIN",
        "idx_user_profiles_skills.*USING GIN"
    ]
    
    for index_pattern in gin_indexes:
        assert re.search(index_pattern, migration_sql, re.IGNORECASE), f"GIN index pattern {index_pattern} not found"


def test_check_constraints_added():
    """Test that check constraints are properly added."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for check constraints
    check_patterns = [
        r"completion_percentage.*CHECK.*>=.*0.*<=.*100",
        r"theme.*CHECK.*light.*dark.*auto",
        r"notification_frequency.*CHECK.*immediate.*hourly.*daily.*weekly",
        r"availability_status.*CHECK.*available.*busy.*away.*offline"
    ]
    
    for pattern in check_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Check constraint pattern {pattern} not found"


def test_foreign_key_references():
    """Test that foreign key references are properly added."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for foreign key references
    fk_patterns = [
        r"template_id.*REFERENCES.*task_templates",
        r"recurring_task_id.*REFERENCES.*recurring_tasks",
        r"task_id.*REFERENCES.*tasks",
        r"depends_on_task_id.*REFERENCES.*tasks"
    ]
    
    for pattern in fk_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Foreign key pattern {pattern} not found"


def test_unique_constraints():
    """Test that unique constraints are properly defined."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for unique constraints
    unique_patterns = [
        r"UNIQUE.*user_id.*provider.*calendar_id",
        r"UNIQUE.*task_id.*depends_on_task_id"
    ]
    
    for pattern in unique_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Unique constraint pattern {pattern} not found"


def test_jsonb_columns_with_defaults():
    """Test that JSONB columns have proper default values."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for JSONB columns with defaults
    jsonb_patterns = [
        r"metadata.*JSONB.*DEFAULT.*'{}'::jsonb",
        r"notification_channels.*JSONB.*DEFAULT.*discord.*email.*web_push",
        r"productivity_goals.*JSONB.*DEFAULT.*'{}'::jsonb",
        r"ui_preferences.*JSONB.*DEFAULT.*'{}'::jsonb"
    ]
    
    for pattern in jsonb_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"JSONB pattern {pattern} not found"


def test_array_columns_with_defaults():
    """Test that array columns have proper default values."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for array columns with defaults
    array_patterns = [
        r"assigned_users.*TEXT\[\].*DEFAULT.*ARRAY\[\]::TEXT\[\]",
        r"tags.*TEXT\[\].*DEFAULT.*ARRAY\[\]::TEXT\[\]",
        r"skills.*TEXT\[\].*DEFAULT.*ARRAY\[\]::TEXT\[\]"
    ]
    
    for pattern in array_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Array pattern {pattern} not found"


def test_triggers_for_updated_at():
    """Test that triggers are created for updated_at columns."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for triggers
    trigger_patterns = [
        r"CREATE TRIGGER.*update_user_profiles_updated_at",
        r"CREATE TRIGGER.*update_calendar_integrations_updated_at"
    ]
    
    for pattern in trigger_patterns:
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Trigger pattern {pattern} not found"


def test_sample_data_insertion():
    """Test that sample data is properly inserted."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for sample data insertion
    assert "INSERT INTO user_profiles" in migration_sql, "No sample user profiles insertion found"
    assert "ON CONFLICT" in migration_sql, "No conflict handling for sample data"
    assert "UPDATE tasks" in migration_sql, "No existing tasks update found"


def test_comments_and_documentation():
    """Test that proper comments and documentation are included."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for comments
    assert "COMMENT ON TABLE" in migration_sql, "No table comments found"
    assert "COMMENT ON COLUMN" in migration_sql, "No column comments found"
    
    # Check for specific table comments
    table_comments = [
        "user_profiles",
        "calendar_integrations", 
        "notification_history",
        "task_dependencies"
    ]
    
    for table in table_comments:
        pattern = rf"COMMENT ON TABLE.*{table}"
        assert re.search(pattern, migration_sql, re.IGNORECASE), f"Comment for table {table} not found"


def test_migration_is_idempotent():
    """Test that the migration uses IF NOT EXISTS for idempotency."""
    migration_path = Path("database/migrations/002_enhance_existing_tables.sql")
    migration_sql = migration_path.read_text()
    
    # Check for IF NOT EXISTS usage
    assert "ADD COLUMN IF NOT EXISTS" in migration_sql, "No IF NOT EXISTS for column additions"
    assert "CREATE TABLE IF NOT EXISTS" in migration_sql, "No IF NOT EXISTS for table creation"
    assert "CREATE INDEX IF NOT EXISTS" in migration_sql, "No IF NOT EXISTS for index creation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
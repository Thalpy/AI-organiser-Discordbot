"""
Test database migration for multi-user collaboration features.

This test ensures that the database migration script creates all necessary
tables, indexes, and constraints correctly.
"""

import asyncio
import os
import pytest
import asyncpg
from pathlib import Path
from typing import AsyncGenerator


@pytest.fixture
async def db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Create a test database connection."""
    # Use test database URL or create a temporary one
    database_url = os.getenv(
        "TEST_DATABASE_URL", 
        "postgresql://taskbot:taskbot_password@localhost:5432/taskbot_test"
    )
    
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def clean_database(db_connection: asyncpg.Connection) -> None:
    """Clean the database before and after tests."""
    # Drop tables if they exist (in reverse dependency order)
    tables_to_drop = [
        "task_activity_log",
        "template_permissions", 
        "recurring_tasks",
        "task_templates",
        "task_messages",
        "task_assignments"
    ]
    
    for table in tables_to_drop:
        await db_connection.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    
    # Drop views
    views_to_drop = [
        "task_collaboration_summary",
        "active_recurring_tasks"
    ]
    
    for view in views_to_drop:
        await db_connection.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
    
    # Drop function
    await db_connection.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")


@pytest.mark.asyncio
@pytest.mark.database
async def test_migration_creates_tables(db_connection: asyncpg.Connection, clean_database):
    """Test that the migration creates all required tables."""
    # Read and execute the migration script
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Execute the migration
    await db_connection.execute(migration_sql)
    
    # Check that all tables were created
    expected_tables = [
        "task_assignments",
        "task_messages", 
        "task_templates",
        "recurring_tasks",
        "template_permissions",
        "task_activity_log"
    ]
    
    for table in expected_tables:
        result = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
            """,
            table
        )
        assert result is True, f"Table {table} was not created"


@pytest.mark.asyncio
@pytest.mark.database
async def test_migration_creates_indexes(db_connection: asyncpg.Connection, clean_database):
    """Test that the migration creates all required indexes."""
    # Read and execute the migration script
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Execute the migration
    await db_connection.execute(migration_sql)
    
    # Check that indexes were created
    expected_indexes = [
        "idx_task_assignments_task_id",
        "idx_task_assignments_assigned_user_id",
        "idx_task_messages_task_id",
        "idx_task_messages_user_id",
        "idx_task_templates_created_by_user_id",
        "idx_recurring_tasks_user_id"
    ]
    
    for index in expected_indexes:
        result = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname = $1
            )
            """,
            index
        )
        assert result is True, f"Index {index} was not created"


@pytest.mark.asyncio
@pytest.mark.database
async def test_migration_creates_views(db_connection: asyncpg.Connection, clean_database):
    """Test that the migration creates all required views."""
    # First, we need to create a basic tasks table for the views to work
    await db_connection.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            is_collaborative BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Read and execute the migration script
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    
    # Execute the migration
    await db_connection.execute(migration_sql)
    
    # Check that views were created
    expected_views = [
        "task_collaboration_summary",
        "active_recurring_tasks"
    ]
    
    for view in expected_views:
        result = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.views 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
            """,
            view
        )
        assert result is True, f"View {view} was not created"


@pytest.mark.asyncio
@pytest.mark.database
async def test_task_assignments_constraints(db_connection: asyncpg.Connection, clean_database):
    """Test task_assignments table constraints and functionality."""
    # Create basic tasks table first
    await db_connection.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            is_collaborative BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Execute migration
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    await db_connection.execute(migration_sql)
    
    # Insert a test task
    task_id = await db_connection.fetchval(
        "INSERT INTO tasks (description) VALUES ('Test task') RETURNING id"
    )
    
    # Test successful assignment
    assignment_id = await db_connection.fetchval("""
        INSERT INTO task_assignments (task_id, assigned_user_id, assigned_by_user_id)
        VALUES ($1, 'user123', 'user456')
        RETURNING id
    """, task_id)
    
    assert assignment_id is not None
    
    # Test unique constraint (should fail)
    with pytest.raises(asyncpg.UniqueViolationError):
        await db_connection.execute("""
            INSERT INTO task_assignments (task_id, assigned_user_id, assigned_by_user_id)
            VALUES ($1, 'user123', 'user789')
        """, task_id)
    
    # Test status constraint (should fail with invalid status)
    with pytest.raises(asyncpg.CheckViolationError):
        await db_connection.execute("""
            INSERT INTO task_assignments (task_id, assigned_user_id, assigned_by_user_id, status)
            VALUES ($1, 'user999', 'user456', 'invalid_status')
        """, task_id)


@pytest.mark.asyncio
@pytest.mark.database
async def test_task_messages_functionality(db_connection: asyncpg.Connection, clean_database):
    """Test task_messages table functionality."""
    # Create basic tasks table first
    await db_connection.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            is_collaborative BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Execute migration
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    await db_connection.execute(migration_sql)
    
    # Insert a test task
    task_id = await db_connection.fetchval(
        "INSERT INTO tasks (description) VALUES ('Test task') RETURNING id"
    )
    
    # Test message insertion
    message_id = await db_connection.fetchval("""
        INSERT INTO task_messages (task_id, user_id, message, message_type)
        VALUES ($1, 'user123', 'This is a test message', 'comment')
        RETURNING id
    """, task_id)
    
    assert message_id is not None
    
    # Test reply message (parent_message_id)
    reply_id = await db_connection.fetchval("""
        INSERT INTO task_messages (task_id, user_id, message, message_type, parent_message_id)
        VALUES ($1, 'user456', 'This is a reply', 'comment', $2)
        RETURNING id
    """, task_id, message_id)
    
    assert reply_id is not None
    
    # Test message type constraint (should fail with invalid type)
    with pytest.raises(asyncpg.CheckViolationError):
        await db_connection.execute("""
            INSERT INTO task_messages (task_id, user_id, message, message_type)
            VALUES ($1, 'user789', 'Invalid message', 'invalid_type')
        """, task_id)


@pytest.mark.asyncio
@pytest.mark.database
async def test_task_templates_functionality(db_connection: asyncpg.Connection, clean_database):
    """Test task_templates table functionality."""
    # Execute migration
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    await db_connection.execute(migration_sql)
    
    # Test template creation
    template_id = await db_connection.fetchval("""
        INSERT INTO task_templates (
            created_by_user_id, 
            name, 
            description, 
            template_data,
            is_shared
        )
        VALUES (
            'user123', 
            'Test Template', 
            'A test template', 
            '{"duration": 30, "priority": "high"}'::jsonb,
            true
        )
        RETURNING id
    """)
    
    assert template_id is not None
    
    # Test template data retrieval
    template_data = await db_connection.fetchval(
        "SELECT template_data FROM task_templates WHERE id = $1",
        template_id
    )
    
    assert template_data is not None
    assert template_data["duration"] == 30
    assert template_data["priority"] == "high"
    
    # Test priority constraint (should fail with invalid priority)
    with pytest.raises(asyncpg.CheckViolationError):
        await db_connection.execute("""
            INSERT INTO task_templates (
                created_by_user_id, 
                name, 
                default_priority
            )
            VALUES ('user456', 'Invalid Template', 'invalid_priority')
        """)


@pytest.mark.asyncio
@pytest.mark.database
async def test_recurring_tasks_functionality(db_connection: asyncpg.Connection, clean_database):
    """Test recurring_tasks table functionality."""
    # Execute migration
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    await db_connection.execute(migration_sql)
    
    # Create a template first
    template_id = await db_connection.fetchval("""
        INSERT INTO task_templates (created_by_user_id, name, template_data)
        VALUES ('user123', 'Recurring Template', '{"duration": 15}'::jsonb)
        RETURNING id
    """)
    
    # Test recurring task creation
    recurring_id = await db_connection.fetchval("""
        INSERT INTO recurring_tasks (
            template_id,
            user_id,
            name,
            recurrence_pattern,
            next_creation_date
        )
        VALUES (
            $1,
            'user123',
            'Daily Standup',
            '{"type": "daily", "time": "09:00"}'::jsonb,
            CURRENT_TIMESTAMP + INTERVAL '1 day'
        )
        RETURNING id
    """, template_id)
    
    assert recurring_id is not None
    
    # Test that the view includes this recurring task
    active_tasks = await db_connection.fetch(
        "SELECT * FROM active_recurring_tasks WHERE id = $1",
        recurring_id
    )
    
    assert len(active_tasks) == 1
    assert active_tasks[0]["template_name"] == "Recurring Template"


@pytest.mark.asyncio
@pytest.mark.database
async def test_updated_at_triggers(db_connection: asyncpg.Connection, clean_database):
    """Test that updated_at triggers work correctly."""
    # Execute migration
    migration_path = Path("database/migrations/001_multi_user_collaboration.sql")
    migration_sql = migration_path.read_text()
    await db_connection.execute(migration_sql)
    
    # Test with task_templates
    template_id = await db_connection.fetchval("""
        INSERT INTO task_templates (created_by_user_id, name, template_data)
        VALUES ('user123', 'Test Template', '{}'::jsonb)
        RETURNING id
    """)
    
    # Get initial timestamps
    initial_times = await db_connection.fetchrow(
        "SELECT created_at, updated_at FROM task_templates WHERE id = $1",
        template_id
    )
    
    # Wait a moment and update
    await asyncio.sleep(0.1)
    await db_connection.execute(
        "UPDATE task_templates SET name = 'Updated Template' WHERE id = $1",
        template_id
    )
    
    # Get updated timestamps
    updated_times = await db_connection.fetchrow(
        "SELECT created_at, updated_at FROM task_templates WHERE id = $1",
        template_id
    )
    
    # created_at should remain the same, updated_at should be different
    assert initial_times["created_at"] == updated_times["created_at"]
    assert initial_times["updated_at"] != updated_times["updated_at"]
    assert updated_times["updated_at"] > initial_times["updated_at"]


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
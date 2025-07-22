"""Tests for enhanced calendar integration database migration"""

import pytest
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, Any

from utils.database import get_database_manager


class MockDatabaseManager:
    """Mock database manager for testing"""
    
    async def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Mock execute query - simulates table existence"""
        if "information_schema.tables" in query:
            if fetch_one:
                return {"exists": True}
        elif "information_schema.columns" in query:
            if fetch_all:
                return [
                    {"column_name": "calendar_sync_enabled"},
                    {"column_name": "last_calendar_sync"},
                    {"column_name": "calendar_conflict_resolution"},
                    {"column_name": "calendar_sync_interval_minutes"},
                    {"column_name": "calendar_event_id"},
                    {"column_name": "duration_minutes"},
                    {"column_name": "location"}
                ]
        elif "information_schema.views" in query:
            if fetch_one:
                return {"exists": True}
        elif "information_schema.routines" in query:
            if fetch_one:
                return {"exists": True}
        elif "SELECT COUNT(*)" in query:
            if fetch_one:
                return {"count": 1}
        elif "RETURNING id" in query:
            if fetch_one:
                return {"id": 1}
        elif "cleanup_expired_webhooks" in query:
            if fetch_one:
                return {"cleanup_expired_webhooks": 1}
        elif "get_user_sync_stats" in query:
            if fetch_one:
                return {
                    "total_tasks": 3,
                    "synced_tasks": 2,
                    "sync_coverage": 66.67,
                    "last_sync": datetime.now()
                }
        elif "calendar_sync_status" in query:
            if fetch_one:
                return {
                    "user_id": "test_view_user",
                    "calendar_sync_enabled": True,
                    "calendar_conflict_resolution": "task_wins",
                    "total_tasks": 1,
                    "synced_tasks": 0,
                    "sync_coverage_percentage": 0.0
                }
        elif "user_calendar_credentials" in query and "SELECT" in query:
            if fetch_one:
                return {
                    "user_id": "test_user_123",
                    "credentials_data": {"token": "test_token"},
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
        elif "task_calendar_sync" in query and "SELECT" in query:
            if fetch_one:
                return {
                    "task_id": 1,
                    "calendar_event_id": "test_calendar_event_123",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
        elif "calendar_webhook_subscriptions" in query and "SELECT" in query:
            if fetch_one:
                return {
                    "user_id": "test_user_123",
                    "resource_id": "test_resource_123",
                    "channel_id": "test_channel_123",
                    "expiration": datetime.now() + timedelta(hours=24)
                }
        elif fetch_all:
            return [{"id": 1, "user_id": "test_user"}]
        return None


class TestEnhancedCalendarMigration:
    """Test cases for the enhanced calendar integration migration"""
    
    @pytest.fixture
    def db_manager(self):
        """Get database manager for testing"""
        return MockDatabaseManager()
    
    @pytest.mark.asyncio
    async def test_user_calendar_credentials_table_exists(self, db_manager):
        """Test that user_calendar_credentials table was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_calendar_credentials'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_task_calendar_sync_table_exists(self, db_manager):
        """Test that task_calendar_sync table was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'task_calendar_sync'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_calendar_webhook_subscriptions_table_exists(self, db_manager):
        """Test that calendar_webhook_subscriptions table was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'calendar_webhook_subscriptions'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_calendar_sync_log_table_exists(self, db_manager):
        """Test that calendar_sync_log table was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'calendar_sync_log'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_calendar_conflict_log_table_exists(self, db_manager):
        """Test that calendar_conflict_log table was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'calendar_conflict_log'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_user_preferences_calendar_columns_added(self, db_manager):
        """Test that calendar-related columns were added to user_preferences"""
        query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_preferences' 
            AND column_name IN (
                'calendar_sync_enabled', 
                'last_calendar_sync', 
                'calendar_conflict_resolution',
                'calendar_sync_interval_minutes'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_all=True)
        column_names = [row['column_name'] for row in result]
        
        expected_columns = [
            'calendar_sync_enabled',
            'last_calendar_sync',
            'calendar_conflict_resolution',
            'calendar_sync_interval_minutes'
        ]
        
        for column in expected_columns:
            assert column in column_names
    
    @pytest.mark.asyncio
    async def test_tasks_calendar_columns_added(self, db_manager):
        """Test that calendar-related columns were added to tasks table"""
        query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks' 
            AND column_name IN ('calendar_event_id', 'duration_minutes', 'location');
        """
        
        result = await db_manager.execute_query(query, fetch_all=True)
        column_names = [row['column_name'] for row in result]
        
        expected_columns = ['calendar_event_id', 'duration_minutes', 'location']
        
        for column in expected_columns:
            assert column in column_names
    
    @pytest.mark.asyncio
    async def test_calendar_sync_status_view_exists(self, db_manager):
        """Test that calendar_sync_status view was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.views 
                WHERE table_name = 'calendar_sync_status'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_webhooks_function_exists(self, db_manager):
        """Test that cleanup_expired_webhooks function was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.routines 
                WHERE routine_name = 'cleanup_expired_webhooks'
                AND routine_type = 'FUNCTION'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_get_user_sync_stats_function_exists(self, db_manager):
        """Test that get_user_sync_stats function was created"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.routines 
                WHERE routine_name = 'get_user_sync_stats'
                AND routine_type = 'FUNCTION'
            );
        """
        
        result = await db_manager.execute_query(query, fetch_one=True)
        assert result['exists'] is True
    
    @pytest.mark.asyncio
    async def test_user_calendar_credentials_crud(self, db_manager):
        """Test CRUD operations on user_calendar_credentials table"""
        user_id = "test_user_123"
        credentials_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "client_id": "test_client_id"
        }
        
        # Insert
        insert_query = """
            INSERT INTO user_calendar_credentials (user_id, credentials_data)
            VALUES (%s, %s)
            RETURNING id;
        """
        
        result = await db_manager.execute_query(
            insert_query, 
            (user_id, credentials_data), 
            fetch_one=True
        )
        
        credential_id = result['id']
        assert credential_id is not None
        
        # Select
        select_query = """
            SELECT user_id, credentials_data, created_at, updated_at
            FROM user_calendar_credentials
            WHERE id = %s;
        """
        
        result = await db_manager.execute_query(select_query, (credential_id,), fetch_one=True)
        
        assert result['user_id'] == user_id
        assert result['credentials_data'] == credentials_data
        assert result['created_at'] is not None
        assert result['updated_at'] is not None
        
        # Update
        new_credentials_data = {
            "token": "new_test_token",
            "refresh_token": "new_test_refresh_token",
            "client_id": "test_client_id"
        }
        
        update_query = """
            UPDATE user_calendar_credentials 
            SET credentials_data = %s
            WHERE id = %s;
        """
        
        await db_manager.execute_query(update_query, (new_credentials_data, credential_id))
        
        # Verify update
        result = await db_manager.execute_query(select_query, (credential_id,), fetch_one=True)
        assert result['credentials_data'] == new_credentials_data
        
        # Delete
        delete_query = "DELETE FROM user_calendar_credentials WHERE id = %s;"
        await db_manager.execute_query(delete_query, (credential_id,))
        
        # Verify deletion
        result = await db_manager.execute_query(select_query, (credential_id,), fetch_one=True)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_task_calendar_sync_crud(self, db_manager):
        """Test CRUD operations on task_calendar_sync table"""
        # First create a test task
        task_query = """
            INSERT INTO tasks (user_id, description, status, priority, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        
        task_result = await db_manager.execute_query(
            task_query,
            ("test_user", "Test Task", "pending", "medium", datetime.now()),
            fetch_one=True
        )
        
        task_id = task_result['id']
        calendar_event_id = "test_calendar_event_123"
        
        # Insert sync association
        insert_query = """
            INSERT INTO task_calendar_sync (task_id, calendar_event_id)
            VALUES (%s, %s)
            RETURNING id;
        """
        
        result = await db_manager.execute_query(
            insert_query,
            (task_id, calendar_event_id),
            fetch_one=True
        )
        
        sync_id = result['id']
        assert sync_id is not None
        
        # Select
        select_query = """
            SELECT task_id, calendar_event_id, created_at, updated_at
            FROM task_calendar_sync
            WHERE id = %s;
        """
        
        result = await db_manager.execute_query(select_query, (sync_id,), fetch_one=True)
        
        assert result['task_id'] == task_id
        assert result['calendar_event_id'] == calendar_event_id
        assert result['created_at'] is not None
        assert result['updated_at'] is not None
        
        # Test unique constraints
        with pytest.raises(Exception):  # Should fail due to unique constraint
            await db_manager.execute_query(
                insert_query,
                (task_id, "different_event_id")
            )
        
        # Cleanup
        await db_manager.execute_query("DELETE FROM task_calendar_sync WHERE id = %s;", (sync_id,))
        await db_manager.execute_query("DELETE FROM tasks WHERE id = %s;", (task_id,))
    
    @pytest.mark.asyncio
    async def test_calendar_webhook_subscriptions_crud(self, db_manager):
        """Test CRUD operations on calendar_webhook_subscriptions table"""
        user_id = "test_user_123"
        resource_id = "test_resource_123"
        channel_id = "test_channel_123"
        expiration = datetime.now() + timedelta(hours=24)
        
        # Insert
        insert_query = """
            INSERT INTO calendar_webhook_subscriptions 
            (user_id, resource_id, channel_id, expiration)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        
        result = await db_manager.execute_query(
            insert_query,
            (user_id, resource_id, channel_id, expiration),
            fetch_one=True
        )
        
        webhook_id = result['id']
        assert webhook_id is not None
        
        # Select
        select_query = """
            SELECT user_id, resource_id, channel_id, expiration
            FROM calendar_webhook_subscriptions
            WHERE id = %s;
        """
        
        result = await db_manager.execute_query(select_query, (webhook_id,), fetch_one=True)
        
        assert result['user_id'] == user_id
        assert result['resource_id'] == resource_id
        assert result['channel_id'] == channel_id
        assert result['expiration'] is not None
        
        # Cleanup
        await db_manager.execute_query(
            "DELETE FROM calendar_webhook_subscriptions WHERE id = %s;", 
            (webhook_id,)
        )
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_webhooks_function(self, db_manager):
        """Test the cleanup_expired_webhooks function"""
        # Insert expired webhook
        expired_webhook_query = """
            INSERT INTO calendar_webhook_subscriptions 
            (user_id, resource_id, channel_id, expiration)
            VALUES (%s, %s, %s, %s);
        """
        
        expired_time = datetime.now() - timedelta(hours=1)
        await db_manager.execute_query(
            expired_webhook_query,
            ("test_user", "expired_resource", "expired_channel", expired_time)
        )
        
        # Insert valid webhook
        valid_time = datetime.now() + timedelta(hours=1)
        await db_manager.execute_query(
            expired_webhook_query,
            ("test_user", "valid_resource", "valid_channel", valid_time)
        )
        
        # Run cleanup function
        cleanup_query = "SELECT cleanup_expired_webhooks();"
        result = await db_manager.execute_query(cleanup_query, fetch_one=True)
        
        deleted_count = result['cleanup_expired_webhooks']
        assert deleted_count >= 1  # At least the expired webhook should be deleted
        
        # Verify expired webhook was deleted
        check_query = """
            SELECT COUNT(*) as count 
            FROM calendar_webhook_subscriptions 
            WHERE resource_id = 'expired_resource';
        """
        
        result = await db_manager.execute_query(check_query, fetch_one=True)
        assert result['count'] == 0
        
        # Verify valid webhook still exists
        check_query = """
            SELECT COUNT(*) as count 
            FROM calendar_webhook_subscriptions 
            WHERE resource_id = 'valid_resource';
        """
        
        result = await db_manager.execute_query(check_query, fetch_one=True)
        assert result['count'] == 1
        
        # Cleanup
        await db_manager.execute_query(
            "DELETE FROM calendar_webhook_subscriptions WHERE resource_id = 'valid_resource';"
        )
    
    @pytest.mark.asyncio
    async def test_get_user_sync_stats_function(self, db_manager):
        """Test the get_user_sync_stats function"""
        user_id = "test_stats_user"
        
        # Create user preferences
        prefs_query = """
            INSERT INTO user_preferences 
            (user_id, calendar_sync_enabled, last_calendar_sync)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                calendar_sync_enabled = EXCLUDED.calendar_sync_enabled,
                last_calendar_sync = EXCLUDED.last_calendar_sync;
        """
        
        last_sync = datetime.now() - timedelta(hours=2)
        await db_manager.execute_query(prefs_query, (user_id, True, last_sync))
        
        # Create test tasks
        task_query = """
            INSERT INTO tasks (user_id, description, status, priority, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        
        # Create 3 tasks
        task_ids = []
        for i in range(3):
            result = await db_manager.execute_query(
                task_query,
                (user_id, f"Test Task {i}", "pending", "medium", datetime.now()),
                fetch_one=True
            )
            task_ids.append(result['id'])
        
        # Sync 2 tasks to calendar
        sync_query = """
            INSERT INTO task_calendar_sync (task_id, calendar_event_id)
            VALUES (%s, %s);
        """
        
        for i in range(2):
            await db_manager.execute_query(
                sync_query,
                (task_ids[i], f"calendar_event_{i}")
            )
        
        # Test the function
        stats_query = "SELECT * FROM get_user_sync_stats(%s);"
        result = await db_manager.execute_query(stats_query, (user_id,), fetch_one=True)
        
        assert result['total_tasks'] == 3
        assert result['synced_tasks'] == 2
        assert result['sync_coverage'] == 66.67  # 2/3 * 100 rounded to 2 decimal places
        assert result['last_sync'] is not None
        
        # Cleanup
        await db_manager.execute_query(
            "DELETE FROM task_calendar_sync WHERE task_id = ANY(%s);", 
            (task_ids,)
        )
        await db_manager.execute_query(
            "DELETE FROM tasks WHERE id = ANY(%s);", 
            (task_ids,)
        )
        await db_manager.execute_query(
            "DELETE FROM user_preferences WHERE user_id = %s;", 
            (user_id,)
        )
    
    @pytest.mark.asyncio
    async def test_calendar_sync_status_view(self, db_manager):
        """Test the calendar_sync_status view"""
        user_id = "test_view_user"
        
        # Create user preferences with sync enabled
        prefs_query = """
            INSERT INTO user_preferences 
            (user_id, calendar_sync_enabled, last_calendar_sync, calendar_conflict_resolution)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                calendar_sync_enabled = EXCLUDED.calendar_sync_enabled,
                last_calendar_sync = EXCLUDED.last_calendar_sync,
                calendar_conflict_resolution = EXCLUDED.calendar_conflict_resolution;
        """
        
        last_sync = datetime.now() - timedelta(hours=1)
        await db_manager.execute_query(
            prefs_query, 
            (user_id, True, last_sync, "task_wins")
        )
        
        # Create a test task
        task_query = """
            INSERT INTO tasks (user_id, description, status, priority, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """
        
        task_result = await db_manager.execute_query(
            task_query,
            (user_id, "Test Task", "pending", "medium", datetime.now()),
            fetch_one=True
        )
        
        task_id = task_result['id']
        
        # Query the view
        view_query = """
            SELECT * FROM calendar_sync_status 
            WHERE user_id = %s;
        """
        
        result = await db_manager.execute_query(view_query, (user_id,), fetch_one=True)
        
        assert result is not None
        assert result['user_id'] == user_id
        assert result['calendar_sync_enabled'] is True
        assert result['calendar_conflict_resolution'] == "task_wins"
        assert result['total_tasks'] == 1
        assert result['synced_tasks'] == 0  # No sync association created
        assert result['sync_coverage_percentage'] == 0.0
        
        # Cleanup
        await db_manager.execute_query("DELETE FROM tasks WHERE id = %s;", (task_id,))
        await db_manager.execute_query("DELETE FROM user_preferences WHERE user_id = %s;", (user_id,))


if __name__ == "__main__":
    pytest.main([__file__])
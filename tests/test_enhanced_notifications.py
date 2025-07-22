"""Unit tests for enhanced notification system with persistent reminders"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from cogs.persistent_reminders import (
    PersistentReminderManager, 
    NotificationHistory, 
    NotificationChannel, 
    EscalationLevel
)


class MockBot:
    """Mock Discord bot for testing"""
    
    def __init__(self):
        self.users = {}
        self.wait_until_ready = AsyncMock()
    
    async def fetch_user(self, user_id):
        """Mock fetch user"""
        if user_id == 999999:  # Invalid user
            return None
        
        if user_id not in self.users:
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.send = AsyncMock()
            self.users[user_id] = mock_user
        
        return self.users[user_id]


class MockDatabaseManager:
    """Mock database manager for testing"""
    
    @staticmethod
    async def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Mock database query execution"""
        if "notification_preferences" in query:
            if fetch_one:
                return {
                    'discord_dm': True,
                    'discord_guild': False,
                    'web_push': True,
                    'email': False,
                    'quiet_hours_start': None,
                    'quiet_hours_end': None,
                    'timezone': 'UTC'
                }
        
        if "tasks t" in query and fetch_all:
            # Return mock tasks for reminder checking
            return [
                {
                    'id': 1,
                    'user_id': '12345',
                    'description': 'Test task',
                    'due_time': datetime.now() + timedelta(minutes=10),
                    'duration_minutes': 15,
                    'location': 'Office',
                    'reminder_minutes': 15,
                    'reminders_enabled': True
                }
            ]
        
        return [] if fetch_all else None


@pytest.fixture
def mock_bot():
    """Fixture for mock bot"""
    return MockBot()


@pytest.fixture
def notification_history():
    """Fixture for notification history"""
    return NotificationHistory()


@pytest.fixture
def persistent_reminder_manager(mock_bot):
    """Fixture for PersistentReminderManager"""
    with patch('cogs.persistent_reminders.DatabaseManager', MockDatabaseManager), \
         patch('cogs.persistent_reminders.get_discord_web_bridge'), \
         patch('cogs.persistent_reminders.get_sync_service'), \
         patch('cogs.persistent_reminders.TaskQueries'):
        
        manager = PersistentReminderManager(mock_bot)
        # Stop background tasks for testing
        manager.check_new_reminders.cancel()
        manager.send_persistent_reminders.cancel()
        manager.check_escalation_reminders.cancel()
        manager.cleanup_old_reminders.cancel()
        
        return manager


class TestNotificationHistory:
    """Test notification history functionality"""
    
    def test_add_notification(self, notification_history):
        """Test adding notifications to history"""
        user_id = "12345"
        notification_data = {
            'type': 'task_reminder',
            'title': 'Test Notification',
            'message': 'This is a test'
        }
        
        notification_history.add_notification(user_id, notification_data)
        
        history = notification_history.get_user_history(user_id)
        assert len(history) == 1
        assert history[0]['type'] == 'task_reminder'
        assert history[0]['title'] == 'Test Notification'
        assert 'timestamp' in history[0]
        assert 'id' in history[0]
    
    def test_history_limit(self, notification_history):
        """Test that history is limited to 100 notifications per user"""
        user_id = "12345"
        
        # Add 150 notifications
        for i in range(150):
            notification_history.add_notification(user_id, {
                'type': 'test',
                'message': f'Notification {i}'
            })
        
        history = notification_history.get_user_history(user_id)
        assert len(history) == 100  # Should be limited to 100
        
        # Should contain the most recent notifications
        assert history[-1]['message'] == 'Notification 149'
        assert history[0]['message'] == 'Notification 50'
    
    def test_get_delivery_stats_empty(self, notification_history):
        """Test delivery stats for user with no notifications"""
        stats = notification_history.get_delivery_stats("nonexistent")
        
        assert stats['total'] == 0
        assert stats['success'] == 0
        assert stats['failed'] == 0
        assert stats['success_rate'] == 0
    
    def test_get_delivery_stats_with_data(self, notification_history):
        """Test delivery stats calculation"""
        user_id = "12345"
        
        # Add successful notifications
        for i in range(7):
            notification_history.add_notification(user_id, {
                'type': 'test',
                'delivered': True
            })
        
        # Add failed notifications
        for i in range(3):
            notification_history.add_notification(user_id, {
                'type': 'test',
                'delivered': False
            })
        
        stats = notification_history.get_delivery_stats(user_id)
        
        assert stats['total'] == 10
        assert stats['success'] == 7
        assert stats['failed'] == 3
        assert stats['success_rate'] == 70.0


class TestPersistentReminderManager:
    """Test enhanced persistent reminder manager"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, persistent_reminder_manager):
        """Test that manager initializes correctly"""
        manager = persistent_reminder_manager
        
        assert manager.active_reminders == {}
        assert manager.user_reminder_state == {}
        assert manager.collaborative_reminders == {}
        assert isinstance(manager.notification_history, NotificationHistory)
    
    @pytest.mark.asyncio
    async def test_start_persistent_reminder(self, persistent_reminder_manager):
        """Test starting a persistent reminder"""
        manager = persistent_reminder_manager
        
        task = {
            'id': 1,
            'user_id': '12345',
            'description': 'Test task',
            'due_time': datetime.now() + timedelta(minutes=10)
        }
        
        with patch.object(manager, 'send_reminder_message') as mock_send:
            await manager.start_persistent_reminder(task)
        
        # Check that reminder was added
        assert 1 in manager.active_reminders
        assert manager.active_reminders[1]['user_id'] == '12345'
        assert manager.active_reminders[1]['task'] == task
        
        # Check user reminder state
        assert '12345' in manager.user_reminder_state
        assert 1 in manager.user_reminder_state['12345']
        assert manager.user_reminder_state['12345'][1]['active'] is True
        
        # Check that initial reminder was sent
        mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_persistent_reminder(self, persistent_reminder_manager):
        """Test stopping a persistent reminder"""
        manager = persistent_reminder_manager
        
        # Set up active reminder
        manager.active_reminders[1] = {
            'user_id': '12345',
            'task': {'id': 1},
            'reminder_count': 3
        }
        manager.user_reminder_state['12345'] = {
            1: {'active': True, 'started_at': datetime.now()}
        }
        
        await manager.stop_persistent_reminder(1, "Test stop")
        
        # Check that reminder was removed
        assert 1 not in manager.active_reminders
        
        # Check user state was updated
        assert manager.user_reminder_state['12345'][1]['active'] is False
        assert 'stopped_at' in manager.user_reminder_state['12345'][1]
        assert manager.user_reminder_state['12345'][1]['stop_reason'] == "Test stop"
    
    @pytest.mark.asyncio
    async def test_send_escalation_notifications(self, persistent_reminder_manager):
        """Test sending escalation notifications"""
        manager = persistent_reminder_manager
        
        task = {
            'id': 1,
            'description': 'Overdue task',
            'assigned_users': ['12345', '67890'],
            'created_by_user_id': '11111'
        }
        
        with patch.object(manager, 'send_smart_notification') as mock_send:
            await manager.send_escalation_notifications(
                task, EscalationLevel.URGENT, 45
            )
        
        # Should send notifications to assigned users and creator
        assert mock_send.call_count == 3
        
        # Check notification data
        call_args_list = mock_send.call_args_list
        
        # First two calls should be for assigned users
        for i, call_args in enumerate(call_args_list[:2]):
            user_id = call_args[0][0]
            notification_data = call_args[0][1]
            escalation_level = call_args[0][2]
            
            assert user_id in ['12345', '67890']
            assert notification_data['type'] == 'task_escalation'
            assert notification_data['overdue_minutes'] == 45
            assert escalation_level == EscalationLevel.URGENT
        
        # Third call should be for creator
        creator_call = call_args_list[2]
        assert creator_call[0][0] == '11111'
        assert creator_call[0][1]['type'] == 'task_escalation_creator'
    
    @pytest.mark.asyncio
    async def test_get_user_notification_preferences(self, persistent_reminder_manager):
        """Test getting user notification preferences"""
        manager = persistent_reminder_manager
        
        prefs = await manager.get_user_notification_preferences('12345')
        
        # Should return default preferences from mock
        assert prefs['discord_dm'] is True
        assert prefs['web_push'] is True
        assert prefs['email'] is False
        assert prefs['timezone'] == 'UTC'
    
    def test_determine_notification_channels_normal(self, persistent_reminder_manager):
        """Test determining notification channels for normal escalation"""
        manager = persistent_reminder_manager
        
        user_prefs = {
            'discord_dm': True,
            'web_push': True,
            'email': False,
            'discord_guild': False
        }
        
        channels = manager.determine_notification_channels(user_prefs, EscalationLevel.NORMAL)
        
        assert NotificationChannel.DISCORD_DM in channels
        assert NotificationChannel.WEB_PUSH in channels
        assert NotificationChannel.EMAIL not in channels
    
    def test_determine_notification_channels_critical(self, persistent_reminder_manager):
        """Test determining notification channels for critical escalation"""
        manager = persistent_reminder_manager
        
        user_prefs = {
            'discord_dm': False,
            'web_push': False,
            'email': True,
            'discord_guild': False
        }
        
        channels = manager.determine_notification_channels(user_prefs, EscalationLevel.CRITICAL)
        
        # Critical escalation should ensure at least Discord DM
        assert NotificationChannel.DISCORD_DM in channels
        assert NotificationChannel.EMAIL in channels
    
    def test_is_in_quiet_hours(self, persistent_reminder_manager):
        """Test quiet hours detection"""
        manager = persistent_reminder_manager
        
        # Test with no quiet hours set
        user_prefs = {'quiet_hours_start': None, 'quiet_hours_end': None}
        assert manager.is_in_quiet_hours(user_prefs) is False
        
        # Test with quiet hours (this is simplified - real implementation would use timezone)
        from datetime import time
        user_prefs = {
            'quiet_hours_start': time(22, 0),  # 10 PM
            'quiet_hours_end': time(8, 0)      # 8 AM
        }
        
        # Mock current time to be in quiet hours
        with patch('cogs.persistent_reminders.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.time.return_value = time(23, 0)  # 11 PM
            assert manager.is_in_quiet_hours(user_prefs) is True
    
    @pytest.mark.asyncio
    async def test_send_discord_dm_notification(self, persistent_reminder_manager, mock_bot):
        """Test sending Discord DM notification"""
        manager = persistent_reminder_manager
        
        notification_data = {
            'type': 'test',
            'title': 'Test Notification',
            'message': 'Test message'
        }
        
        with patch.object(manager, 'create_notification_embed') as mock_embed:
            mock_embed.return_value = MagicMock()
            
            result = await manager.send_discord_dm_notification('12345', notification_data)
        
        assert result is True
        
        # Check that user was fetched and message was sent
        user = await mock_bot.fetch_user(12345)
        user.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_discord_dm_notification_forbidden(self, persistent_reminder_manager, mock_bot):
        """Test Discord DM notification when DMs are disabled"""
        manager = persistent_reminder_manager
        
        # Mock user.send to raise Forbidden exception
        user = await mock_bot.fetch_user(12345)
        user.send.side_effect = Exception("Forbidden")  # Simplified for testing
        
        notification_data = {'type': 'test', 'title': 'Test', 'message': 'Test'}
        
        with patch.object(manager, 'create_notification_embed'):
            result = await manager.send_discord_dm_notification('12345', notification_data)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_smart_notification(self, persistent_reminder_manager):
        """Test smart notification routing"""
        manager = persistent_reminder_manager
        
        notification_data = {
            'type': 'test',
            'title': 'Test Notification',
            'message': 'Test message'
        }
        
        with patch.object(manager, 'get_user_notification_preferences') as mock_prefs, \
             patch.object(manager, 'determine_notification_channels') as mock_channels, \
             patch.object(manager, 'send_notification_via_channel') as mock_send:
            
            mock_prefs.return_value = {'discord_dm': True}
            mock_channels.return_value = [NotificationChannel.DISCORD_DM]
            mock_send.return_value = True
            
            result = await manager.send_smart_notification('12345', notification_data)
        
        assert result is True
        mock_send.assert_called_once()
        
        # Check that notification was added to history
        history = manager.notification_history.get_user_history('12345')
        assert len(history) == 1
        assert history[0]['delivered'] is True
    
    @pytest.mark.asyncio
    async def test_send_smart_notification_multiple_channels_urgent(self, persistent_reminder_manager):
        """Test smart notification with multiple channels for urgent escalation"""
        manager = persistent_reminder_manager
        
        notification_data = {
            'type': 'test',
            'title': 'Urgent Notification',
            'message': 'Urgent message'
        }
        
        with patch.object(manager, 'get_user_notification_preferences') as mock_prefs, \
             patch.object(manager, 'determine_notification_channels') as mock_channels, \
             patch.object(manager, 'send_notification_via_channel') as mock_send:
            
            mock_prefs.return_value = {'discord_dm': True, 'email': True}
            mock_channels.return_value = [NotificationChannel.DISCORD_DM, NotificationChannel.EMAIL]
            mock_send.return_value = True
            
            result = await manager.send_smart_notification(
                '12345', notification_data, EscalationLevel.URGENT
            )
        
        assert result is True
        # For urgent notifications, should try all channels
        assert mock_send.call_count == 2
    
    def test_create_notification_embed(self, persistent_reminder_manager):
        """Test creating notification embed"""
        manager = persistent_reminder_manager
        
        notification_data = {
            'type': 'task_escalation',
            'title': 'Task Overdue',
            'message': 'Your task is overdue',
            'escalation_level': 'urgent',
            'task_id': 123,
            'overdue_minutes': 30
        }
        
        embed = manager.create_notification_embed(notification_data)
        
        assert embed.title == 'Task Overdue'
        assert embed.description == 'Your task is overdue'
        assert len(embed.fields) == 2  # Task ID and Overdue By
        assert embed.fields[0].value == '123'
        assert embed.fields[1].value == '30 minutes'


class TestEscalationLevels:
    """Test escalation level functionality"""
    
    @pytest.mark.asyncio
    async def test_escalation_level_determination(self, persistent_reminder_manager):
        """Test that escalation levels are determined correctly"""
        manager = persistent_reminder_manager
        
        # Mock collaborative reminders
        manager.collaborative_reminders[1] = {'12345': {}}
        
        current_time = datetime.now()
        
        # Create overdue task
        overdue_task = {
            'id': 1,
            'status': 'pending',
            'due_time': current_time - timedelta(minutes=45),  # 45 minutes overdue
            'description': 'Test task'
        }
        
        with patch('cogs.persistent_reminders.TaskQueries.get_task_by_id') as mock_get_task, \
             patch.object(manager, 'send_escalation_notifications') as mock_escalate:
            
            mock_get_task.return_value = overdue_task
            
            await manager.check_escalation_reminders()
            
            # Should call escalation with URGENT level (30+ minutes overdue)
            mock_escalate.assert_called_once()
            call_args = mock_escalate.call_args[0]
            assert call_args[1] == EscalationLevel.URGENT  # escalation_level
            assert call_args[2] == 45  # overdue_minutes
    
    @pytest.mark.asyncio
    async def test_critical_escalation_level(self, persistent_reminder_manager):
        """Test critical escalation level for very overdue tasks"""
        manager = persistent_reminder_manager
        
        manager.collaborative_reminders[1] = {'12345': {}}
        
        current_time = datetime.now()
        
        # Create very overdue task
        overdue_task = {
            'id': 1,
            'status': 'pending',
            'due_time': current_time - timedelta(minutes=90),  # 90 minutes overdue
            'description': 'Test task'
        }
        
        with patch('cogs.persistent_reminders.TaskQueries.get_task_by_id') as mock_get_task, \
             patch.object(manager, 'send_escalation_notifications') as mock_escalate:
            
            mock_get_task.return_value = overdue_task
            
            await manager.check_escalation_reminders()
            
            # Should call escalation with CRITICAL level (60+ minutes overdue)
            mock_escalate.assert_called_once()
            call_args = mock_escalate.call_args[0]
            assert call_args[1] == EscalationLevel.CRITICAL


class TestCleanupFunctionality:
    """Test cleanup and maintenance functionality"""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_reminders(self, persistent_reminder_manager):
        """Test cleanup of old reminder data"""
        manager = persistent_reminder_manager
        
        # Add old inactive reminder
        old_time = datetime.now() - timedelta(days=10)
        manager.user_reminder_state['12345'] = {
            1: {
                'active': False,
                'stopped_at': old_time.isoformat()
            }
        }
        
        # Add recent inactive reminder
        recent_time = datetime.now() - timedelta(hours=1)
        manager.user_reminder_state['67890'] = {
            2: {
                'active': False,
                'stopped_at': recent_time.isoformat()
            }
        }
        
        # Add active reminder
        manager.user_reminder_state['11111'] = {
            3: {
                'active': True,
                'started_at': datetime.now()
            }
        }
        
        await manager.cleanup_old_reminders()
        
        # Old inactive reminder should be removed
        assert '12345' not in manager.user_reminder_state
        
        # Recent inactive reminder should remain
        assert '67890' in manager.user_reminder_state
        
        # Active reminder should remain
        assert '11111' in manager.user_reminder_state
    
    @pytest.mark.asyncio
    async def test_cleanup_collaborative_reminders(self, persistent_reminder_manager):
        """Test cleanup of collaborative reminders for completed tasks"""
        manager = persistent_reminder_manager
        
        # Add collaborative reminder for completed task
        manager.collaborative_reminders[1] = {'12345': {}}
        
        with patch('cogs.persistent_reminders.TaskQueries.get_task_by_id') as mock_get_task:
            # Mock task as completed
            mock_get_task.return_value = {'id': 1, 'status': 'completed'}
            
            await manager.cleanup_old_reminders()
            
            # Collaborative reminder should be removed
            assert 1 not in manager.collaborative_reminders


if __name__ == "__main__":
    pytest.main([__file__])
"""Integration tests for Discord-Web synchronization"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.discord_web_bridge import DiscordWebBridge, BridgeMessage, get_discord_web_bridge
from src.sync_service import SyncService, SyncEvent, SyncDirection, ConflictResolver
from src.sync_service import get_sync_service


class MockWebSocketManager:
    """Mock WebSocket manager for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.broadcast_messages = []
        self.personal_messages = {}
        self.multi_user_messages = {}
    
    async def send_personal_message(self, message, user_id):
        """Mock send personal message"""
        if user_id not in self.personal_messages:
            self.personal_messages[user_id] = []
        self.personal_messages[user_id].append(message)
    
    async def broadcast_to_all(self, message):
        """Mock broadcast to all"""
        self.broadcast_messages.append(message)
    
    async def send_to_multiple_users(self, message, user_ids):
        """Mock send to multiple users"""
        for user_id in user_ids:
            if user_id not in self.multi_user_messages:
                self.multi_user_messages[user_id] = []
            self.multi_user_messages[user_id].append(message)


class MockDiscordBot:
    """Mock Discord bot for testing"""
    
    def __init__(self):
        self.users = {}
        self.sent_messages = {}
    
    async def fetch_user(self, user_id):
        """Mock fetch user"""
        if user_id in [999999, 888888]:  # Invalid users
            return None
        
        if user_id not in self.users:
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.display_name = f"User{user_id}"
            mock_user.send = AsyncMock()
            self.users[user_id] = mock_user
        
        return self.users[user_id]


@pytest.fixture
def mock_websocket_manager():
    """Fixture for mock WebSocket manager"""
    return MockWebSocketManager()


@pytest.fixture
def mock_discord_bot():
    """Fixture for mock Discord bot"""
    return MockDiscordBot()


@pytest.fixture
def discord_web_bridge(mock_websocket_manager, mock_discord_bot):
    """Fixture for Discord-Web bridge"""
    bridge = DiscordWebBridge()
    bridge.websocket_manager = mock_websocket_manager
    bridge.discord_bot = mock_discord_bot
    bridge.is_initialized = True
    return bridge


@pytest.fixture
def sync_service(discord_web_bridge):
    """Fixture for sync service"""
    service = SyncService()
    service.bridge = discord_web_bridge
    return service


class TestDiscordWebBridge:
    """Test Discord-Web bridge functionality"""
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self, mock_websocket_manager, mock_discord_bot):
        """Test bridge initialization"""
        bridge = DiscordWebBridge()
        
        with patch('src.discord_web_bridge.get_websocket_manager', return_value=mock_websocket_manager):
            await bridge.initialize(mock_discord_bot)
        
        assert bridge.is_initialized
        assert bridge.discord_bot == mock_discord_bot
        assert bridge.websocket_manager == mock_websocket_manager
    
    @pytest.mark.asyncio
    async def test_send_to_web_personal_message(self, discord_web_bridge, mock_websocket_manager):
        """Test sending personal message to web"""
        message = BridgeMessage(
            type='task_updated',
            source='discord',
            target='user',
            user_id='12345',
            data={'task': {'id': 1, 'description': 'Test task'}},
            timestamp=datetime.now().timestamp()
        )
        
        await discord_web_bridge.send_to_web(message)
        
        assert '12345' in mock_websocket_manager.personal_messages
        sent_message = mock_websocket_manager.personal_messages['12345'][0]
        assert sent_message['type'] == 'task_updated'
        assert sent_message['source'] == 'discord'
    
    @pytest.mark.asyncio
    async def test_send_to_web_broadcast(self, discord_web_bridge, mock_websocket_manager):
        """Test broadcasting message to web"""
        message = BridgeMessage(
            type='system_announcement',
            source='system',
            target='broadcast',
            user_id='',
            data={'message': 'System maintenance'},
            timestamp=datetime.now().timestamp()
        )
        
        await discord_web_bridge.send_to_web(message)
        
        assert len(mock_websocket_manager.broadcast_messages) == 1
        sent_message = mock_websocket_manager.broadcast_messages[0]
        assert sent_message['type'] == 'system_announcement'
    
    @pytest.mark.asyncio
    async def test_send_to_web_collaborators(self, discord_web_bridge, mock_websocket_manager):
        """Test sending message to collaborators"""
        message = BridgeMessage(
            type='task_assigned',
            source='discord',
            target='collaborators',
            user_id='12345',
            data={
                'task': {'id': 1, 'description': 'Test task'},
                'collaborators': ['12345', '67890']
            },
            timestamp=datetime.now().timestamp()
        )
        
        await discord_web_bridge.send_to_web(message)
        
        assert '12345' in mock_websocket_manager.multi_user_messages
        assert '67890' in mock_websocket_manager.multi_user_messages
    
    @pytest.mark.asyncio
    async def test_send_to_discord_task_created(self, discord_web_bridge, mock_discord_bot):
        """Test sending task creation to Discord"""
        message = BridgeMessage(
            type='task_created',
            source='web',
            target='discord',
            user_id='12345',
            data={
                'task': {
                    'id': 1,
                    'description': 'Test task',
                    'assigned_users': ['12345', '67890']
                }
            },
            timestamp=datetime.now().timestamp()
        )
        
        await discord_web_bridge.send_to_discord(message)
        
        # Verify users were notified
        user1 = await mock_discord_bot.fetch_user(12345)
        user2 = await mock_discord_bot.fetch_user(67890)
        
        user1.send.assert_called_once()
        user2.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_to_discord_task_updated(self, discord_web_bridge, mock_discord_bot):
        """Test sending task update to Discord"""
        message = BridgeMessage(
            type='task_updated',
            source='web',
            target='discord',
            user_id='12345',
            data={
                'task': {
                    'id': 1,
                    'description': 'Updated task',
                    'assigned_users': ['67890']  # Only notify 67890, not the updater
                },
                'updated_by': '12345',
                'changes': {'description': 'Updated task'}
            },
            timestamp=datetime.now().timestamp()
        )
        
        await discord_web_bridge.send_to_discord(message)
        
        # Verify only the non-updater was notified
        user2 = await mock_discord_bot.fetch_user(67890)
        user2.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_queuing_when_not_initialized(self):
        """Test message queuing when bridge is not initialized"""
        bridge = DiscordWebBridge()
        
        message = BridgeMessage(
            type='task_updated',
            source='discord',
            target='web',
            user_id='12345',
            data={'task': {'id': 1}},
            timestamp=datetime.now().timestamp()
        )
        
        await bridge.send_to_web(message)
        
        # Message should be queued
        assert len(bridge.message_queue) == 1
        assert bridge.message_queue[0] == message
    
    @pytest.mark.asyncio
    async def test_process_message_queue(self, mock_websocket_manager, mock_discord_bot):
        """Test processing queued messages after initialization"""
        bridge = DiscordWebBridge()
        
        # Add messages to queue before initialization
        message1 = BridgeMessage(
            type='task_updated',
            source='discord',
            target='web',
            user_id='12345',
            data={'task': {'id': 1}},
            timestamp=datetime.now().timestamp()
        )
        
        message2 = BridgeMessage(
            type='task_created',
            source='web',
            target='discord',
            user_id='67890',
            data={'task': {'id': 2, 'assigned_users': ['67890']}},
            timestamp=datetime.now().timestamp()
        )
        
        bridge.message_queue = [message1, message2]
        
        # Initialize bridge
        with patch('src.discord_web_bridge.get_websocket_manager', return_value=mock_websocket_manager):
            await bridge.initialize(mock_discord_bot)
        
        # Queue should be processed and empty
        assert len(bridge.message_queue) == 0
        assert '12345' in mock_websocket_manager.personal_messages


class TestSyncService:
    """Test synchronization service functionality"""
    
    @pytest.mark.asyncio
    async def test_sync_task_from_discord(self, sync_service):
        """Test syncing task from Discord to web"""
        task_data = {
            'id': 1,
            'description': 'Test task',
            'status': 'completed',
            'assigned_users': ['12345']
        }
        
        with patch.object(sync_service, '_process_sync_event') as mock_process:
            await sync_service.sync_task_from_discord(task_data, '12345', 'updated')
            
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            event = call_args[0]
            direction = call_args[1]
            
            assert event.event_type == 'task_updated'
            assert event.source == 'discord'
            assert event.user_id == '12345'
            assert event.data == task_data
            assert direction == SyncDirection.DISCORD_TO_WEB
    
    @pytest.mark.asyncio
    async def test_sync_task_from_web(self, sync_service):
        """Test syncing task from web to Discord"""
        task_data = {
            'id': 1,
            'description': 'Test task',
            'status': 'in_progress',
            'assigned_users': ['12345', '67890']
        }
        
        with patch.object(sync_service, '_process_sync_event') as mock_process:
            await sync_service.sync_task_from_web(task_data, '12345', 'created')
            
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            event = call_args[0]
            direction = call_args[1]
            
            assert event.event_type == 'task_created'
            assert event.source == 'web'
            assert direction == SyncDirection.WEB_TO_DISCORD
    
    @pytest.mark.asyncio
    async def test_sync_notification(self, sync_service):
        """Test syncing notifications"""
        notification_data = {
            'id': 'notif_1',
            'type': 'task_assignment',
            'title': 'New Task',
            'message': 'You have been assigned a new task'
        }
        
        with patch.object(sync_service, '_process_sync_event') as mock_process:
            await sync_service.sync_notification(notification_data, '12345')
            
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            event = call_args[0]
            direction = call_args[1]
            
            assert event.event_type == 'notification_sent'
            assert event.source == 'system'
            assert direction == SyncDirection.BIDIRECTIONAL
    
    @pytest.mark.asyncio
    async def test_sync_task_message(self, sync_service):
        """Test syncing task messages"""
        message_data = {
            'id': 'msg_1',
            'content': 'This is a test message',
            'user_id': '12345'
        }
        
        with patch.object(sync_service, '_process_sync_event') as mock_process:
            await sync_service.sync_task_message(message_data, '1', '12345', 'web')
            
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            event = call_args[0]
            direction = call_args[1]
            
            assert event.event_type == 'message_added'
            assert event.source == 'web'
            assert direction == SyncDirection.WEB_TO_DISCORD
            assert event.data['task_id'] == '1'
    
    @pytest.mark.asyncio
    async def test_process_sync_event_discord_to_web(self, sync_service):
        """Test processing sync event from Discord to web"""
        event = SyncEvent(
            event_type='task_updated',
            source='discord',
            user_id='12345',
            entity_type='task',
            entity_id='1',
            data={'id': 1, 'description': 'Test task'},
            timestamp=datetime.now()
        )
        
        with patch.object(sync_service.bridge, 'send_to_web') as mock_send:
            await sync_service._process_sync_event(event, SyncDirection.DISCORD_TO_WEB)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args.type == 'task_updated'
            assert call_args.target == 'web'
    
    @pytest.mark.asyncio
    async def test_process_sync_event_web_to_discord(self, sync_service):
        """Test processing sync event from web to Discord"""
        event = SyncEvent(
            event_type='task_created',
            source='web',
            user_id='12345',
            entity_type='task',
            entity_id='1',
            data={'id': 1, 'description': 'Test task'},
            timestamp=datetime.now()
        )
        
        with patch.object(sync_service.bridge, 'send_to_discord') as mock_send:
            await sync_service._process_sync_event(event, SyncDirection.WEB_TO_DISCORD)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args.type == 'task_created'
            assert call_args.target == 'discord'
    
    @pytest.mark.asyncio
    async def test_process_sync_event_bidirectional(self, sync_service):
        """Test processing bidirectional sync event"""
        event = SyncEvent(
            event_type='notification_sent',
            source='system',
            user_id='12345',
            entity_type='notification',
            entity_id='notif_1',
            data={'message': 'Test notification'},
            timestamp=datetime.now()
        )
        
        with patch.object(sync_service.bridge, 'broadcast_update') as mock_broadcast:
            await sync_service._process_sync_event(event, SyncDirection.BIDIRECTIONAL)
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[0][0] == 'notification_sent'  # message_type
            assert call_args[0][1] == {'message': 'Test notification'}  # data
    
    @pytest.mark.asyncio
    async def test_sync_lock_prevention(self, sync_service):
        """Test that sync locks prevent infinite loops"""
        event = SyncEvent(
            event_type='task_updated',
            source='discord',
            user_id='12345',
            entity_type='task',
            entity_id='1',
            data={'id': 1},
            timestamp=datetime.now()
        )
        
        # Add sync lock
        sync_service.sync_locks.add('task:1')
        
        with patch.object(sync_service.bridge, 'send_to_web') as mock_send:
            await sync_service._process_sync_event(event, SyncDirection.DISCORD_TO_WEB)
            
            # Should not send due to sync lock
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_sync_status(self, sync_service):
        """Test getting sync status"""
        # Add some test data
        sync_service.sync_locks.add('task:1')
        sync_service.pending_events['task:2'] = [
            SyncEvent('task_updated', 'web', '12345', 'task', '2', {}, datetime.now())
        ]
        sync_service.sync_stats['events_processed'] = 5
        
        status = await sync_service.get_sync_status()
        
        assert status['is_active'] is True
        assert 'task:1' in status['active_syncs']
        assert status['pending_events_count'] == 1
        assert status['stats']['events_processed'] == 5
    
    @pytest.mark.asyncio
    async def test_force_sync_task(self, sync_service):
        """Test force syncing a specific task"""
        mock_task_data = {
            'id': 1,
            'description': 'Test task',
            'status': 'completed'
        }
        
        with patch('src.sync_service.get_task_service') as mock_service:
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_task_by_id.return_value = mock_task_data
            
            with patch.object(sync_service, '_process_sync_event') as mock_process:
                result = await sync_service.force_sync_task('1')
                
                assert result is True
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_events(self, sync_service):
        """Test cleaning up old events"""
        # Add old and new events
        old_time = datetime.now() - timedelta(hours=2)
        new_time = datetime.now()
        
        sync_service.pending_events['task:1'] = [
            SyncEvent('task_updated', 'web', '12345', 'task', '1', {}, old_time),
            SyncEvent('task_updated', 'discord', '12345', 'task', '1', {}, new_time)
        ]
        
        sync_service.last_sync_times['task:2'] = old_time
        sync_service.last_sync_times['task:3'] = new_time
        
        await sync_service.cleanup_old_events()
        
        # Old events should be removed
        assert len(sync_service.pending_events['task:1']) == 1
        assert sync_service.pending_events['task:1'][0].timestamp == new_time
        assert 'task:2' not in sync_service.last_sync_times
        assert 'task:3' in sync_service.last_sync_times


class TestConflictResolver:
    """Test conflict resolution functionality"""
    
    @pytest.fixture
    def conflict_resolver(self):
        """Fixture for conflict resolver"""
        return ConflictResolver()
    
    @pytest.mark.asyncio
    async def test_resolve_task_conflict(self, conflict_resolver):
        """Test resolving task conflicts"""
        discord_event = SyncEvent(
            event_type='task_updated',
            source='discord',
            user_id='12345',
            entity_type='task',
            entity_id='1',
            data={'id': 1, 'status': 'completed', 'description': 'Old description'},
            timestamp=datetime.now()
        )
        
        web_event = SyncEvent(
            event_type='task_updated',
            source='web',
            user_id='12345',
            entity_type='task',
            entity_id='1',
            data={'id': 1, 'status': 'in_progress', 'description': 'New description'},
            timestamp=datetime.now() - timedelta(seconds=1)  # Slightly older
        )
        
        resolved = await conflict_resolver.resolve_conflict(discord_event, web_event)
        
        # Discord status should take priority, web description should take priority
        assert resolved.data['status'] == 'completed'  # From Discord
        assert resolved.data['description'] == 'New description'  # From Web
        assert resolved.source == 'merged'
    
    @pytest.mark.asyncio
    async def test_resolve_message_conflict(self, conflict_resolver):
        """Test resolving message conflicts"""
        discord_event = SyncEvent(
            event_type='message_added',
            source='discord',
            user_id='12345',
            entity_type='message',
            entity_id='msg_1',
            data={'content': 'Discord message'},
            timestamp=datetime.now()
        )
        
        web_event = SyncEvent(
            event_type='message_added',
            source='web',
            user_id='12345',
            entity_type='message',
            entity_id='msg_1',
            data={'content': 'Web message'},
            timestamp=datetime.now() - timedelta(seconds=1)
        )
        
        resolved = await conflict_resolver.resolve_conflict(discord_event, web_event)
        
        # Should keep the more recent message
        assert resolved.data['content'] == 'Discord message'
        assert resolved.source == 'discord'
    
    @pytest.mark.asyncio
    async def test_resolve_unknown_entity_conflict(self, conflict_resolver):
        """Test resolving conflicts for unknown entity types"""
        discord_event = SyncEvent(
            event_type='unknown_updated',
            source='discord',
            user_id='12345',
            entity_type='unknown',
            entity_id='1',
            data={'value': 'discord'},
            timestamp=datetime.now()
        )
        
        web_event = SyncEvent(
            event_type='unknown_updated',
            source='web',
            user_id='12345',
            entity_type='unknown',
            entity_id='1',
            data={'value': 'web'},
            timestamp=datetime.now() - timedelta(seconds=1)
        )
        
        resolved = await conflict_resolver.resolve_conflict(discord_event, web_event)
        
        # Should use most recent for unknown types
        assert resolved.data['value'] == 'discord'


class TestConvenienceFunctions:
    """Test convenience functions for sync operations"""
    
    @pytest.mark.asyncio
    async def test_sync_task_update_from_web(self):
        """Test sync_task_update convenience function from web"""
        task_data = {'id': 1, 'description': 'Test task'}
        
        with patch('src.sync_service.get_sync_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service
            
            from src.sync_service import sync_task_update
            await sync_task_update(task_data, '12345', 'web')
            
            mock_service.sync_task_from_web.assert_called_once_with(task_data, '12345', 'updated')
    
    @pytest.mark.asyncio
    async def test_sync_task_update_from_discord(self):
        """Test sync_task_update convenience function from Discord"""
        task_data = {'id': 1, 'description': 'Test task'}
        
        with patch('src.sync_service.get_sync_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service
            
            from src.sync_service import sync_task_update
            await sync_task_update(task_data, '12345', 'discord')
            
            mock_service.sync_task_from_discord.assert_called_once_with(task_data, '12345', 'updated')
    
    @pytest.mark.asyncio
    async def test_sync_notification_to_discord(self):
        """Test sync_notification_to_discord convenience function"""
        notification_data = {'id': 'notif_1', 'message': 'Test notification'}
        
        with patch('src.sync_service.get_sync_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service
            
            from src.sync_service import sync_notification_to_discord
            await sync_notification_to_discord(notification_data, '12345')
            
            mock_service.sync_notification.assert_called_once_with(
                notification_data, '12345', SyncDirection.WEB_TO_DISCORD
            )


if __name__ == "__main__":
    pytest.main([__file__])
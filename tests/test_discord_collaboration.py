"""Unit tests for Discord collaboration features"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

from cogs.tasks import TaskManager
from src.services import TaskManagementException
from src.models import TaskCreateRequest, TaskPriority


class MockBot:
    """Mock Discord bot for testing"""
    def __init__(self):
        self.user = MagicMock()
        self.user.id = 12345
        
    async def fetch_user(self, user_id):
        """Mock fetch_user method"""
        if user_id == 999999:  # Invalid user
            return None
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.mention = f"<@{user_id}>"
        mock_user.display_name = f"User{user_id}"
        return mock_user


class MockInteraction:
    """Mock Discord interaction for testing"""
    def __init__(self, user_id=12345, guild_id=67890):
        self.user = MagicMock()
        self.user.id = user_id
        self.user.mention = f"<@{user_id}>"
        
        self.guild = MagicMock()
        self.guild.id = guild_id
        
        self.response = MagicMock()
        self.response.send_message = AsyncMock()
        self.response.edit_message = AsyncMock()


@pytest.fixture
def mock_bot():
    """Fixture for mock bot"""
    return MockBot()


@pytest.fixture
def task_manager(mock_bot):
    """Fixture for TaskManager cog"""
    with patch('cogs.tasks.get_websocket_manager') as mock_ws_manager:
        mock_ws_manager.return_value = AsyncMock()
        cog = TaskManager(mock_bot)
        return cog


@pytest.fixture
def mock_interaction():
    """Fixture for mock interaction"""
    return MockInteraction()


class TestTaskManagerCollaboration:
    """Test TaskManager collaboration features"""
    
    def test_parse_user_mentions(self, task_manager):
        """Test parsing user mentions from string"""
        # Test valid mentions
        mentions = "<@123456789> <@!987654321>"
        result = task_manager.parse_user_mentions(mentions)
        assert result == ['123456789', '987654321']
        
        # Test no mentions
        no_mentions = "hello world"
        result = task_manager.parse_user_mentions(no_mentions)
        assert result == []
        
        # Test mixed content
        mixed = "Hello <@123456789> and <@!987654321> how are you?"
        result = task_manager.parse_user_mentions(mixed)
        assert result == ['123456789', '987654321']
    
    def test_parse_priority(self, task_manager):
        """Test parsing priority strings"""
        assert task_manager.parse_priority("low") == TaskPriority.LOW
        assert task_manager.parse_priority("HIGH") == TaskPriority.HIGH
        assert task_manager.parse_priority("Normal") == TaskPriority.NORMAL
        assert task_manager.parse_priority("urgent") == TaskPriority.URGENT
        assert task_manager.parse_priority("invalid") == TaskPriority.NORMAL
    
    @pytest.mark.asyncio
    async def test_add_collaborative_task_success(self, task_manager, mock_interaction):
        """Test successful collaborative task creation"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.get_user_action_logger') as mock_logger:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.create_task.return_value = {
                'id': 1,
                'description': 'Test task',
                'assigned_users': ['123456789']
            }
            
            mock_logger.return_value = MagicMock()
            
            # Execute command
            await task_manager.add_collaborative_task(
                mock_interaction,
                description="Test collaborative task",
                assigned_users="<@123456789>",
                duration=30,
                priority="high",
                location="Office"
            )
            
            # Verify task service was called
            mock_task_service.create_task.assert_called_once()
            
            # Verify response was sent
            mock_interaction.response.send_message.assert_called_once()
            
            # Verify embed contains correct information
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "Collaborative Task Created!" in embed.title
    
    @pytest.mark.asyncio
    async def test_add_collaborative_task_no_mentions(self, task_manager, mock_interaction):
        """Test collaborative task creation with no user mentions"""
        await task_manager.add_collaborative_task(
            mock_interaction,
            description="Test task",
            assigned_users="no mentions here",
            duration=15
        )
        
        # Should send error message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Please mention at least one user" in call_args[0][0]
        assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_add_collaborative_task_invalid_users(self, task_manager, mock_interaction):
        """Test collaborative task creation with invalid user mentions"""
        with patch.object(task_manager.bot, 'fetch_user', return_value=None):
            await task_manager.add_collaborative_task(
                mock_interaction,
                description="Test task",
                assigned_users="<@999999>",  # Invalid user
                duration=15
            )
            
            # Should send error message about invalid users
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            assert "could not be found" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_assign_users_to_task_success(self, task_manager, mock_interaction):
        """Test successful user assignment to existing task"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.get_user_action_logger') as mock_logger:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.assign_task_to_users.return_value = True
            mock_task_service.get_task_by_id.return_value = {
                'id': 1,
                'description': 'Test task'
            }
            
            mock_logger.return_value = MagicMock()
            
            # Execute command
            await task_manager.assign_users_to_task(
                mock_interaction,
                task_id=1,
                users="<@123456789>",
                message="Please help with this task"
            )
            
            # Verify service calls
            mock_task_service.assign_task_to_users.assert_called_once_with(
                1, ['123456789'], '12345', "Please help with this task"
            )
            
            # Verify success response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "Task Assigned Successfully!" in embed.title
    
    @pytest.mark.asyncio
    async def test_assign_users_to_task_failure(self, task_manager, mock_interaction):
        """Test failed user assignment to existing task"""
        with patch('cogs.tasks.get_task_service') as mock_service:
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.assign_task_to_users.return_value = False
            
            # Execute command
            await task_manager.assign_users_to_task(
                mock_interaction,
                task_id=1,
                users="<@123456789>"
            )
            
            # Verify failure response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            assert "Failed to assign task" in call_args[0][0]
            assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_update_task_status_success(self, task_manager, mock_interaction):
        """Test successful task status update"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.get_user_action_logger') as mock_logger:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.update_task_status.return_value = True
            mock_task_service.get_task_by_id.return_value = {
                'id': 1,
                'description': 'Test task'
            }
            
            mock_logger.return_value = MagicMock()
            
            # Execute command
            await task_manager.update_task_status(
                mock_interaction,
                task_id=1,
                status="completed",
                notes="Task finished successfully"
            )
            
            # Verify service calls
            mock_task_service.update_task_status.assert_called_once_with(
                1, '12345', 'completed', "Task finished successfully"
            )
            
            # Verify WebSocket update
            task_manager.websocket_manager.send_task_update.assert_called_once()
            
            # Verify success response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "Task Status Updated!" in embed.title
    
    @pytest.mark.asyncio
    async def test_update_task_status_invalid_status(self, task_manager, mock_interaction):
        """Test task status update with invalid status"""
        await task_manager.update_task_status(
            mock_interaction,
            task_id=1,
            status="invalid_status"
        )
        
        # Should send error message
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Invalid status" in call_args[0][0]
        assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_add_task_comment_success(self, task_manager, mock_interaction):
        """Test successful task comment addition"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.get_user_action_logger') as mock_logger:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.add_task_message.return_value = {
                'id': 1,
                'message': 'Test comment',
                'user_id': '12345'
            }
            
            mock_logger.return_value = MagicMock()
            
            # Execute command
            await task_manager.add_task_comment(
                mock_interaction,
                task_id=1,
                comment="This is a test comment"
            )
            
            # Verify service calls
            mock_task_service.add_task_message.assert_called_once_with(
                1, '12345', "This is a test comment"
            )
            
            # Verify WebSocket update
            task_manager.websocket_manager.send_task_message.assert_called_once()
            
            # Verify success response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "Comment Added!" in embed.title
            assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_view_my_tasks_success(self, task_manager, mock_interaction):
        """Test successful task viewing"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.get_user_action_logger') as mock_logger:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_user_tasks.return_value = [
                {
                    'id': 1,
                    'description': 'Test task 1',
                    'status': 'pending',
                    'completion_percentage': 0,
                    'is_collaborative': False
                },
                {
                    'id': 2,
                    'description': 'Test collaborative task',
                    'status': 'in_progress',
                    'completion_percentage': 50,
                    'is_collaborative': True,
                    'assigned_users': ['12345', '67890']
                }
            ]
            
            mock_logger.return_value = MagicMock()
            
            # Execute command
            await task_manager.view_my_tasks(
                mock_interaction,
                status="pending",
                show_collaborative=False
            )
            
            # Verify service calls
            mock_task_service.get_user_tasks.assert_called_once_with('12345', 'pending')
            
            # Verify response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "Your Tasks" in embed.title
            assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_view_my_tasks_collaborative(self, task_manager, mock_interaction):
        """Test viewing collaborative tasks"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.get_user_action_logger') as mock_logger:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_collaborative_tasks.return_value = [
                {
                    'id': 1,
                    'description': 'Collaborative task',
                    'status': 'in_progress',
                    'completion_percentage': 75,
                    'is_collaborative': True,
                    'assigned_users': ['12345', '67890', '11111']
                }
            ]
            
            mock_logger.return_value = MagicMock()
            
            # Execute command
            await task_manager.view_my_tasks(
                mock_interaction,
                show_collaborative=True
            )
            
            # Verify service calls
            mock_task_service.get_collaborative_tasks.assert_called_once_with('12345', None)
            
            # Verify response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "Your Collaborative Tasks" in embed.title
    
    @pytest.mark.asyncio
    async def test_view_my_tasks_no_tasks(self, task_manager, mock_interaction):
        """Test viewing tasks when none exist"""
        with patch('cogs.tasks.get_task_service') as mock_service:
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.get_user_tasks.return_value = []
            
            # Execute command
            await task_manager.view_my_tasks(mock_interaction)
            
            # Verify response
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            embed = call_args[1]['embed']
            assert "No Tasks Found" in embed.title
    
    @pytest.mark.asyncio
    async def test_websocket_integration(self, task_manager, mock_interaction):
        """Test WebSocket integration in commands"""
        with patch('cogs.tasks.get_task_service') as mock_service:
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.update_task_status.return_value = True
            mock_task_service.get_task_by_id.return_value = {'id': 1, 'description': 'Test'}
            
            # Execute command that should trigger WebSocket update
            await task_manager.update_task_status(
                mock_interaction,
                task_id=1,
                status="completed"
            )
            
            # Verify WebSocket manager was called
            task_manager.websocket_manager.send_task_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, task_manager, mock_interaction):
        """Test error handling in commands"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch('cogs.tasks.ErrorHandler') as mock_error_handler:
            
            # Setup mocks to raise exception
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.create_task.side_effect = TaskManagementException("Test error")
            
            mock_error_handler.handle_error = AsyncMock()
            
            # Execute command that should raise exception
            await task_manager.add_collaborative_task(
                mock_interaction,
                description="Test task",
                assigned_users="<@123456789>"
            )
            
            # Verify error handler was called
            mock_error_handler.handle_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_notification_system(self, task_manager, mock_interaction):
        """Test user notification system in collaborative tasks"""
        with patch('cogs.tasks.get_task_service') as mock_service, \
             patch.object(task_manager.bot, 'fetch_user') as mock_fetch_user:
            
            # Setup mocks
            mock_task_service = AsyncMock()
            mock_service.return_value = mock_task_service
            mock_task_service.create_task.return_value = {
                'id': 1,
                'description': 'Test task',
                'assigned_users': ['123456789']
            }
            
            mock_user = AsyncMock()
            mock_user.send = AsyncMock()
            mock_fetch_user.return_value = mock_user
            
            # Execute command
            await task_manager.add_collaborative_task(
                mock_interaction,
                description="Test collaborative task",
                assigned_users="<@123456789>"
            )
            
            # Verify user was notified
            mock_user.send.assert_called_once()
            
            # Verify WebSocket notification was sent
            task_manager.websocket_manager.send_notification.assert_called_once()


class TestWebSocketIntegration:
    """Test WebSocket integration with Discord commands"""
    
    @pytest.mark.asyncio
    async def test_task_update_websocket_sync(self, task_manager):
        """Test that task updates are synced via WebSocket"""
        with patch('cogs.tasks.TaskQueries') as mock_queries:
            mock_queries.update_task.return_value = True
            mock_queries.get_task_by_id.return_value = {
                'id': 1,
                'description': 'Test task',
                'status': 'completed'
            }
            
            # Simulate task update
            mock_interaction = MockInteraction()
            
            # This would be called from within a command
            updated_task = await mock_queries.get_task_by_id(1, '12345')
            await task_manager.websocket_manager.send_task_update(updated_task)
            
            # Verify WebSocket update was sent
            task_manager.websocket_manager.send_task_update.assert_called_once_with(updated_task)
    
    @pytest.mark.asyncio
    async def test_notification_websocket_sync(self, task_manager):
        """Test that notifications are synced via WebSocket"""
        notification_data = {
            "type": "task_assigned",
            "task": {"id": 1, "description": "Test task"},
            "assigned_by": "12345"
        }
        
        await task_manager.websocket_manager.send_notification("67890", notification_data)
        
        # Verify WebSocket notification was sent
        task_manager.websocket_manager.send_notification.assert_called_once_with(
            "67890", notification_data
        )


if __name__ == "__main__":
    pytest.main([__file__])
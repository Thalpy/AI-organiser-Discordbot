"""
Enhanced Discord cog for collaborative task management
Integrates with the web application and provides multi-user task features
"""

import re
from datetime import datetime
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.services import get_task_service, TaskManagementException
from src.models import TaskCreateRequest, TaskPriority
from src.websocket import get_websocket_manager
from utils.discord_helpers import EmbedBuilder, ErrorHandler, MessageFormatter
from utils.logging_config import get_user_action_logger

user_logger = get_user_action_logger()


class CollaborativeTaskManager(commands.Cog):
    """Enhanced task manager with collaboration features"""
    
    def __init__(self, bot):
        self.bot = bot
        self.websocket_manager = get_websocket_manager()
    
    def parse_user_mentions(self, users_str: str) -> List[str]:
        """Parse user mentions from string"""
        # Extract user IDs from mentions like <@123456789>
        mention_pattern = r'<@!?(\d+)>'
        user_ids = re.findall(mention_pattern, users_str)
        return user_ids
    
    def parse_priority(self, priority_str: str) -> TaskPriority:
        """Parse priority string to TaskPriority enum"""
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT
        }
        return priority_map.get(priority_str.lower(), TaskPriority.NORMAL)
    
    @app_commands.command(name="create_collaborative_task", description="Create a task and assign it to multiple users")
    async def create_collaborative_task(
        self,
        interaction: discord.Interaction,
        description: str,
        assigned_users: str,
        duration: int = 15,
        priority: str = "normal",
        location: Optional[str] = None
    ):
        """Create a collaborative task with multiple assignees"""
        user_id = str(interaction.user.id)
        
        try:
            # Parse assigned users
            user_ids = self.parse_user_mentions(assigned_users)
            
            if not user_ids:
                await interaction.response.send_message(
                    "❌ Please mention at least one user to assign the task to.",
                    ephemeral=True
                )
                return
            
            # Validate mentioned users are in the guild
            valid_user_ids = []
            invalid_mentions = []
            
            for user_id_str in user_ids:
                try:
                    user = await self.bot.fetch_user(int(user_id_str))
                    if user:
                        valid_user_ids.append(user_id_str)
                    else:
                        invalid_mentions.append(user_id_str)
                except:
                    invalid_mentions.append(user_id_str)
            
            if invalid_mentions:
                await interaction.response.send_message(
                    f"⚠️ Some mentioned users could not be found: {', '.join(invalid_mentions)}",
                    ephemeral=True
                )
                return
            
            # Create task data
            task_data = TaskCreateRequest(
                description=description,
                assigned_users=valid_user_ids,
                duration_minutes=duration,
                priority=self.parse_priority(priority),
                location=location,
                is_collaborative=True
            )
            
            # Create task through service
            task_service = await get_task_service()
            task = await task_service.create_task(user_id, task_data)
            
            # Create success embed
            embed = EmbedBuilder.success_embed(
                title="Collaborative Task Created!",
                description=f"**{description}**",
                fields=[
                    ("👥 Assigned Users", f"{len(valid_user_ids)} users", True),
                    ("⏱️ Duration", f"{duration} minutes", True),
                    ("🔥 Priority", priority.title(), True),
                    ("📍 Location", location or "Not specified", True),
                    ("🆔 Task ID", str(task['id']), True)
                ],
                footer="All assigned users will receive notifications"
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Send notifications to assigned users
            for assigned_user_id in valid_user_ids:
                try:
                    assigned_user = await self.bot.fetch_user(int(assigned_user_id))
                    if assigned_user:
                        notification_embed = EmbedBuilder.info_embed(
                            title="📋 New Task Assignment",
                            description=f"You've been assigned to a collaborative task by {interaction.user.mention}",
                            fields=[
                                ("Task", description, False),
                                ("Duration", f"{duration} minutes", True),
                                ("Priority", priority.title(), True),
                                ("Location", location or "Not specified", True)
                            ],
                            footer="Use /start to begin working on this task"
                        )
                        
                        await assigned_user.send(embed=notification_embed)
                        
                        # Send WebSocket notification
                        await self.websocket_manager.send_notification(
                            assigned_user_id,
                            {
                                "type": "task_assigned",
                                "task": task,
                                "assigned_by": user_id
                            }
                        )
                        
                except Exception as e:
                    print(f"Failed to notify user {assigned_user_id}: {e}")
            
            user_logger.log_discord_command(
                user_id, "create_collaborative_task", 
                str(interaction.guild_id) if interaction.guild else None,
                True
            )
            
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to create collaborative task.")
    
    @app_commands.command(name="assign_task", description="Assign an existing task to additional users")
    async def assign_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
        users: str,
        message: Optional[str] = None
    ):
        """Assign an existing task to additional users"""
        user_id = str(interaction.user.id)
        
        try:
            # Parse user mentions
            user_ids = self.parse_user_mentions(users)
            
            if not user_ids:
                await interaction.response.send_message(
                    "❌ Please mention at least one user to assign the task to.",
                    ephemeral=True
                )
                return
            
            # Assign task through service
            task_service = await get_task_service()
            success = await task_service.assign_task_to_users(
                task_id, user_ids, user_id, message
            )
            
            if success:
                # Get updated task
                task = await task_service.get_task_by_id(task_id, user_id)
                
                embed = EmbedBuilder.success_embed(
                    title="Task Assigned Successfully!",
                    description=f"Task **{task['description']}** has been assigned to {len(user_ids)} additional users.",
                    fields=[
                        ("👥 New Assignees", f"{len(user_ids)} users", True),
                        ("📝 Message", message or "No message", False)
                    ],
                    footer=f"Task ID: {task_id}"
                )
                
                await interaction.response.send_message(embed=embed)
                
                # Notify assigned users
                for assigned_user_id in user_ids:
                    try:
                        assigned_user = await self.bot.fetch_user(int(assigned_user_id))
                        if assigned_user:
                            notification_embed = EmbedBuilder.info_embed(
                                title="📋 Task Assignment Update",
                                description=f"You've been assigned to an existing task by {interaction.user.mention}",
                                fields=[
                                    ("Task", task['description'], False),
                                    ("Message", message or "No additional message", False)
                                ]
                            )
                            
                            await assigned_user.send(embed=notification_embed)
                            
                            # Send WebSocket notification
                            await self.websocket_manager.send_task_assignment(task, [assigned_user_id])
                            
                    except Exception as e:
                        print(f"Failed to notify user {assigned_user_id}: {e}")
                
                user_logger.log_discord_command(user_id, "assign_task", None, True)
            else:
                await interaction.response.send_message("❌ Failed to assign task.", ephemeral=True)
                
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to assign task.")
    
    @app_commands.command(name="task_progress", description="Update progress on a collaborative task")
    async def update_task_progress(
        self,
        interaction: discord.Interaction,
        task_id: int,
        progress: int,
        notes: Optional[str] = None
    ):
        """Update progress on a collaborative task"""
        user_id = str(interaction.user.id)
        
        try:
            if progress < 0 or progress > 100:
                await interaction.response.send_message(
                    "❌ Progress must be between 0 and 100.",
                    ephemeral=True
                )
                return
            
            # Update progress through service
            task_service = await get_task_service()
            success = await task_service.update_task_progress(task_id, user_id, progress, notes)
            
            if success:
                # Get updated task
                task = await task_service.get_task_by_id(task_id, user_id)
                
                embed = EmbedBuilder.success_embed(
                    title="Progress Updated!",
                    description=f"Task **{task['description']}** progress updated to {progress}%",
                    fields=[
                        ("📊 Progress", f"{progress}%", True),
                        ("📝 Notes", notes or "No notes", False)
                    ],
                    footer=f"Task ID: {task_id}"
                )
                
                await interaction.response.send_message(embed=embed)
                
                # Send real-time update
                await self.websocket_manager.send_task_update(task)
                
                user_logger.log_discord_command(user_id, "task_progress", None, True)
            else:
                await interaction.response.send_message("❌ Failed to update progress.", ephemeral=True)
                
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to update task progress.")
    
    @app_commands.command(name="task_message", description="Add a message to a collaborative task")
    async def add_task_message(
        self,
        interaction: discord.Interaction,
        task_id: int,
        message: str
    ):
        """Add a message to a collaborative task"""
        user_id = str(interaction.user.id)
        
        try:
            # Add message through service
            task_service = await get_task_service()
            message_data = await task_service.add_task_message(task_id, user_id, message)
            
            embed = EmbedBuilder.success_embed(
                title="Message Added!",
                description=f"Your message has been added to the task collaboration thread.",
                fields=[
                    ("💬 Message", message[:200] + "..." if len(message) > 200 else message, False)
                ],
                footer=f"Task ID: {task_id}"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Send real-time update
            await self.websocket_manager.send_task_message(message_data)
            
            user_logger.log_discord_command(user_id, "task_message", None, True)
            
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to add message.")
    
    @app_commands.command(name="my_collaborative_tasks", description="View your collaborative tasks")
    async def view_collaborative_tasks(
        self,
        interaction: discord.Interaction,
        status: Optional[str] = None
    ):
        """View user's collaborative tasks"""
        user_id = str(interaction.user.id)
        
        try:
            # Get tasks through service
            task_service = await get_task_service()
            tasks = await task_service.get_collaborative_tasks(user_id, status)
            
            if not tasks:
                status_text = f" with status '{status}'" if status else ""
                embed = EmbedBuilder.info_embed(
                    title="No Collaborative Tasks",
                    description=f"You don't have any collaborative tasks{status_text}.",
                    footer="Use /create_collaborative_task to create one"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create task list embed
            embed = EmbedBuilder.create_embed(
                title="👥 Your Collaborative Tasks",
                description=f"Found {len(tasks)} collaborative task(s)",
                color=EmbedBuilder.INFO
            )
            
            for task in tasks[:10]:  # Limit to 10 tasks
                status_emoji = {
                    'pending': '🕓',
                    'in_progress': '▶️',
                    'completed': '✅',
                    'cancelled': '❌'
                }
                
                emoji = status_emoji.get(task.get('status', 'pending'), '❓')
                
                # Format assigned users
                assigned_users = task.get('assigned_users', [])
                if assigned_users:
                    user_count = len([u for u in assigned_users if u])
                    users_text = f"{user_count} users assigned"
                else:
                    users_text = "No assignments"
                
                # Format due time
                due_text = "No due time"
                if task.get('due_time'):
                    due_text = MessageFormatter.format_time(task['due_time'])
                
                embed.add_field(
                    name=f"{emoji} {task['description'][:50]}",
                    value=f"**ID:** {task['id']}\n**Users:** {users_text}\n**Due:** {due_text}\n**Progress:** {task.get('completion_percentage', 0)}%",
                    inline=True
                )
            
            if len(tasks) > 10:
                embed.set_footer(text=f"Showing 10 of {len(tasks)} tasks. Use filters to narrow results.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            user_logger.log_discord_command(user_id, "my_collaborative_tasks", None, True)
            
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to retrieve collaborative tasks.")
    
    @app_commands.command(name="task_details", description="View detailed information about a task")
    async def view_task_details(
        self,
        interaction: discord.Interaction,
        task_id: int
    ):
        """View detailed information about a specific task"""
        user_id = str(interaction.user.id)
        
        try:
            # Get task details through service
            task_service = await get_task_service()
            task = await task_service.get_task_by_id(task_id, user_id)
            messages = await task_service.get_task_messages(task_id, user_id)
            
            # Create detailed embed
            embed = EmbedBuilder.task_embed(task, "📋 Task Details: ")
            
            # Add collaboration info
            assigned_users = task.get('assigned_users', [])
            if assigned_users:
                user_mentions = []
                for user_id_str in assigned_users:
                    if user_id_str:
                        try:
                            user = await self.bot.fetch_user(int(user_id_str))
                            user_mentions.append(user.mention if user else f"User {user_id_str}")
                        except:
                            user_mentions.append(f"User {user_id_str}")
                
                embed.add_field(
                    name="👥 Assigned Users",
                    value="\n".join(user_mentions) if user_mentions else "None",
                    inline=False
                )
            
            # Add recent messages
            if messages:
                recent_messages = messages[-3:]  # Last 3 messages
                message_text = ""
                
                for msg in recent_messages:
                    try:
                        msg_user = await self.bot.fetch_user(int(msg['user_id']))
                        username = msg_user.display_name if msg_user else f"User {msg['user_id']}"
                    except:
                        username = f"User {msg['user_id']}"
                    
                    message_text += f"**{username}:** {msg['message'][:100]}\n"
                
                embed.add_field(
                    name="💬 Recent Messages",
                    value=message_text or "No messages",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            user_logger.log_discord_command(user_id, "task_details", None, True)
            
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to retrieve task details.")


async def setup(bot):
    await bot.add_cog(CollaborativeTaskManager(bot))
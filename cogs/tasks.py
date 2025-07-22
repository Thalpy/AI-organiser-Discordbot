from discord.ext import commands
from discord import app_commands
import discord
import datetime
import re
from typing import Optional, List
from utils.database import TaskQueries, get_connection
from utils.discord_helpers import EmbedBuilder, ErrorHandler, MessageFormatter
from src.services import get_task_service, TaskManagementException
from src.models import TaskCreateRequest, TaskPriority, TaskStatus
from src.websocket import get_websocket_manager
from utils.logging_config import get_user_action_logger

user_logger = get_user_action_logger()

class TaskManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.websocket_manager = get_websocket_manager()
    
    def parse_user_mentions(self, users_str: str) -> List[str]:
        """Parse user mentions from string"""
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

    @app_commands.command(name="start", description="Start a task")
    async def start_task(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        try:
            tasks = await TaskQueries.get_user_tasks(user_id, status='pending', limit=10)

            if not tasks:
                embed = EmbedBuilder.info_embed(
                    title="No Pending Tasks",
                    description="You don't have any pending tasks to start.",
                    footer="Use /add to create a new task"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to load your tasks.")
            return

        class TaskView(discord.ui.View):
            def __init__(self, task_list):
                super().__init__(timeout=60)
                for t in task_list:
                    self.add_item(discord.ui.Button(label=t['description'][:40], style=discord.ButtonStyle.primary, custom_id=str(t['id'])))

        async def button_callback(i: discord.Interaction):
            try:
                task_id = int(i.data['custom_id'])
                now = datetime.datetime.now()
                
                # Get the task details first
                task = await TaskQueries.get_task_by_id(task_id, user_id)
                if not task:
                    await ErrorHandler.handle_error(i, Exception("Task not found"), "Task not found.")
                    return
                
                # Update task status
                success = await TaskQueries.update_task(
                    task_id, user_id,
                    start_time=now,
                    status='in_progress',
                    num_sessions=(task.get('num_sessions', 0) or 0) + 1
                )
                
                # Stop persistent reminders for this task
                persistent_reminder_cog = i.client.get_cog("PersistentReminderManager")
                if persistent_reminder_cog:
                    await persistent_reminder_cog.stop_persistent_reminder(task_id, "Task started via /start command")
                
                # Send real-time update to web interface
                if success:
                    try:
                        updated_task = await TaskQueries.get_task_by_id(task_id, user_id)
                        await self.websocket_manager.send_task_update(updated_task)
                        user_logger.log_discord_command(user_id, "start_task", str(i.guild_id) if i.guild else None, True)
                    except Exception as ws_error:
                        print(f"Failed to send WebSocket update: {ws_error}")
                
                if success:
                    embed = EmbedBuilder.success_embed(
                        title="Task Started!",
                        description=f"You're now working on: **{task['description']}**",
                        fields=[
                            ("Started At", MessageFormatter.format_time(now), True),
                            ("Estimated Duration", MessageFormatter.format_duration(task.get('duration_minutes', 15)), True)
                        ],
                        footer="Use /finish to complete or /delay to pause"
                    )
                    await i.response.edit_message(embed=embed, view=None)
                else:
                    await ErrorHandler.handle_error(i, Exception("Update failed"), "Could not start the task.")
            except Exception as e:
                await ErrorHandler.handle_error(i, e, "Failed to start the task.")

        view = TaskView(tasks)
        for item in view.children:
            item.callback = button_callback

        await interaction.response.send_message("Select a task to start:", ephemeral=True, view=view)

    @app_commands.command(name="finish", description="Finish your current task")
    async def finish_task(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        try:
            tasks = await TaskQueries.get_user_tasks(user_id, status='in_progress', limit=1)
            
            if not tasks:
                embed = EmbedBuilder.warning_embed(
                    title="No Active Task",
                    description="You don't have any tasks in progress.",
                    footer="Use /start to begin working on a task"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            task = tasks[0]
            now = datetime.datetime.now()
            
            # Calculate duration
            duration_minutes = 0
            if task.get('start_time'):
                duration = now - task['start_time']
                duration_minutes = int(duration.total_seconds() / 60)
            
            # Update task
            success = await TaskQueries.update_task(
                task['id'], user_id,
                stop_time=now,
                status='done',
                actual_duration=(task.get('actual_duration', 0) or 0) + duration_minutes
            )
            
            # Send real-time update to web interface
            if success:
                try:
                    updated_task = await TaskQueries.get_task_by_id(task['id'], user_id)
                    await self.websocket_manager.send_task_update(updated_task)
                    user_logger.log_discord_command(user_id, "finish_task", str(interaction.guild_id) if interaction.guild else None, True)
                except Exception as ws_error:
                    print(f"Failed to send WebSocket update: {ws_error}")
            
            if success:
                embed = EmbedBuilder.success_embed(
                    title="Task Completed!",
                    description=f"**{task['description']}** has been marked as complete.",
                    fields=[
                        ("Duration", MessageFormatter.format_duration(duration_minutes), True),
                        ("Completed At", MessageFormatter.format_time(now), True)
                    ],
                    footer=f"Task ID: {task['id']}"
                )
            else:
                embed = EmbedBuilder.error_embed(
                    title="Update Failed",
                    description="Could not update the task status."
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to finish the task.")

    @app_commands.command(name="delay", description="Delay the current task")
    async def delay_task(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        try:
            tasks = await TaskQueries.get_user_tasks(user_id, status='in_progress', limit=1)
            
            if not tasks:
                embed = EmbedBuilder.warning_embed(
                    title="No Active Task",
                    description="You don't have any tasks in progress to delay."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            task = tasks[0]
            
            # Update task status
            success = await TaskQueries.update_task(
                task['id'], user_id,
                start_time=None,
                status='pending'
            )
            
            # Send real-time update to web interface
            if success:
                try:
                    updated_task = await TaskQueries.get_task_by_id(task['id'], user_id)
                    await self.websocket_manager.send_task_update(updated_task)
                    user_logger.log_discord_command(user_id, "delay_task", str(interaction.guild_id) if interaction.guild else None, True)
                except Exception as ws_error:
                    print(f"Failed to send WebSocket update: {ws_error}")
            
            if success:
                embed = EmbedBuilder.warning_embed(
                    title="Task Delayed",
                    description=f"**{task['description']}** has been moved back to pending.",
                    fields=[
                        ("Status", "🕓 Pending", True),
                        ("Next Step", "Use /start when ready to resume", False)
                    ],
                    footer=f"Task ID: {task['id']}"
                )
            else:
                embed = EmbedBuilder.error_embed(
                    title="Update Failed",
                    description="Could not delay the task."
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to delay the task.")

    @app_commands.command(name="add_collaborative", description="Create a new collaborative task with multiple assignees")
    async def add_collaborative_task(
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
            
            # Validate mentioned users
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
            
            # Create task using the service layer
            task_service = await get_task_service()
            task_data = TaskCreateRequest(
                description=description,
                assigned_users=valid_user_ids,
                duration_minutes=duration,
                priority=self.parse_priority(priority),
                location=location,
                is_collaborative=True
            )
            
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
                user_id, "add_collaborative_task", 
                str(interaction.guild_id) if interaction.guild else None,
                True
            )
            
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to create collaborative task.")

    @app_commands.command(name="assign_users", description="Assign additional users to an existing task")
    async def assign_users_to_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
        users: str,
        message: Optional[str] = None
    ):
        """Assign additional users to an existing task"""
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
            
            # Use service layer to assign task
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
                
                user_logger.log_discord_command(user_id, "assign_users_to_task", None, True)
            else:
                await interaction.response.send_message("❌ Failed to assign task.", ephemeral=True)
                
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to assign task.")

    @app_commands.command(name="task_status", description="Update the status of a task and sync with web")
    async def update_task_status(
        self,
        interaction: discord.Interaction,
        task_id: int,
        status: str,
        notes: Optional[str] = None
    ):
        """Update task status with web synchronization"""
        user_id = str(interaction.user.id)
        
        try:
            # Validate status
            valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled', 'on_hold']
            if status.lower() not in valid_statuses:
                await interaction.response.send_message(
                    f"❌ Invalid status. Valid options: {', '.join(valid_statuses)}",
                    ephemeral=True
                )
                return
            
            # Update task through service
            task_service = await get_task_service()
            success = await task_service.update_task_status(task_id, user_id, status.lower(), notes)
            
            if success:
                # Get updated task
                task = await task_service.get_task_by_id(task_id, user_id)
                
                status_emojis = {
                    'pending': '🕓',
                    'in_progress': '▶️',
                    'completed': '✅',
                    'cancelled': '❌',
                    'on_hold': '⏸️'
                }
                
                embed = EmbedBuilder.success_embed(
                    title="Task Status Updated!",
                    description=f"Task **{task['description']}** status changed to {status_emojis.get(status.lower(), '📋')} **{status.title()}**",
                    fields=[
                        ("📝 Notes", notes or "No notes", False)
                    ],
                    footer=f"Task ID: {task_id} • Changes synced with web interface"
                )
                
                await interaction.response.send_message(embed=embed)
                
                # Send real-time update
                await self.websocket_manager.send_task_update(task)
                
                user_logger.log_discord_command(user_id, "update_task_status", None, True)
            else:
                await interaction.response.send_message("❌ Failed to update task status.", ephemeral=True)
                
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to update task status.")

    @app_commands.command(name="task_comment", description="Add a comment to a task for collaboration")
    async def add_task_comment(
        self,
        interaction: discord.Interaction,
        task_id: int,
        comment: str
    ):
        """Add a comment to a task for collaboration"""
        user_id = str(interaction.user.id)
        
        try:
            # Add comment through service
            task_service = await get_task_service()
            message_data = await task_service.add_task_message(task_id, user_id, comment)
            
            embed = EmbedBuilder.success_embed(
                title="Comment Added!",
                description=f"Your comment has been added to the task collaboration thread.",
                fields=[
                    ("💬 Comment", comment[:200] + "..." if len(comment) > 200 else comment, False)
                ],
                footer=f"Task ID: {task_id} • Visible in web interface and to all collaborators"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Send real-time update
            await self.websocket_manager.send_task_message(message_data)
            
            user_logger.log_discord_command(user_id, "add_task_comment", None, True)
            
        except TaskManagementException as e:
            await ErrorHandler.handle_error(interaction, e, e.message)
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to add comment.")

    @app_commands.command(name="my_tasks", description="View your tasks with collaboration info")
    async def view_my_tasks(
        self,
        interaction: discord.Interaction,
        status: Optional[str] = None,
        show_collaborative: bool = False
    ):
        """View user's tasks with collaboration information"""
        user_id = str(interaction.user.id)
        
        try:
            # Get tasks through service
            task_service = await get_task_service()
            
            if show_collaborative:
                tasks = await task_service.get_collaborative_tasks(user_id, status)
                title = "👥 Your Collaborative Tasks"
            else:
                tasks = await task_service.get_user_tasks(user_id, status)
                title = "📋 Your Tasks"
            
            if not tasks:
                status_text = f" with status '{status}'" if status else ""
                embed = EmbedBuilder.info_embed(
                    title="No Tasks Found",
                    description=f"You don't have any tasks{status_text}.",
                    footer="Use /add_collaborative to create a collaborative task"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create task list embed
            embed = EmbedBuilder.create_embed(
                title=title,
                description=f"Found {len(tasks)} task(s)",
                color=EmbedBuilder.INFO
            )
            
            for task in tasks[:10]:  # Limit to 10 tasks
                status_emoji = {
                    'pending': '🕓',
                    'in_progress': '▶️',
                    'completed': '✅',
                    'cancelled': '❌',
                    'on_hold': '⏸️'
                }
                
                emoji = status_emoji.get(task.get('status', 'pending'), '❓')
                
                # Format collaboration info
                collab_info = ""
                if task.get('is_collaborative'):
                    assigned_users = task.get('assigned_users', [])
                    if assigned_users:
                        user_count = len([u for u in assigned_users if u])
                        collab_info = f"👥 {user_count} collaborators"
                    else:
                        collab_info = "👥 Collaborative"
                
                # Format due time
                due_text = "No due time"
                if task.get('due_time'):
                    due_text = MessageFormatter.format_time(task['due_time'])
                
                field_value = f"**ID:** {task['id']}\n**Due:** {due_text}\n**Progress:** {task.get('completion_percentage', 0)}%"
                if collab_info:
                    field_value += f"\n{collab_info}"
                
                embed.add_field(
                    name=f"{emoji} {task['description'][:50]}",
                    value=field_value,
                    inline=True
                )
            
            if len(tasks) > 10:
                embed.set_footer(text=f"Showing 10 of {len(tasks)} tasks. Use filters to narrow results.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            user_logger.log_discord_command(user_id, "view_my_tasks", None, True)
            
        except Exception as e:
            await ErrorHandler.handle_error(interaction, e, "Failed to retrieve tasks.")

async def setup(bot):
    await bot.add_cog(TaskManager(bot))

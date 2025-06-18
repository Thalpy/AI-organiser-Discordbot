# Refactored Tasks Cog - Example of using new utility modules
# This demonstrates how to use the new database and Discord utilities

from discord.ext import commands
from discord import app_commands
import discord
import datetime
from typing import Optional, List
from utils.database import TaskQueries, DatabaseManager
from utils.discord_helpers import EmbedBuilder, ErrorHandler, MessageFormatter
from utils.time_helpers import DateTimeParser, TimeZoneManager

class TaskManagerRefactored(commands.Cog):
    """Refactored task manager using utility modules"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start_task", description="Start a task (refactored version)")
    async def start_task(self, interaction: discord.Interaction):
        """Start a task with improved error handling and UI"""
        user_id = str(interaction.user.id)
        
        try:
            # Use the new database utility
            tasks = await TaskQueries.get_user_tasks(user_id, status='pending', limit=10)
            
            if not tasks:
                embed = EmbedBuilder.info_embed(
                    title="No Pending Tasks",
                    description="You don't have any pending tasks to start.",
                    footer="Use /add to create a new task"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create task selection view
            view = TaskSelectionView(tasks, user_id)
            
            embed = EmbedBuilder.info_embed(
                title="Select Task to Start",
                description="Choose a task from your pending list:",
                fields=[
                    ("Available Tasks", str(len(tasks)), True),
                    ("Tip", "Tasks are sorted by priority and due date", False)
                ]
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await ErrorHandler.handle_error(
                interaction, e, 
                "Failed to load your tasks. Please try again."
            )

    @app_commands.command(name="finish_task", description="Finish your current task (refactored version)")
    async def finish_task(self, interaction: discord.Interaction):
        """Finish current task with improved feedback"""
        user_id = str(interaction.user.id)
        
        try:
            # Get current task
            tasks = await TaskQueries.get_user_tasks(user_id, status='in_progress', limit=1)
            
            if not tasks:
                embed = EmbedBuilder.warning_embed(
                    title="No Active Task",
                    description="You don't have any tasks in progress.",
                    footer="Use /start_task to begin working on a task"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            task = tasks[0]
            now = datetime.datetime.now()
            
            # Calculate duration if start_time exists
            duration_minutes = 0
            if task.get('start_time'):
                duration = now - task['start_time']
                duration_minutes = int(duration.total_seconds() / 60)
            
            # Update task status
            success = await TaskQueries.update_task(
                task['id'], user_id,
                stop_time=now,
                status='done',
                actual_duration=(task.get('actual_duration', 0) or 0) + duration_minutes
            )
            
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
                    description="Could not update the task status. Please try again."
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ErrorHandler.handle_error(
                interaction, e,
                "Failed to finish the task. Please try again."
            )

    @app_commands.command(name="delay_task", description="Delay the current task (refactored version)")
    async def delay_task(self, interaction: discord.Interaction):
        """Delay current task with better feedback"""
        user_id = str(interaction.user.id)
        
        try:
            # Get current task
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
            
            if success:
                embed = EmbedBuilder.warning_embed(
                    title="Task Delayed",
                    description=f"**{task['description']}** has been moved back to pending.",
                    fields=[
                        ("Status", "🕓 Pending", True),
                        ("Next Step", "Use /start_task when ready to resume", False)
                    ],
                    footer=f"Task ID: {task['id']}"
                )
            else:
                embed = EmbedBuilder.error_embed(
                    title="Update Failed",
                    description="Could not delay the task. Please try again."
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ErrorHandler.handle_error(
                interaction, e,
                "Failed to delay the task. Please try again."
            )

class TaskSelectionView(discord.ui.View):
    """Improved task selection with better UI"""
    
    def __init__(self, tasks: List[dict], user_id: str):
        super().__init__(timeout=60)
        self.tasks = tasks
        self.user_id = user_id
        
        # Add buttons for each task (up to 5)
        for i, task in enumerate(tasks[:5]):
            button = TaskButton(task, i)
            self.add_item(button)

class TaskButton(discord.ui.Button):
    """Individual task button with improved styling"""
    
    def __init__(self, task: dict, index: int):
        self.task = task
        
        # Create button label with emoji and truncated description
        description = MessageFormatter.truncate_text(task['description'], 40)
        priority_emoji = "🔥" if task.get('priority') else "📋"
        
        super().__init__(
            label=f"{priority_emoji} {description}",
            style=discord.ButtonStyle.primary if task.get('priority') else discord.ButtonStyle.secondary,
            custom_id=f"task_{task['id']}"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle task selection"""
        try:
            now = datetime.datetime.now()
            
            # Update task status
            success = await TaskQueries.update_task(
                self.task['id'], 
                str(interaction.user.id),
                start_time=now,
                status='in_progress',
                num_sessions=(self.task.get('num_sessions', 0) or 0) + 1
            )
            
            if success:
                embed = EmbedBuilder.success_embed(
                    title="Task Started!",
                    description=f"You're now working on: **{self.task['description']}**",
                    fields=[
                        ("Started At", MessageFormatter.format_time(now), True),
                        ("Estimated Duration", MessageFormatter.format_duration(self.task.get('duration_minutes', 15)), True),
                        ("Session #", str((self.task.get('num_sessions', 0) or 0) + 1), True)
                    ],
                    footer="Use /finish_task when complete or /delay_task to pause"
                )
                
                # Disable all buttons
                for item in self.view.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self.view)
            else:
                await ErrorHandler.handle_error(
                    interaction, Exception("Database update failed"),
                    "Could not start the task. Please try again."
                )
                
        except Exception as e:
            await ErrorHandler.handle_error(
                interaction, e,
                "Failed to start the task. Please try again."
            )

async def setup(bot):
    await bot.add_cog(TaskManagerRefactored(bot))
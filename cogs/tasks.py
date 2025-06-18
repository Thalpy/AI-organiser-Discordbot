from discord.ext import commands
from discord import app_commands
import discord
import datetime
from typing import Optional, List
from utils.database import TaskQueries, get_connection
from utils.discord_helpers import EmbedBuilder, ErrorHandler, MessageFormatter

class TaskManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    await bot.add_cog(TaskManager(bot))

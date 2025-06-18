from discord.ext import commands
from discord import app_commands
import discord
from utils.database import TaskQueries, get_connection
from utils.discord_helpers import EmbedBuilder, ErrorHandler, MessageFormatter
from utils.logging_config import get_user_action_logger, get_performance_logger
import logging

logger = logging.getLogger(__name__)
user_logger = get_user_action_logger()
perf_logger = get_performance_logger("list_modal")

# --- View with a dropdown and buttons for selected task ---
class TaskDropdownView(discord.ui.View):
    def __init__(self, tasks):
        super().__init__(timeout=120)
        self.tasks = tasks
        self.dropdown = TaskDropdown(tasks)
        self.add_item(self.dropdown)

        # Buttons are created and assigned callbacks but NOT added to this view
        self.edit_btn = discord.ui.Button(emoji="✏️", style=discord.ButtonStyle.primary, custom_id="edit")
        label = "Uncomplete" if self.tasks and self.tasks[0].get("status") == "done" else "Complete"
        emoji = "🔁" if label == "Uncomplete" else "✅"
        self.complete_btn = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.success, custom_id="complete")
        self.delete_btn = discord.ui.Button(emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="delete")

        self.edit_btn.callback = self.button_callback
        self.complete_btn.callback = self.button_callback
        self.delete_btn.callback = self.button_callback

        self.selected_task_id = None


    async def button_callback(self, interaction: discord.Interaction):
        if not self.selected_task_id:
            embed = EmbedBuilder.warning_embed(
                "No Task Selected",
                "Please select a task from the dropdown first."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_id = str(interaction.user.id)
        task_id = self.selected_task_id
        action = interaction.data["custom_id"]
        
        logger.info(f"User {user_id} performing action '{action}' on task {task_id}")

        try:
            if action == "delete":
                success = await TaskQueries.delete_task(task_id, user_id)
                if success:
                    embed = EmbedBuilder.success_embed(
                        "Task Deleted",
                        "The task has been permanently removed."
                    )
                    user_logger.log_task_action(user_id, "deleted", task_id)
                else:
                    embed = EmbedBuilder.error_embed(
                        "Delete Failed",
                        "Could not delete the task. It may have already been removed."
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "complete":
                success = await TaskQueries.update_task(task_id, user_id, status='done')
                if success:
                    embed = EmbedBuilder.success_embed(
                        "Task Completed",
                        "The task has been marked as complete! 🎉"
                    )
                    user_logger.log_task_action(user_id, "completed", task_id)
                else:
                    embed = EmbedBuilder.error_embed(
                        "Update Failed",
                        "Could not mark the task as complete."
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "edit":
                # Get task details for editing
                task = await TaskQueries.get_task_by_id(task_id, user_id)
                if not task:
                    embed = EmbedBuilder.error_embed(
                        "Task Not Found",
                        "The task was not found or you don't have permission to edit it."
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Import and create modal for editing
                from cogs.todo_modal import TaskModal
                modal = TaskModal(user_id, task['description'], task_id=task_id)
                modal.task_id = task_id  # Mark this as an edit modal
                
                # Pre-fill modal with existing data
                if task.get('schedule_time') and task.get('schedule_date'):
                    modal.datetime_str.default = f"{task['schedule_date'].month:02}/{task['schedule_date'].day:02} {task['schedule_time'].strftime('%H:%M')}"
                if task.get('duration_minutes'):
                    modal.duration.default = str(task['duration_minutes'])
                if task.get('deadline'):
                    modal.deadline.default = task['deadline'].strftime('%Y-%m-%d %H:%M')
                if task.get('location'):
                    modal.location.default = task['location']
                
                await interaction.response.send_modal(modal)
                user_logger.log_task_action(user_id, "opened_edit_modal", task_id)
                
        except Exception as e:
            logger.error(f"Error in button callback for user {user_id}, action {action}: {e}")
            await ErrorHandler.handle_error(
                interaction, e,
                f"Failed to {action} the task. Please try again."
            )

class TaskDropdown(discord.ui.Select):
    def __init__(self, tasks):
        self.task_map = {str(task["id"]): task for task in tasks}
        options = [
            discord.SelectOption(label=task["description"][:100], value=str(task["id"]))
            for task in tasks
        ]
        super().__init__(placeholder="Select a task to manage...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        task_id = int(self.values[0])
        self.view.selected_task_id = task_id
        task = self.task_map[str(task_id)]
        details = f"""
**Task ID:** {task['id']}
**Description:** {task['description']}
**Due Time:** {task.get('due_time', '—')}
**Duration:** {task.get('duration_minutes', '15')} minutes
**Deadline:** {task.get('deadline', '—')}
**Location:** {task.get('location', '—')}
**Priority:** {'Yes' if task.get('priority') else 'No'}
"""
        await interaction.response.defer(ephemeral=True)

        view = discord.ui.View(timeout=120)
        view.add_item(self.view.edit_btn)
        view.add_item(self.view.complete_btn)
        view.add_item(self.view.delete_btn)

        await interaction.followup.send(content=details, view=view, ephemeral=True)

# --- Toggle View (footer only) ---
class TaskToggleFooter(discord.ui.View):
    def __init__(self, status_filter):
        super().__init__(timeout=120)
        self.status_filter = status_filter
        toggle_label = "Show ✅ Done" if status_filter == "pending" else "Show 🕓 Pending"
        toggle = discord.ui.Button(label=toggle_label, style=discord.ButtonStyle.secondary, custom_id=f"toggle_{status_filter}")
        toggle.callback = self.toggle_callback
        self.add_item(toggle)

    async def toggle_callback(self, interaction: discord.Interaction):
        new_status = "done" if self.status_filter == "pending" else "pending"
        cog = interaction.client.get_cog("TaskListCog")
        await cog.send_task_list(interaction, filter_status=new_status)

# --- Task listing cog ---
class TaskListCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list", description="List your tasks with a dropdown and action buttons")
    async def list_tasks(self, interaction: discord.Interaction):
        await self.send_task_list(interaction, filter_status="pending")

    async def send_task_list(self, interaction: discord.Interaction, filter_status="pending"):
        user_id = str(interaction.user.id)
        logger.info(f"User {user_id} requesting task list with filter: {filter_status}")
        
        try:
            perf_logger.start_timer("load_task_list")
            
            # Get task counts and tasks using utility functions
            task_counts = await TaskQueries.get_task_counts(user_id)
            tasks = await TaskQueries.get_user_tasks(user_id, status=filter_status, limit=25)
            
            perf_logger.end_timer("load_task_list", f"Loaded {len(tasks)} tasks for user {user_id}")
            
            # Create improved summary embed
            status_emoji = {
                'pending': '🕓',
                'done': '✅',
                'in_progress': '▶️'
            }
            
            embed = EmbedBuilder.create_embed(
                title=f"📊 Task Summary - {status_emoji.get(filter_status, '📋')} {filter_status.title()}",
                description=f"Showing your {filter_status} tasks",
                color=EmbedBuilder.PRIMARY,
                fields=[
                    ("📈 Total Tasks", str(task_counts['total']), True),
                    ("🕓 Pending", str(task_counts['pending']), True),
                    ("✅ Completed", str(task_counts['done']), True),
                    ("📋 Showing", f"{len(tasks)} {filter_status} tasks", False)
                ],
                footer=f"Use buttons below to manage tasks • Filter: {filter_status}"
            )

            if not tasks:
                embed.add_field(
                    name="No Tasks Found", 
                    value=f"You don't have any {filter_status} tasks.", 
                    inline=False
                )
                view = TaskToggleFooter(filter_status)
            else:
                view = TaskDropdownView(tasks)

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            # Add toggle footer if we have tasks
            if tasks:
                await interaction.followup.send(view=TaskToggleFooter(filter_status), ephemeral=True)
            
            user_logger.log_command_usage(user_id, "list", str(interaction.guild_id) if interaction.guild else None)
            
        except Exception as e:
            logger.error(f"Failed to load task list for user {user_id}: {e}")
            await ErrorHandler.handle_error(
                interaction, e,
                "Failed to load your task list. Please try again."
            )

async def setup(bot):
    await bot.add_cog(TaskListCog(bot))

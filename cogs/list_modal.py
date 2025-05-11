from discord.ext import commands
from discord import app_commands
import discord
import psycopg2
from config import DB_CONFIG

# DB connection
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

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
            await interaction.response.send_message("⚠️ Please select a task first.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        task_id = self.selected_task_id
        action = interaction.data["custom_id"]

        with get_connection() as conn:
            with conn.cursor() as cur:
                if action == "delete":
                    cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
                    conn.commit()
                    await interaction.response.send_message("🗑️ Task deleted.", ephemeral=True)
                elif action == "complete":
                    cur.execute("UPDATE tasks SET status = 'done' WHERE id = %s AND user_id = %s", (task_id, user_id))
                    conn.commit()
                    await interaction.response.send_message("✅ Task marked as complete.", ephemeral=True)
                elif action == "edit":
                    with get_connection() as edit_conn:
                        with edit_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as edit_cur:
                            edit_cur.execute("""
                            SELECT description, schedule_time, schedule_date, duration_minutes, deadline, location
                            FROM tasks WHERE id = %s AND user_id = %s
                            """, (task_id, user_id))
                            row = edit_cur.fetchone()
                            if not row:
                                await interaction.response.send_message("❌ Task not found or access denied.", ephemeral=True)
                                return

                    from cogs.todo_modal import TaskModal
                    modal = TaskModal(user_id, row['description'], task_id=task_id)
                    modal.task_id = task_id  # Mark this as an edit modal
                    if row['schedule_time'] and row['schedule_date']:
                        modal.datetime_str.default = f"{row['schedule_date'].month:02}/{row['schedule_date'].day:02} {row['schedule_time'].strftime('%H:%M')}"
                    if row['duration_minutes']:
                        modal.duration.default = str(row['duration_minutes'])
                    if row['deadline']:
                        modal.deadline.default = row['deadline'].strftime('%Y-%m-%d %H:%M')
                    if row['location']:
                        modal.location.default = row['location']
                    await interaction.response.send_modal(modal)

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

        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id,))
                total = cur.fetchone()["count"]

                cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s AND status = 'done'", (user_id,))
                done = cur.fetchone()["count"]

                cur.execute("SELECT id, description, due_time, duration_minutes, deadline, location, priority FROM tasks WHERE user_id = %s AND status = %s ORDER BY id DESC LIMIT 25", (user_id, filter_status))
                tasks = cur.fetchall()

        active = total - done

        summary_embed = discord.Embed(
            title="📊 Task Summary",
            description=f"**Total:** {total}  •  **Active:** {active}  •  **Completed:** {done}",
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=summary_embed, view=TaskDropdownView(tasks), ephemeral=True)
        await interaction.followup.send(view=TaskToggleFooter(filter_status), ephemeral=True)

async def setup(bot):
    await bot.add_cog(TaskListCog(bot))

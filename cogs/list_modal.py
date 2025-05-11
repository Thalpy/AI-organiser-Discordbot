from discord.ext import commands
from discord import app_commands
import discord
import psycopg2
from config import DB_CONFIG

# DB connection
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# Buttons for deleting and editing
class TaskToggleView(discord.ui.View):
    def __init__(self, tasks, status_filter):
        super().__init__(timeout=120)
        self.status_filter = status_filter
        for task in tasks:
            row = TaskActionRow(task)
            self.add_item(row.edit_button)
            self.add_item(row.complete_button)
            self.add_item(row.delete_button)

        toggle_label = "Show ✅ Done" if status_filter == "pending" else "Show 🕓 Pending"
        toggle_style = discord.ButtonStyle.secondary
        self.add_item(discord.ui.Button(label=toggle_label, style=toggle_style, custom_id=f"toggle_{status_filter}"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow interaction refresh
        if interaction.data["custom_id"].startswith("toggle_"):
            new_status = "done" if self.status_filter == "pending" else "pending"
            await TaskListCog.resend_task_list(interaction, new_status)
            return False
        return True

class TaskActionRow:
    def __init__(self, task):
        self.task = task
        self.edit_button = discord.ui.Button(emoji="✏️", style=discord.ButtonStyle.primary, custom_id=f"edit_{task['id']}")
        self.delete_button = discord.ui.Button(emoji="🗑️", style=discord.ButtonStyle.danger, custom_id=f"delete_{task['id']}")
        self.complete_button = discord.ui.Button(emoji="✅", style=discord.ButtonStyle.success, custom_id=f"complete_{task['id']}")

        for button in [self.edit_button, self.delete_button, self.complete_button]:
            button.callback = self.make_callback(button.custom_id)

    def make_callback(self, custom_id):
        async def callback(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            task_id = int(custom_id.split("_")[1])
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if "delete" in custom_id:
                        cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
                        await interaction.response.send_message("🗑️ Task deleted.", ephemeral=True)
                    elif "complete" in custom_id:
                        cur.execute("UPDATE tasks SET status = 'done' WHERE id = %s AND user_id = %s", (task_id, user_id))
                        await interaction.response.send_message("✅ Task marked as complete.", ephemeral=True)
                    elif "edit" in custom_id:
                        await interaction.response.send_message("✏️ Edit is not implemented yet.", ephemeral=True)
                    conn.commit()
        return callback

class TaskDeleteButton(discord.ui.Button):
    def __init__(self, task_id, label, style):
        super().__init__(label=label, style=style, custom_id=f"delete_{task_id}")
        self.task_id = task_id

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (self.task_id, user_id))
                conn.commit()
        await interaction.response.send_message(f"🗑️ Task `{self.task_id}` deleted.", ephemeral=True)

class TaskEditButton(discord.ui.Button):
    def __init__(self, task_id, label, style):
        super().__init__(label=label, style=style, custom_id=f"edit_{task_id}")
        self.task_id = task_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✏️ Edit for task `{self.task_id}` is not implemented yet.", ephemeral=True)

# Main listing cog
class TaskListCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list", description="List your tasks with action buttons")
    async def list_tasks(self, interaction: discord.Interaction):
        await self.resend_task_list(interaction, "pending")

    @staticmethod
    async def resend_task_list(interaction: discord.Interaction, status_filter: str):
        user_id = str(interaction.user.id)
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id,))
                total = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s AND status = 'done'", (user_id,))
                done = cur.fetchone()["count"]
                cur.execute("SELECT id, description FROM tasks WHERE user_id = %s AND status = %s ORDER BY id DESC LIMIT 10", (user_id, status_filter))
                tasks = cur.fetchall()

        active = total - done
        stat_embed = discord.Embed(
            title="📊 Task Summary",
            description=f"**Total:** {total}  •  **Active:** {active}  •  **Completed:** {done}",
            color=discord.Color.purple()
        )

        if not tasks:
            stat_embed.add_field(name="(No Tasks)", value="Nothing to display.", inline=False)

        await interaction.response.send_message(embed=stat_embed, view=TaskToggleView(tasks, status_filter), ephemeral=True)
        
async def setup(bot):
    await bot.add_cog(TaskListCog(bot))
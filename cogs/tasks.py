from discord.ext import commands
from discord import app_commands
import discord
import datetime
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class TaskManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start", description="Start a task")
    async def start_task(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, description FROM tasks
                    WHERE user_id = %s AND status = 'pending'
                    ORDER BY due_time ASC NULLS LAST, id ASC LIMIT 10
                """, (user_id,))
                tasks = cur.fetchall()

        if not tasks:
            await interaction.response.send_message("No pending tasks found.", ephemeral=True)
            return

        class TaskView(discord.ui.View):
            def __init__(self, task_list):
                super().__init__(timeout=60)
                for t in task_list:
                    self.add_item(discord.ui.Button(label=t['description'][:40], style=discord.ButtonStyle.primary, custom_id=str(t['id'])))

        async def button_callback(i: discord.Interaction):
            task_id = int(i.data['custom_id'])
            now = datetime.datetime.now()
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE tasks
                        SET start_time = %s, status = 'in_progress'
                        WHERE id = %s
                    """, (now, task_id))
                    cur.execute("""
                        UPDATE tasks
                        SET num_sessions = COALESCE(num_sessions, 0) + 1
                        WHERE id = %s
                    """, (task_id,))
                    conn.commit()
            await i.response.edit_message(content=f"▶️ Started task `{task_id}`.", view=None)

        view = TaskView(tasks)
        for item in view.children:
            item.callback = button_callback

        await interaction.response.send_message("Select a task to start:", ephemeral=True, view=view)

    @app_commands.command(name="finish", description="Finish your current task")
    async def finish_task(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now()
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, start_time FROM tasks
                    WHERE user_id = %s AND status = 'in_progress'
                    ORDER BY start_time DESC LIMIT 1
                """, (user_id,))
                task = cur.fetchone()
                if not task:
                    await interaction.response.send_message("No task in progress.", ephemeral=True)
                    return

                duration = (now - task['start_time']).total_seconds() / 60

                cur.execute("""
                    UPDATE tasks
                    SET stop_time = %s, status = 'done', actual_duration = COALESCE(actual_duration, 0) + %s
                    WHERE id = %s
                """, (now, duration, task['id']))
                conn.commit()

        await interaction.response.send_message(f"✅ Finished task `{task['id']}` after {int(duration)} minutes.", ephemeral=True)

    @app_commands.command(name="delay", description="Delay the current task")
    async def delay_task(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id FROM tasks
                    WHERE user_id = %s AND status = 'in_progress'
                    ORDER BY start_time DESC LIMIT 1
                """, (user_id,))
                task = cur.fetchone()
                if not task:
                    await interaction.response.send_message("No task is currently in progress.", ephemeral=True)
                    return

                cur.execute("""
                    UPDATE tasks
                    SET start_time = NULL, status = 'pending'
                    WHERE id = %s
                """, (task['id'],))
                conn.commit()

        await interaction.response.send_message(f"⏸️ Delayed task `{task['id']}`.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TaskManager(bot))

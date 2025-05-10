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

    @app_commands.command(name="todo", description="Add a new task")
    @app_commands.describe(
        task="What do you need to do?",
        schedule_time="Optional static time (HH:MM)",
        day_month="Optional static day/month (DD/MM)",
        duration_minutes="Estimated duration (default 15)",
        priority="High priority?",
        deadline="Deadline (YYYY-MM-DD HH:MM)",
        mirrored_users="Comma-separated @users or IDs",
        location="Location or URL"
    )
    async def add_task(
        self,
        interaction: discord.Interaction,
        task: str,
        schedule_time: Optional[str] = None,
        day_month: Optional[str] = None,
        duration_minutes: Optional[int] = 15,
        priority: Optional[bool] = False,
        deadline: Optional[str] = None,
        mirrored_users: Optional[str] = None,  # Changed from List[User]
        location: Optional[str] = None
    ):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now()

        schedule_date = None
        schedule_time_obj = None
        due_time = None

        try:
            if day_month:
                day, month = map(int, day_month.split("/"))
                schedule_date = datetime.date(year=now.year, month=month, day=day)

            if schedule_time:
                hour, minute = map(int, schedule_time.split(":"))
                schedule_time_obj = datetime.time(hour, minute)

            if schedule_date and schedule_time_obj:
                due_time = datetime.datetime.combine(schedule_date, schedule_time_obj)
            elif schedule_date:
                due_time = datetime.datetime.combine(schedule_date, datetime.time(9, 0))
            elif schedule_time_obj:
                due_time = datetime.datetime.combine(now.date(), schedule_time_obj)

            deadline_ts = None
            if deadline:
                deadline_ts = datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M")

            mirrored_ids = []
            if mirrored_users:
                for raw in mirrored_users.split(","):
                    cleaned = raw.strip().lstrip("<@!").rstrip(">")
                    if cleaned.isdigit():
                        mirrored_ids.append(cleaned)

        except Exception:
            await interaction.response.send_message("Invalid date/time format. Use HH:MM and DD/MM.", ephemeral=True)
            return

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (
                        user_id, description, schedule_time, schedule_date, duration_minutes,
                        priority, deadline, mirrored_users, location, due_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    task,
                    schedule_time_obj,
                    schedule_date,
                    duration_minutes,
                    priority,
                    deadline_ts,
                    mirrored_ids if mirrored_ids else None,
                    location,
                    due_time
                ))
                conn.commit()

        await interaction.response.send_message(f"✅ Task added: **{task}**", ephemeral=True)

    @app_commands.command(name="list", description="List your recent tasks")
    async def list_tasks(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, description, status FROM tasks
                    WHERE user_id = %s
                    ORDER BY id DESC LIMIT 10
                """, (user_id,))
                rows = cur.fetchall()

        if not rows:
            await interaction.response.send_message("You have no tasks yet.", ephemeral=True)
            return

        msg = "**Your recent tasks:**\n"
        for row in rows:
            msg += f"- `{row['id']}`: {row['description']} (**{row['status']}**)"
        await interaction.response.send_message(msg, ephemeral=True)

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

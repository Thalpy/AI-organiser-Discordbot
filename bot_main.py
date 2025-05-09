import discord
from discord.ext import tasks
from discord import app_commands
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
from config import DISCORD_TOKEN, DB_CONFIG

# --- DB Setup ---
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    description TEXT,
                    due_time TIMESTAMP,
                    start_time TIMESTAMP,
                    stop_time TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id TEXT PRIMARY KEY,
                    reminder_channel_id TEXT
                )
            """)
            conn.commit()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

class TaskBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        init_db()
        await self.tree.sync()  # Global sync; you can limit to specific guilds in dev
        remind_tasks.start()

bot = TaskBot()

# --- Slash Commands ---
@bot.tree.command(name="todo", description="Add a new task")
@app_commands.describe(task="What do you need to do?")
async def add_task(interaction: discord.Interaction, task: str):
    user_id = str(interaction.user.id)
    due_time = datetime.datetime.now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks (user_id, description, due_time) VALUES (%s, %s, %s)",
                        (user_id, task, due_time))
            conn.commit()
    await interaction.response.send_message(f"Task added: {task}", ephemeral=True)

@bot.tree.command(name="start", description="Start a task from your pending list")
async def start_task(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, description FROM tasks WHERE user_id = %s AND status = 'pending' ORDER BY id DESC LIMIT 10", (user_id,))
            rows = cur.fetchall()

    if not rows:
        await interaction.response.send_message("You have no pending tasks.", ephemeral=True)
        return

    class StartTaskView(discord.ui.View):
        def __init__(self, tasks):
            super().__init__(timeout=60)
            for task in tasks:
                self.add_item(discord.ui.Button(
                    label=task['description'][:40],
                    style=discord.ButtonStyle.primary,
                    custom_id=str(task['id']))
                )

        async def interaction_check(self, i):
            return i.user.id == interaction.user.id

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

    async def button_callback(i: discord.Interaction):
        task_id = int(i.data['custom_id'])
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE tasks SET start_time = %s, status = 'in_progress' WHERE id = %s",
                            (datetime.datetime.now(), task_id))
                conn.commit()
        await i.response.edit_message(content=f"Started task {task_id}.", view=None)

    view = StartTaskView(rows)
    for item in view.children:
        item.callback = button_callback

    await interaction.response.send_message("Select a task to start:", ephemeral=True, view=view)

@bot.tree.command(name="finish", description="Finish your current task")
async def finish_task(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, description FROM tasks WHERE user_id = %s AND status = 'in_progress' ORDER BY start_time DESC", (user_id,))
            rows = cur.fetchall()

    if not rows:
        await interaction.response.send_message("No tasks are in progress.", ephemeral=True)
        return

    if len(rows) == 1:
        task_id = rows[0]['id']
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE tasks SET stop_time = %s, status = 'done' WHERE id = %s",
                            (datetime.datetime.now(), task_id))
                conn.commit()
        await interaction.response.send_message(f"Finished task {task_id}.", ephemeral=True)
        return

    class FinishView(discord.ui.View):
        def __init__(self, tasks):
            super().__init__(timeout=60)
            for task in tasks:
                self.add_item(discord.ui.Button(
                    label=task['description'][:40],
                    style=discord.ButtonStyle.success,
                    custom_id=str(task['id']))
                )

    async def button_callback(i: discord.Interaction):
        task_id = int(i.data['custom_id'])
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE tasks SET stop_time = %s, status = 'done' WHERE id = %s",
                            (datetime.datetime.now(), task_id))
                conn.commit()
        await i.response.edit_message(content=f"Finished task {task_id}.", view=None)

    view = FinishView(rows)
    for item in view.children:
        item.callback = button_callback

    await interaction.response.send_message("Select a task to finish:", ephemeral=True, view=view)

@bot.tree.command(name="delay", description="Delay your current task")
async def delay_task(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tasks WHERE user_id = %s AND status = 'in_progress' ORDER BY start_time DESC LIMIT 1", (user_id,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE tasks SET start_time = NULL, status = 'pending' WHERE id = %s", (row[0],))
                conn.commit()
                await interaction.response.send_message(f"Delayed task {row[0]}.", ephemeral=True)
                return
    await interaction.response.send_message("No task in progress to delay.", ephemeral=True)

@bot.tree.command(name="list", description="List your recent tasks")
async def list_tasks(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, description, status
                FROM tasks
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT 10
            """, (user_id,))
            rows = cur.fetchall()

    if not rows:
        await interaction.response.send_message("You have no tasks yet.", ephemeral=True)
        return

    msg = "**Your recent tasks:**\n"
    for row in rows:
        msg += f"- `{row['id']}`: {row['description']} (**{row['status']}**)\n"

    await interaction.response.send_message(msg, ephemeral=True)


# --- Reminder System ---
@tasks.loop(minutes=10)
async def remind_tasks():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, user_id, description FROM tasks WHERE status = 'pending'")
            tasks_due = cur.fetchall()
    for task in tasks_due:
        try:
            user = await bot.fetch_user(int(task["user_id"]))
            await user.send(f"⏰ Reminder: '{task['description']}' (Task ID: {task['id']}) is still pending.")
        except Exception as e:
            print(f"Reminder failed for user {task['user_id']}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")

bot.run(DISCORD_TOKEN)

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
        init_db()  # Ensure all tables are created before background tasks start
        for guild in self.guilds:
            await self.tree.sync(guild=guild)
        remind_tasks.start()


bot = TaskBot()

# --- Slash Commands ---
@bot.tree.command(name="todo", description="Add a new task")
async def add_task(interaction: discord.Interaction, task: str):
    user_id = str(interaction.user.id)
    due_time = datetime.datetime.now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks (user_id, description, due_time) VALUES (%s, %s, %s)",
                        (user_id, task, due_time))
            conn.commit()
    await interaction.response.send_message(f"Task added: {task}", ephemeral=True)

@bot.tree.command(name="start", description="Start a task by ID")
async def start_task(interaction: discord.Interaction, task_id: int):
    start_time = datetime.datetime.now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET start_time = %s, status = 'in_progress' WHERE id = %s",
                        (start_time, task_id))
            conn.commit()
    await interaction.response.send_message(f"Task {task_id} started.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop a task by ID")
async def stop_task(interaction: discord.Interaction, task_id: int):
    stop_time = datetime.datetime.now()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET stop_time = %s, status = 'done' WHERE id = %s",
                        (stop_time, task_id))
            conn.commit()
    await interaction.response.send_message(f"Task {task_id} completed.", ephemeral=True)

@bot.tree.command(name="list", description="List your current tasks")
async def list_tasks(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, description, status FROM tasks WHERE user_id = %s ORDER BY id DESC LIMIT 10", (user_id,))
            rows = cur.fetchall()

    if not rows:
        await interaction.response.send_message("You have no tasks.", ephemeral=True)
        return

    message = "Your tasks:\n"
    for row in rows:
        message += f"`{row['id']}` - {row['description']} (**{row['status']}**)\n"
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="setreminderchannel", description="Set the reminder channel for this server")
async def set_reminder_channel(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO settings (guild_id, reminder_channel_id) VALUES (%s, %s) ON CONFLICT (guild_id) DO UPDATE SET reminder_channel_id = EXCLUDED.reminder_channel_id",
                        (guild_id, channel_id))
            conn.commit()
    await interaction.response.send_message(f"✅ Reminder channel set to <#{channel_id}>", ephemeral=True)

# --- DM Message Command Handling ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower().startswith("todo "):
            task = message.content[5:].strip()
            if not task:
                await message.channel.send("❗ Please provide a task description after 'todo'.")
                return
            user_id = str(message.author.id)
            due_time = datetime.datetime.now()
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO tasks (user_id, description, due_time) VALUES (%s, %s, %s)",
                                (user_id, task, due_time))
                    conn.commit()
            await message.channel.send(f"✅ Task added: {task}")
    elif isinstance(message.channel, discord.TextChannel):
        # Automatically set first message channel as reminder channel if not already set
        guild_id = str(message.guild.id)
        channel_id = str(message.channel.id)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM settings WHERE guild_id = %s", (guild_id,))
                if cur.fetchone() is None:
                    cur.execute("INSERT INTO settings (guild_id, reminder_channel_id) VALUES (%s, %s)", (guild_id, channel_id))
                    conn.commit()

# --- Reminders ---
@tasks.loop(minutes=10)
async def remind_tasks():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, user_id, description FROM tasks WHERE status = 'pending'")
            tasks_due = cur.fetchall()

            cur.execute("SELECT guild_id, reminder_channel_id FROM settings")
            channels = {row['guild_id']: row['reminder_channel_id'] for row in cur.fetchall()}

    for task in tasks_due:
        user = await bot.fetch_user(int(task['user_id']))
        if user:
            try:
                await user.send(f"Reminder: You have a pending task - '{task['description']}' (ID: {task['id']})")
            except discord.Forbidden:
                print(f"Cannot send DM to user {task['user_id']}")

# --- Events ---
@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    init_db()

bot.run(DISCORD_TOKEN)
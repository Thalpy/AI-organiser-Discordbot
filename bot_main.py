# Let's start restructuring the bot into a modular format using cogs.
# First, create the main bot file that sets up and loads cogs.

from discord.ext import commands, tasks
from discord import app_commands
import discord
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DISCORD_TOKEN, DB_CONFIG, DEBUG_GUILD_ID

# --- DB Setup ---
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Task list table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    description TEXT,
                    schedule_time TIME,
                    schedule_date DATE,
                    duration_minutes INTEGER DEFAULT 15,
                    location TEXT,
                    priority BOOLEAN DEFAULT FALSE,
                    deadline TIMESTAMP,
                    mirrored_users TEXT[],
                    due_time TIMESTAMP,
                    start_time TIMESTAMP,
                    stop_time TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    num_sessions INTEGER DEFAULT 0,
                    actual_duration FLOAT DEFAULT 0
                )
            """)
            # Patch in missing columns for existing installs (For development - remove for production)
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS schedule_time TIME;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS schedule_date DATE;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 15;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location TEXT;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS deadline TIMESTAMP;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS mirrored_users TEXT[];")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_time TIMESTAMP;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS start_time TIMESTAMP;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS stop_time TIMESTAMP;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS num_sessions INTEGER DEFAULT 0;")
            cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS actual_duration FLOAT DEFAULT 0;")

            # User settings table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id TEXT PRIMARY KEY,
                    reminder_channel_id TEXT
                )
            """)

            # User preferences table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    work_start TIME DEFAULT '09:00',
                    work_end TIME DEFAULT '17:00',
                    lunch_duration_minutes INTEGER DEFAULT 30,
                    time_zone TEXT DEFAULT 'GMT',
                    lunch_window_start TIME DEFAULT '12:00',
                    lunch_window_end TIME DEFAULT '14:00'
                )
            """)

            # Task metrics table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS task_metrics (
                    task_id INTEGER PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
                    total_time_minutes INTEGER DEFAULT 0,
                    sessions_count INTEGER DEFAULT 0,
                    delayed_count INTEGER DEFAULT 0,
                    estimated_vs_actual_ratio FLOAT
                )
            """)

            # Google Calendar OAuth token storage
            cur.execute("""
                CREATE TABLE IF NOT EXISTS calendar_tokens (
                    user_id TEXT PRIMARY KEY,
                    token TEXT,
                    refresh_token TEXT,
                    token_uri TEXT,
                    client_id TEXT,
                    client_secret TEXT,
                    scopes TEXT
                )
            """)
            conn.commit()



intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    
    init_db()

    # Debug
    guild = discord.Object(id=DEBUG_GUILD_ID)

    # Clear and re-register commands for this guild only
    bot.tree.clear_commands(guild=guild)
    await bot.load_extension("cogs.tasks")
    await bot.load_extension("cogs.todo_modal")
    await bot.load_extension("cogs.list_modal")
    await bot.load_extension("cogs.calendar_oauth")
    await bot.load_extension("cogs.calendar_ui")
    await bot.load_extension("cogs.calendar_push_test")
    await bot.load_extension("cogs.preferences")
    await bot.tree.sync()
    await bot.tree.sync(guild=guild)
    print("Commands synced.")    
    for cmd in bot.tree.get_commands(guild=guild):
        print(f"↪ Slash command: /{cmd.name}")
    

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")

bot.run(DISCORD_TOKEN)

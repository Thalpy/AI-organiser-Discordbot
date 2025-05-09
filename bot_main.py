# Let's start restructuring the bot into a modular format using cogs.
# First, create the main bot file that sets up and loads cogs.

from discord.ext import commands, tasks
from discord import app_commands
import discord
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
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

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    
    init_db()

    # Debug
    GUILD_ID = 538506324229619745
    guild = discord.Object(id=GUILD_ID)

    # Clear and re-register commands for this guild only
    bot.tree.clear_commands(guild=guild)
    await bot.load_extension("cogs.tasks")
    await bot.tree.sync()
    print("Commands synced.")
    for cmd in bot.tree.get_commands(guild=guild):
        print(f"↪ Slash command: /{cmd.name}")

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")

bot.run(DISCORD_TOKEN)

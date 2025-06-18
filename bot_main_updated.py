# Updated bot_main.py with comprehensive logging and utilities
# Enhanced version using the new utility modules

from discord.ext import commands, tasks
from discord import app_commands
import discord
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DISCORD_TOKEN, DB_CONFIG, DEBUG_GUILD_ID

# Import logging utilities
from utils.logging_config import setup_bot_logging, get_logger, get_performance_logger, get_user_action_logger
from utils.database import DatabaseManager
import logging
import sys
import traceback

# Setup logging first
setup_bot_logging(debug=True)  # Set to False for production
logger = get_logger(__name__)
perf_logger = get_performance_logger("bot_main")
user_logger = get_user_action_logger()

# --- DB Setup with improved logging ---
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    """Initialize database with comprehensive logging"""
    logger.info("Initializing database...")
    perf_logger.start_timer("database_init")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                logger.debug("Creating tasks table...")
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
                
                logger.debug("Adding missing columns to tasks table...")
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

                logger.debug("Creating settings table...")
                # User settings table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        guild_id TEXT PRIMARY KEY,
                        reminder_channel_id TEXT
                    )
                """)

                logger.debug("Creating user_preferences table...")
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

                logger.debug("Creating task_metrics table...")
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

                logger.debug("Creating calendar_tokens table...")
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

                logger.debug("Creating notification system tables...")
                # Notification system tables
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS task_reminders (
                        id SERIAL PRIMARY KEY,
                        task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
                        reminder_type VARCHAR(50) NOT NULL,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(task_id, reminder_type)
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS notification_preferences (
                        user_id TEXT PRIMARY KEY,
                        task_reminders BOOLEAN DEFAULT TRUE,
                        overdue_alerts BOOLEAN DEFAULT TRUE,
                        daily_summaries BOOLEAN DEFAULT TRUE,
                        reminder_minutes INTEGER DEFAULT 15,
                        quiet_hours_start TIME DEFAULT NULL,
                        quiet_hours_end TIME DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS notification_log (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        notification_type VARCHAR(50) NOT NULL,
                        task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        delivery_status VARCHAR(20) DEFAULT 'sent',
                        error_message TEXT DEFAULT NULL
                    )
                """)

                logger.debug("Creating database indexes...")
                # Create indexes for performance
                cur.execute("CREATE INDEX IF NOT EXISTS idx_task_reminders_task_id ON task_reminders(task_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_notification_log_user_id ON notification_log(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_time ON tasks(due_time)")
                
                conn.commit()
                logger.info("Database initialization completed successfully")
                
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.error(traceback.format_exc())
        raise
    finally:
        perf_logger.end_timer("database_init")

# Bot setup with enhanced logging
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    logger.info("Bot setup hook started")
    perf_logger.start_timer("bot_setup")
    
    try:
        # Initialize database
        init_db()

        # Debug guild setup
        guild = discord.Object(id=DEBUG_GUILD_ID)
        logger.info(f"Setting up debug guild: {DEBUG_GUILD_ID}")

        # Clear and re-register commands for this guild only
        bot.tree.clear_commands(guild=guild)
        
        # Load cogs with logging
        cogs_to_load = [
            "cogs.tasks",
            "cogs.todo_modal", 
            "cogs.list_modal",
            "cogs.calendar_oauth",
            "cogs.calendar_ui",
            "cogs.calendar_push_test",
            "cogs.preferences",
            "cogs.scheduler",
            "cogs.notifications"
        ]
        
        for cog in cogs_to_load:
            try:
                logger.debug(f"Loading cog: {cog}")
                await bot.load_extension(cog)
                logger.info(f"Successfully loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
                logger.error(traceback.format_exc())
        
        # Sync commands
        logger.info("Syncing command tree...")
        await bot.tree.sync()
        await bot.tree.sync(guild=guild)
        
        # Log registered commands
        logger.info("Commands synced successfully")
        commands_list = bot.tree.get_commands(guild=guild)
        logger.info(f"Registered {len(commands_list)} slash commands:")
        for cmd in commands_list:
            logger.info(f"  /{cmd.name} - {cmd.description}")
        
        perf_logger.end_timer("bot_setup", f"Loaded {len(cogs_to_load)} cogs and {len(commands_list)} commands")
        
    except Exception as e:
        logger.error(f"Bot setup failed: {e}")
        logger.error(traceback.format_exc())
        raise

@bot.event
async def on_ready():
    logger.info(f"Bot connected successfully as {bot.user}")
    logger.info(f"Bot ID: {bot.user.id}")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Log guild information
    for guild in bot.guilds:
        logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: Exception):
    """Global error handler for application commands"""
    logger.error(f"Command error in /{interaction.command.name if interaction.command else 'unknown'}: {error}")
    logger.error(traceback.format_exc())
    
    user_logger.log_error_interaction(
        str(interaction.user.id),
        type(error).__name__,
        interaction.command.name if interaction.command else "unknown",
        str(error)
    )
    
    # Try to send user-friendly error message
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred. The issue has been logged and will be investigated.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ An unexpected error occurred. The issue has been logged and will be investigated.",
                ephemeral=True
            )
    except:
        logger.error("Failed to send error message to user")

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler for other events"""
    logger.error(f"Error in event {event}: {sys.exc_info()[1]}")
    logger.error(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    """Error handler for prefix commands"""
    logger.error(f"Prefix command error: {error}")
    logger.error(traceback.format_exc())

# Graceful shutdown
async def shutdown_handler():
    """Handle graceful shutdown"""
    logger.info("Shutting down bot...")
    await bot.close()
    logger.info("Bot shutdown complete")

if __name__ == "__main__":
    try:
        logger.info("Starting Discord Task Management Bot...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Discord.py version: {discord.__version__}")
        
        bot.run(DISCORD_TOKEN)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error starting bot: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("Bot process ended")
from discord.ext import commands
from discord import app_commands
import discord
import urllib.parse
import json
import os
import asyncio

from src.calendar_integration import get_calendar_service
from utils.logging_config import get_logger

logger = get_logger(__name__)

# === Load client_id from credentials file ===
CREDENTIALS_FILE = "credentials/client_secret.json"

if not os.path.exists(CREDENTIALS_FILE):
    logger.warning(f"Missing {CREDENTIALS_FILE}. Calendar integration disabled.")
    CLIENT_ID = None
    REDIRECT_URI = None
else:
    with open(CREDENTIALS_FILE) as f:
        client_info = json.load(f)
        CLIENT_ID = client_info["web"]["client_id"]
        REDIRECT_URI = client_info["web"]["redirect_uris"][0]  # Typically http://localhost:8080/oauth2callback

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

class CalendarOAuth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.calendar_service = None

    async def cog_load(self):
        """Initialize the calendar service when the cog loads"""
        try:
            self.calendar_service = await get_calendar_service()
            logger.info("Calendar OAuth cog loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize calendar service: {e}")

    @app_commands.command(name="setup_calendar", description="Link your Google Calendar account")
    async def setup_calendar(self, interaction: discord.Interaction):
        """Set up Google Calendar integration"""
        if not CLIENT_ID:
            await interaction.response.send_message(
                "❌ Calendar integration is not configured. Please contact an administrator.",
                ephemeral=True
            )
            return

        try:
            user_id = str(interaction.user.id)
            
            # Get authorization URL from the calendar service
            if not self.calendar_service:
                self.calendar_service = await get_calendar_service()
            
            auth_url = await self.calendar_service.get_authorization_url(user_id)
            
            embed = discord.Embed(
                title="🗓️ Google Calendar Setup",
                description="Click the link below to connect your Google Calendar account:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Authorization Link",
                value=f"[Click here to authorize]({auth_url})",
                inline=False
            )
            embed.add_field(
                name="What happens next?",
                value="After authorization, your tasks will automatically sync with your Google Calendar.",
                inline=False
            )
            embed.set_footer(text="This link is unique to you and expires in 10 minutes.")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to setup calendar for user {interaction.user.id}: {e}")
            await interaction.response.send_message(
                "❌ Failed to generate calendar setup link. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="calendar_status", description="Check your calendar sync status")
    async def calendar_status(self, interaction: discord.Interaction):
        """Check calendar synchronization status"""
        try:
            user_id = str(interaction.user.id)
            
            if not self.calendar_service:
                self.calendar_service = await get_calendar_service()
            
            status = await self.calendar_service.get_sync_status(user_id)
            
            embed = discord.Embed(
                title="🗓️ Calendar Sync Status",
                color=discord.Color.green() if status.get("sync_enabled") else discord.Color.red()
            )
            
            # Sync status
            sync_status = "✅ Enabled" if status.get("sync_enabled") else "❌ Disabled"
            embed.add_field(name="Sync Status", value=sync_status, inline=True)
            
            # Last sync time
            last_sync = status.get("last_sync")
            if last_sync:
                embed.add_field(name="Last Sync", value=f"<t:{int(last_sync.timestamp())}:R>", inline=True)
            else:
                embed.add_field(name="Last Sync", value="Never", inline=True)
            
            # Pending conflicts
            conflicts = status.get("pending_conflicts", 0)
            embed.add_field(name="Pending Conflicts", value=str(conflicts), inline=True)
            
            # Statistics
            stats = status.get("statistics", {})
            if stats:
                total_tasks = stats.get("total_tasks", 0)
                synced_tasks = stats.get("synced_tasks", 0)
                coverage = stats.get("sync_coverage", 0)
                
                embed.add_field(name="Total Tasks", value=str(total_tasks), inline=True)
                embed.add_field(name="Synced Tasks", value=str(synced_tasks), inline=True)
                embed.add_field(name="Sync Coverage", value=f"{coverage:.1f}%", inline=True)
            
            # Show conflicts if any
            if conflicts > 0:
                embed.add_field(
                    name="⚠️ Conflicts Detected",
                    value=f"You have {conflicts} sync conflicts. Use `/calendar_sync` to resolve them.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to get calendar status for user {interaction.user.id}: {e}")
            await interaction.response.send_message(
                "❌ Failed to retrieve calendar status. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="calendar_sync", description="Manually sync your calendar")
    @app_commands.describe(
        direction="Sync direction: task_to_calendar, calendar_to_task, or bidirectional"
    )
    async def calendar_sync(
        self, 
        interaction: discord.Interaction,
        direction: str = "bidirectional"
    ):
        """Manually trigger calendar synchronization"""
        try:
            user_id = str(interaction.user.id)
            
            if not self.calendar_service:
                self.calendar_service = await get_calendar_service()
            
            # Validate direction
            valid_directions = ["task_to_calendar", "calendar_to_task", "bidirectional"]
            if direction not in valid_directions:
                await interaction.response.send_message(
                    f"❌ Invalid direction. Must be one of: {', '.join(valid_directions)}",
                    ephemeral=True
                )
                return
            
            # Defer response since sync might take a while
            await interaction.response.defer(ephemeral=True)
            
            # Perform sync
            from src.calendar_integration import SyncDirection
            sync_direction = SyncDirection(direction)
            
            result = await self.calendar_service.perform_full_sync(user_id, sync_direction)
            
            if "error" in result:
                await interaction.followup.send(
                    f"❌ Sync failed: {result['error']}",
                    ephemeral=True
                )
                return
            
            # Create result embed
            embed = discord.Embed(
                title="🔄 Calendar Sync Complete",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Tasks → Calendar",
                value=str(result.get("tasks_synced_to_calendar", 0)),
                inline=True
            )
            embed.add_field(
                name="Calendar → Tasks",
                value=str(result.get("calendar_events_synced_to_tasks", 0)),
                inline=True
            )
            embed.add_field(
                name="Conflicts",
                value=f"{result.get('conflicts_resolved', 0)}/{result.get('conflicts_detected', 0)}",
                inline=True
            )
            
            # Show errors if any
            errors = result.get("errors", [])
            if errors:
                error_text = "\n".join(errors[:3])  # Show first 3 errors
                if len(errors) > 3:
                    error_text += f"\n... and {len(errors) - 3} more"
                embed.add_field(name="⚠️ Errors", value=error_text, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to sync calendar for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to sync calendar. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(name="calendar_disable", description="Disable calendar synchronization")
    async def calendar_disable(self, interaction: discord.Interaction):
        """Disable calendar synchronization"""
        try:
            user_id = str(interaction.user.id)
            
            if not self.calendar_service:
                self.calendar_service = await get_calendar_service()
            
            success = await self.calendar_service.disable_sync(user_id)
            
            if success:
                embed = discord.Embed(
                    title="🗓️ Calendar Sync Disabled",
                    description="Calendar synchronization has been disabled for your account.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="What this means:",
                    value="• Tasks will no longer sync to your calendar\n• Existing calendar events will remain unchanged\n• You can re-enable sync anytime with `/setup_calendar`",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Failed to Disable Sync",
                    description="Could not disable calendar synchronization. Please try again.",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to disable calendar sync for user {interaction.user.id}: {e}")
            await interaction.response.send_message(
                "❌ Failed to disable calendar sync. Please try again later.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(CalendarOAuth(bot))

from discord.ext import commands
from discord import app_commands
import discord
import psycopg2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class CalendarPush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="calendar_push_test", description="Push a test event to your Google Calendar")
    async def push_test(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT token, refresh_token, token_uri, client_id, client_secret, scopes
                    FROM calendar_tokens WHERE user_id = %s
                """, (user_id,))
                row = cur.fetchone()

        if not row:
            await interaction.response.send_message("❌ No Google Calendar token found. Please run /setup_calendar first.", ephemeral=True)
            return

        creds = Credentials(
            token=row[0],
            refresh_token=row[1],
            token_uri=row[2],
            client_id=row[3],
            client_secret=row[4],
            scopes=row[5].split()
        )

        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": "🧪 Whimsylabs Test Event",
            "description": "This is a test event created by the Discord bot.",
            "start": {
                "dateTime": "2025-05-10T14:00:00",
                "timeZone": "Europe/London"
            },
            "end": {
                "dateTime": "2025-05-10T14:30:00",
                "timeZone": "Europe/London"
            },
        }

        created = service.events().insert(calendarId="primary", body=event).execute()

        await interaction.response.send_message(
            f"✅ Test event created: [{created['summary']}]({created['htmlLink']})",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(CalendarPush(bot))

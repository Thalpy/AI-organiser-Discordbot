# This is the start of the cog file: cogs/calendar_oauth.py
# It registers a /setup_calendar command and generates the Google OAuth URL for each user.

from discord.ext import commands
from discord import app_commands
import discord
import urllib.parse

# Constants you need to replace
CLIENT_ID = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
REDIRECT_URI = "http://localhost:8080/"
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

class CalendarOAuth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_calendar", description="Link your Google Calendar account")
    async def setup_calendar(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        state = str(user_id)  # Can expand later with nonce/hash

        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

        await interaction.response.send_message(
            f"Click the link below to connect your Google Calendar:\n\n{auth_url}",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(CalendarOAuth(bot))

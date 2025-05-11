from discord.ext import commands
from discord import app_commands
import discord
import urllib.parse
import json
import os

# === Load client_id from credentials file ===
CREDENTIALS_FILE = "credentials/client_secret.json"

if not os.path.exists(CREDENTIALS_FILE):
    raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}. Upload your OAuth credentials.")

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

    @app_commands.command(name="setup_calendar", description="Link your Google Calendar account")
    async def setup_calendar(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        state = str(user_id)

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

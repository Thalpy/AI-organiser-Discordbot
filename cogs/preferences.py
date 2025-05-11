# cogs/preferences.py

from discord.ext import commands
from discord import app_commands
import discord
from discord.ui import View, Button, Modal, TextInput
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class Preferences(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="preferences", description="Edit your user preferences for scheduling")
    async def preferences(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO user_preferences (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id,))
                conn.commit()

                cur.execute("SELECT * FROM user_preferences WHERE user_id = %s", (user_id,))
                prefs = cur.fetchone()

        embed = discord.Embed(title="🛠️ Your Preferences", color=discord.Color.teal())
        embed.add_field(name="Work Start", value=str(prefs["work_start"]), inline=True)
        embed.add_field(name="Work End", value=str(prefs["work_end"]), inline=True)
        embed.add_field(name="Lunch Duration", value=f"{prefs['lunch_duration_minutes']} min", inline=True)
        embed.add_field(name="Lunch Window", value=f"{prefs['lunch_window_start']}–{prefs['lunch_window_end']}", inline=True)
        embed.add_field(name="Time Zone", value=prefs["time_zone"], inline=True)

        view = PreferencesView(user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PreferencesView(View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

        self.add_item(EditButton("Work Start", "work_start", "HH:MM (24h)", self.user_id))
        self.add_item(EditButton("Work End", "work_end", "HH:MM (24h)", self.user_id))
        self.add_item(EditButton("Lunch Duration", "lunch_duration_minutes", "Minutes", self.user_id))
        self.add_item(EditButton("Lunch Window Start", "lunch_window_start", "HH:MM", self.user_id))
        self.add_item(EditButton("Lunch Window End", "lunch_window_end", "HH:MM", self.user_id))
        self.add_item(TimeZoneSelect(self.user_id))

class EditButton(Button):
    def __init__(self, label, field_name, placeholder, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.field_name = field_name
        self.placeholder = placeholder
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditPreferenceModal(self.label, self.field_name, self.placeholder, self.user_id))

class TimeZoneSelect(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id

        options = [
            discord.SelectOption(label="GMT"),
            discord.SelectOption(label="UTC"),
            discord.SelectOption(label="Europe/London"),
            discord.SelectOption(label="Europe/Berlin"),
            discord.SelectOption(label="America/New_York"),
            discord.SelectOption(label="America/Los_Angeles"),
            discord.SelectOption(label="Asia/Tokyo"),
            discord.SelectOption(label="Asia/Kolkata"),
        ]

        super().__init__(
            placeholder="Select your time zone",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_zone = self.values[0]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_preferences
                    SET time_zone = %s
                    WHERE user_id = %s
                """, (selected_zone, self.user_id))
                conn.commit()

        await interaction.response.send_message(f"🕓 Time zone set to `{selected_zone}`", ephemeral=True)


class EditPreferenceModal(Modal, title="Edit Preference"):
    def __init__(self, label, field_name, placeholder, user_id):
        super().__init__()
        self.label = label
        self.field_name = field_name
        self.user_id = user_id
        self.input = TextInput(label=label, placeholder=placeholder, required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip()

        try:
            # --- Validate Time ---
            if self.field_name in ["work_start", "work_end", "lunch_window_start", "lunch_window_end"]:
                hour, minute = map(int, value.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time range")
                value = f"{hour:02d}:{minute:02d}"

            # --- Validate Integer Duration ---
            elif self.field_name == "lunch_duration_minutes":
                minutes = int(value)
                if minutes < 10 or minutes > 180:
                    raise ValueError("Lunch must be 10–180 minutes")
                value = str(minutes)

            # --- Validate Time Zone ---
            elif self.field_name == "time_zone":
                valid_zones = [
                    "GMT", "UTC", "Europe/London", "Europe/Berlin", "America/New_York",
                    "America/Los_Angeles", "Asia/Tokyo", "Asia/Kolkata"
                ]
                if value not in valid_zones:
                    raise ValueError(f"Use a valid time zone. e.g. 'Europe/London'")

            # Update database
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        UPDATE user_preferences
                        SET {self.field_name} = %s
                        WHERE user_id = %s
                    """, (value, self.user_id))
                    conn.commit()

            await interaction.response.send_message(f"✅ Updated **{self.field_name}** to `{value}`.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Preferences(bot))

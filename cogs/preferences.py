# cogs/preferences.py - Updated with utilities and logging

from discord.ext import commands
from discord import app_commands
import discord
from discord.ui import View, Button, Modal, TextInput
from utils.database import UserQueries
from utils.discord_helpers import EmbedBuilder, ErrorHandler, ValidationHelpers
from utils.validation import UserPreferencesValidator, InputValidator
import logging

logger = logging.getLogger(__name__)

class Preferences(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Preferences cog initialized")

    @app_commands.command(name="preferences", description="Edit your user preferences for scheduling")
    async def preferences(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        logger.info(f"User {user_id} accessing preferences")

        try:
            # Get user preferences (creates defaults if none exist)
            prefs = await UserQueries.get_user_preferences(user_id)

            embed = EmbedBuilder.create_embed(
                title="⚙️ Your Preferences",
                description="Configure your work schedule and preferences",
                color=EmbedBuilder.SECONDARY,
                fields=[
                    ("🌅 Work Start", str(prefs["work_start"]), True),
                    ("🌇 Work End", str(prefs["work_end"]), True),
                    ("🍽️ Lunch Duration", f"{prefs['lunch_duration_minutes']} minutes", True),
                    ("⏰ Lunch Window", f"{prefs['lunch_window_start']} - {prefs['lunch_window_end']}", True),
                    ("🌍 Time Zone", prefs["time_zone"], True),
                    ("💡 Tip", "Click buttons below to modify settings", False)
                ],
                footer="Changes are saved automatically"
            )

            view = PreferencesView(user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            logger.info(f"Preferences displayed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to load preferences for user {user_id}: {e}")
            await ErrorHandler.handle_error(
                interaction, e, 
                "Failed to load your preferences. Please try again."
            )

class PreferencesView(View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        logger.debug(f"PreferencesView created for user {user_id}")

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
        logger.debug(f"User {self.user_id} clicked edit button for {self.field_name}")
        try:
            await interaction.response.send_modal(
                EditPreferenceModal(self.label, self.field_name, self.placeholder, self.user_id)
            )
        except Exception as e:
            logger.error(f"Error opening modal for {self.field_name}: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to open settings modal.")

class TimeZoneSelect(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id

        options = [
            discord.SelectOption(label="GMT", description="Greenwich Mean Time"),
            discord.SelectOption(label="UTC", description="Coordinated Universal Time"),
            discord.SelectOption(label="Europe/London", description="London, UK"),
            discord.SelectOption(label="Europe/Berlin", description="Berlin, Germany"),
            discord.SelectOption(label="America/New_York", description="New York, USA"),
            discord.SelectOption(label="America/Los_Angeles", description="Los Angeles, USA"),
            discord.SelectOption(label="Asia/Tokyo", description="Tokyo, Japan"),
            discord.SelectOption(label="Asia/Kolkata", description="Mumbai, India"),
        ]

        super().__init__(
            placeholder="Select your time zone",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_zone = self.values[0]
        logger.info(f"User {self.user_id} updating timezone to {selected_zone}")
        
        try:
            # Validate timezone
            valid, validated_zone, error = InputValidator.validate_timezone(selected_zone)
            if not valid:
                embed = EmbedBuilder.error_embed("Invalid Timezone", error)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Update preference
            success = await UserQueries.update_user_preference(self.user_id, 'time_zone', validated_zone)
            
            if success:
                embed = EmbedBuilder.success_embed(
                    "Timezone Updated",
                    f"Your timezone has been set to **{validated_zone}**"
                )
                logger.info(f"Timezone updated successfully for user {self.user_id}")
            else:
                embed = EmbedBuilder.error_embed(
                    "Update Failed",
                    "Could not update your timezone. Please try again."
                )
                logger.error(f"Failed to update timezone for user {self.user_id}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error updating timezone for user {self.user_id}: {e}")
            await ErrorHandler.handle_error(
                interaction, e,
                "Failed to update timezone. Please try again."
            )

class EditPreferenceModal(Modal, title="Edit Preference"):
    def __init__(self, label, field_name, placeholder, user_id):
        super().__init__()
        self.label = label
        self.field_name = field_name
        self.user_id = user_id
        self.input = TextInput(label=label, placeholder=placeholder, required=True)
        self.add_item(self.input)
        logger.debug(f"EditPreferenceModal created for {field_name}")

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip()
        logger.info(f"User {self.user_id} updating {self.field_name} to {value}")

        try:
            # Validate based on field type
            if self.field_name in ["work_start", "work_end", "lunch_window_start", "lunch_window_end"]:
                valid, time_obj, error = InputValidator.validate_time_input(value)
                if not valid:
                    embed = EmbedBuilder.error_embed("Invalid Time", error)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                # Additional validation for work hours
                if self.field_name in ["work_start", "work_end"]:
                    # Get current preferences to validate work hours together
                    prefs = await UserQueries.get_user_preferences(self.user_id)
                    start_time = value if self.field_name == "work_start" else str(prefs.get("work_start", "09:00"))
                    end_time = value if self.field_name == "work_end" else str(prefs.get("work_end", "17:00"))
                    
                    work_valid, work_error = UserPreferencesValidator.validate_work_hours(start_time, end_time)
                    if not work_valid:
                        embed = EmbedBuilder.error_embed("Invalid Work Hours", work_error)
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                
                validated_value = time_obj.strftime('%H:%M')

            elif self.field_name == "lunch_duration_minutes":
                valid, duration, error = InputValidator.validate_duration_input(value)
                if not valid:
                    embed = EmbedBuilder.error_embed("Invalid Duration", error)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                if duration < 10 or duration > 180:
                    embed = EmbedBuilder.error_embed(
                        "Invalid Duration", 
                        "Lunch duration must be between 10 and 180 minutes"
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                validated_value = str(duration)

            elif self.field_name == "time_zone":
                valid, timezone, error = InputValidator.validate_timezone(value)
                if not valid:
                    embed = EmbedBuilder.error_embed("Invalid Timezone", error)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                validated_value = timezone

            else:
                validated_value = value

            # Update database
            success = await UserQueries.update_user_preference(self.user_id, self.field_name, validated_value)
            
            if success:
                embed = EmbedBuilder.success_embed(
                    "Preference Updated",
                    f"**{self.label}** has been updated to `{validated_value}`"
                )
                logger.info(f"Successfully updated {self.field_name} for user {self.user_id}")
            else:
                embed = EmbedBuilder.error_embed(
                    "Update Failed",
                    "Could not update your preference. Please try again."
                )
                logger.error(f"Failed to update {self.field_name} for user {self.user_id}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error updating {self.field_name} for user {self.user_id}: {e}")
            await ErrorHandler.handle_error(
                interaction, e,
                f"Failed to update {self.label.lower()}. Please try again."
            )

async def setup(bot):
    await bot.add_cog(Preferences(bot))
    logger.info("Preferences cog loaded successfully")
# Notification Settings UI for Discord Task Management Bot
# Handles user interface for notification preferences

import discord
from discord.ui import View, Button, Select, Modal, TextInput
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class NotificationSettingsView(View):
    def __init__(self, user_id: str, current_prefs: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.current_prefs = current_prefs
        
        # Add toggle buttons
        self.add_item(ToggleButton("Task Reminders", "task_reminders", current_prefs.get('task_reminders', True)))
        self.add_item(ToggleButton("Overdue Alerts", "overdue_alerts", current_prefs.get('overdue_alerts', True)))
        self.add_item(ToggleButton("Daily Summaries", "daily_summaries", current_prefs.get('daily_summaries', True)))
        
        # Add reminder time selector
        self.add_item(ReminderTimeSelect(current_prefs.get('reminder_minutes', 15)))

class ToggleButton(Button):
    def __init__(self, label: str, setting_key: str, current_value: bool):
        self.setting_key = setting_key
        self.current_value = current_value
        
        style = discord.ButtonStyle.success if current_value else discord.ButtonStyle.secondary
        emoji = "✅" if current_value else "❌"
        
        super().__init__(label=label, style=style, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        # Toggle the value
        new_value = not self.current_value
        
        # Update database
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO notification_preferences (user_id, {self.setting_key})
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET {self.setting_key} = EXCLUDED.{self.setting_key}
                """, (self.view.user_id, new_value))
                conn.commit()

        # Update button appearance
        self.current_value = new_value
        self.style = discord.ButtonStyle.success if new_value else discord.ButtonStyle.secondary
        self.emoji = "✅" if new_value else "❌"
        
        # Update the view
        await interaction.response.edit_message(
            content=f"🔔 **{self.label}** {'enabled' if new_value else 'disabled'}",
            view=self.view
        )

class ReminderTimeSelect(Select):
    def __init__(self, current_minutes: int):
        options = [
            discord.SelectOption(label="5 minutes before", value="5", default=current_minutes==5),
            discord.SelectOption(label="10 minutes before", value="10", default=current_minutes==10),
            discord.SelectOption(label="15 minutes before", value="15", default=current_minutes==15),
            discord.SelectOption(label="30 minutes before", value="30", default=current_minutes==30),
            discord.SelectOption(label="60 minutes before", value="60", default=current_minutes==60),
        ]
        
        super().__init__(
            placeholder="Choose reminder timing...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        new_minutes = int(self.values[0])
        
        # Update database
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO notification_preferences (user_id, reminder_minutes)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET reminder_minutes = EXCLUDED.reminder_minutes
                """, (self.view.user_id, new_minutes))
                conn.commit()

        await interaction.response.send_message(
            f"⏰ Reminder time updated to **{new_minutes} minutes** before tasks",
            ephemeral=True
        )

class QuietHoursModal(Modal, title="🌙 Set Quiet Hours"):
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        
        self.start_time = TextInput(
            label="Quiet Hours Start (HH:MM)",
            placeholder="22:00",
            required=True,
            max_length=5
        )
        
        self.end_time = TextInput(
            label="Quiet Hours End (HH:MM)",
            placeholder="08:00",
            required=True,
            max_length=5
        )
        
        self.add_item(self.start_time)
        self.add_item(self.end_time)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate time format
            start_hour, start_min = map(int, self.start_time.value.split(':'))
            end_hour, end_min = map(int, self.end_time.value.split(':'))
            
            if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
                raise ValueError("Invalid start time")
            if not (0 <= end_hour <= 23 and 0 <= end_min <= 59):
                raise ValueError("Invalid end time")
            
            # Update database
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO notification_preferences (user_id, quiet_hours_start, quiet_hours_end)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET 
                            quiet_hours_start = EXCLUDED.quiet_hours_start,
                            quiet_hours_end = EXCLUDED.quiet_hours_end
                    """, (self.user_id, self.start_time.value, self.end_time.value))
                    conn.commit()

            await interaction.response.send_message(
                f"🌙 Quiet hours set: **{self.start_time.value}** to **{self.end_time.value}**\n"
                "No notifications will be sent during these hours.",
                ephemeral=True
            )
            
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ Invalid time format. Please use HH:MM (24-hour format)",
                ephemeral=True
            )
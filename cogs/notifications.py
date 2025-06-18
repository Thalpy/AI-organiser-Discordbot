# Notification System for Discord Task Management Bot
# Handles sending reminders and alerts to users

from discord.ext import commands, tasks
from discord import app_commands
import discord
import datetime
import asyncio
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG
from .notification_utils import NotificationUtils

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class NotificationManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Start notification checking tasks
        self.check_task_reminders.start()
        self.check_overdue_tasks.start()
        self.send_daily_schedules.start()

    def cog_unload(self):
        self.check_task_reminders.cancel()
        self.check_overdue_tasks.cancel()
        self.send_daily_schedules.cancel()

    @tasks.loop(minutes=5)
    async def check_task_reminders(self):
        """Check for tasks that need reminders (15 minutes before due time)"""
        await self.send_task_reminders()

    @tasks.loop(minutes=30)
    async def check_overdue_tasks(self):
        """Check for overdue tasks every 30 minutes"""
        await self.send_overdue_alerts()

    @tasks.loop(hours=24)
    async def send_daily_schedules(self):
        """Send daily schedule summaries at 8 AM"""
        current_time = datetime.datetime.now().time()
        target_time = datetime.time(8, 0)  # 8 AM
        
        # Only run at approximately 8 AM
        if abs((datetime.datetime.combine(datetime.date.today(), current_time) - 
                datetime.datetime.combine(datetime.date.today(), target_time)).total_seconds()) < 1800:  # 30 min window
            await self.send_daily_schedule_summaries()

    @check_task_reminders.before_loop
    @check_overdue_tasks.before_loop
    @send_daily_schedules.before_loop
    async def before_notification_loops(self):
        await self.bot.wait_until_ready()

    async def send_task_reminders(self):
        """Send reminders for tasks starting soon (based on user preferences)"""
        now = datetime.datetime.now()
        
        # Get all users and their reminder preferences
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT t.user_id, 
                           COALESCE(np.reminder_minutes, 15) as reminder_minutes
                    FROM tasks t
                    LEFT JOIN notification_preferences np ON t.user_id = np.user_id
                    WHERE t.status = 'pending' AND t.due_time IS NOT NULL
                """)
                users_with_prefs = cur.fetchall()

        tasks_to_remind = []
        for user_pref in users_with_prefs:
            user_id = user_pref['user_id']
            reminder_minutes = user_pref['reminder_minutes']
            
            # Check if user wants reminders and it's not quiet hours
            if not NotificationUtils.should_send_notification(user_id, 'task_reminder'):
                continue
                
            reminder_time = now + datetime.timedelta(minutes=reminder_minutes)
            
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT t.id, t.user_id, t.description, t.due_time, t.duration_minutes, t.location
                        FROM tasks t
                        WHERE t.user_id = %s
                        AND t.status = 'pending'
                        AND t.due_time BETWEEN %s AND %s
                        AND NOT EXISTS (
                            SELECT 1 FROM task_reminders tr 
                            WHERE tr.task_id = t.id AND tr.reminder_type = 'pre_task'
                        )
                    """, (user_id, now, reminder_time))
                    
                    user_tasks = cur.fetchall()
                    tasks_to_remind.extend(user_tasks)

        for task in tasks_to_remind:
            await self.send_task_reminder(task)
            await self.mark_reminder_sent(task['id'], 'pre_task')

    async def send_task_reminder(self, task: Dict):
        """Send a reminder for a specific task"""
        try:
            user = await self.bot.fetch_user(int(task['user_id']))
            if not user:
                return

            embed = discord.Embed(
                title="⏰ Task Reminder",
                description=f"Your task **{task['description']}** starts in 15 minutes!",
                color=discord.Color.orange(),
                timestamp=task['due_time']
            )
            
            embed.add_field(
                name="📅 Scheduled Time", 
                value=task['due_time'].strftime('%H:%M'), 
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Duration", 
                value=f"{task['duration_minutes']} minutes", 
                inline=True
            )
            
            if task['location']:
                embed.add_field(
                    name="📍 Location", 
                    value=task['location'], 
                    inline=True
                )

            embed.set_footer(text="Use /start to begin this task when ready")

            await user.send(embed=embed)
            print(f"✅ Sent reminder to user {task['user_id']} for task: {task['description']}")
            
        except discord.Forbidden:
            print(f"❌ Cannot send DM to user {task['user_id']}")
        except Exception as e:
            print(f"❌ Error sending reminder: {e}")

    async def send_overdue_alerts(self):
        """Send alerts for overdue tasks"""
        now = datetime.datetime.now()
        
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT t.id, t.user_id, t.description, t.due_time, t.duration_minutes
                    FROM tasks t
                    WHERE t.status = 'pending'
                    AND t.due_time < %s
                    AND NOT EXISTS (
                        SELECT 1 FROM task_reminders tr 
                        WHERE tr.task_id = t.id AND tr.reminder_type = 'overdue'
                        AND tr.sent_at > %s
                    )
                """, (now, now - datetime.timedelta(hours=1)))  # Don't spam - only once per hour
                
                overdue_tasks = cur.fetchall()

        for task in overdue_tasks:
            await self.send_overdue_alert(task)
            await self.mark_reminder_sent(task['id'], 'overdue')

    async def send_overdue_alert(self, task: Dict):
        """Send an overdue alert for a specific task"""
        try:
            user = await self.bot.fetch_user(int(task['user_id']))
            if not user:
                return

            now = datetime.datetime.now()
            overdue_duration = now - task['due_time']
            overdue_minutes = int(overdue_duration.total_seconds() / 60)

            embed = discord.Embed(
                title="🚨 Overdue Task Alert",
                description=f"Your task **{task['description']}** is {overdue_minutes} minutes overdue!",
                color=discord.Color.red(),
                timestamp=now
            )
            
            embed.add_field(
                name="📅 Was Scheduled", 
                value=task['due_time'].strftime('%H:%M'), 
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Duration", 
                value=f"{task['duration_minutes']} minutes", 
                inline=True
            )

            embed.set_footer(text="Use /start to begin this task now, or /delay to reschedule")

            await user.send(embed=embed)
            print(f"🚨 Sent overdue alert to user {task['user_id']} for task: {task['description']}")
            
        except discord.Forbidden:
            print(f"❌ Cannot send DM to user {task['user_id']}")
        except Exception as e:
            print(f"❌ Error sending overdue alert: {e}")

    async def send_daily_schedule_summaries(self):
        """Send daily schedule summaries to all users"""
        today = datetime.date.today()
        
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all users with tasks scheduled for today
                cur.execute("""
                    SELECT DISTINCT user_id FROM tasks 
                    WHERE schedule_date = %s AND status = 'pending'
                """, (today,))
                users_with_tasks = cur.fetchall()

        for user_row in users_with_tasks:
            await self.send_daily_schedule_summary(user_row['user_id'], today)

    async def send_daily_schedule_summary(self, user_id: str, date: datetime.date):
        """Send daily schedule summary to a specific user"""
        try:
            user = await self.bot.fetch_user(int(user_id))
            if not user:
                return

            # Get user's tasks for the day
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT description, due_time, duration_minutes, priority, location
                        FROM tasks 
                        WHERE user_id = %s AND schedule_date = %s AND status = 'pending'
                        ORDER BY due_time ASC
                    """, (user_id, date))
                    tasks = cur.fetchall()

            if not tasks:
                return

            embed = discord.Embed(
                title=f"🌅 Good Morning! Your Schedule for {date.strftime('%B %d, %Y')}",
                description=f"You have {len(tasks)} tasks scheduled today",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )

            schedule_text = ""
            for task in tasks:
                time_str = task['due_time'].strftime('%H:%M')
                priority_icon = "🔥" if task['priority'] else "📋"
                location_str = f" @ {task['location']}" if task['location'] else ""
                
                schedule_text += f"{priority_icon} **{time_str}** - {task['description']} ({task['duration_minutes']}min){location_str}\n"

            embed.add_field(name="📅 Today's Schedule", value=schedule_text, inline=False)
            embed.set_footer(text="Have a productive day! Use /start when you're ready to begin tasks.")

            await user.send(embed=embed)
            print(f"🌅 Sent daily schedule to user {user_id}")
            
        except discord.Forbidden:
            print(f"❌ Cannot send DM to user {user_id}")
        except Exception as e:
            print(f"❌ Error sending daily schedule: {e}")

    async def mark_reminder_sent(self, task_id: int, reminder_type: str):
        """Mark that a reminder has been sent for a task"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO task_reminders (task_id, reminder_type, sent_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (task_id, reminder_type) DO UPDATE SET sent_at = EXCLUDED.sent_at
                """, (task_id, reminder_type, datetime.datetime.now()))
                conn.commit()

    @app_commands.command(name="notification_settings", description="Configure your notification preferences")
    async def notification_settings(self, interaction: discord.Interaction):
        """Allow users to configure notification preferences"""
        user_id = str(interaction.user.id)
        
        # Get current settings
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM notification_preferences WHERE user_id = %s
                """, (user_id,))
                prefs = cur.fetchone()

        if not prefs:
            # Create default preferences
            prefs = {
                'task_reminders': True,
                'overdue_alerts': True,
                'daily_summaries': True,
                'reminder_minutes': 15
            }

        embed = discord.Embed(
            title="🔔 Notification Settings",
            description="Configure when and how you receive notifications",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Task Reminders", 
            value="✅ Enabled" if prefs['task_reminders'] else "❌ Disabled", 
            inline=True
        )
        
        embed.add_field(
            name="🚨 Overdue Alerts", 
            value="✅ Enabled" if prefs['overdue_alerts'] else "❌ Disabled", 
            inline=True
        )
        
        embed.add_field(
            name="🌅 Daily Summaries", 
            value="✅ Enabled" if prefs['daily_summaries'] else "❌ Disabled", 
            inline=True
        )
        
        embed.add_field(
            name="⏰ Reminder Time", 
            value=f"{prefs['reminder_minutes']} minutes before", 
            inline=True
        )

        from .notification_settings import NotificationSettingsView
        view = NotificationSettingsView(user_id, prefs)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(NotificationManager(bot))
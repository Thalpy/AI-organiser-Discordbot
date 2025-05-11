# This is the file: cogs/calendar_ui.py
# It defines /calendar week and /calendar today for simulated calendar display

from discord.ext import commands
from discord import app_commands
import discord
import datetime
import calendar
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class CalendarUI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="calendar_today", description="View your tasks for today")
    async def calendar_today(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + datetime.timedelta(days=1)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, description, due_time, status FROM tasks
                    WHERE user_id = %s AND due_time BETWEEN %s AND %s
                    ORDER BY due_time ASC
                """, (user_id, today_start, today_end))
                tasks = cur.fetchall()

        if not tasks:
            await interaction.response.send_message("📭 You have no tasks scheduled for today.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📅 Tasks for Today",
            description="\n".join([f"• `{t['due_time'].strftime('%H:%M')}` - {t['description']} (**{t['status']}**)" for t in tasks]),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="calendar_week", description="View a week calendar of your tasks")
    async def calendar_week(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        today = datetime.datetime.now()
        week_start = today - datetime.timedelta(days=today.weekday())  # Monday
        week_end = week_start + datetime.timedelta(days=7)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, description, due_time, status FROM tasks
                    WHERE user_id = %s AND due_time BETWEEN %s AND %s
                    ORDER BY due_time ASC
                """, (user_id, week_start, week_end))
                tasks = cur.fetchall()

        days = {i: [] for i in range(7)}  # Mon–Sun
        for t in tasks:
            day_idx = t["due_time"].weekday()
            time_str = t["due_time"].strftime("%H:%M")
            days[day_idx].append(f"`{time_str}` {t['description']} (**{t['status']}**)")

        embed = discord.Embed(title="🗓️ Week View", color=discord.Color.green())
        for i in range(7):
            day_name = calendar.day_name[i]
            if days[i]:
                embed.add_field(name=day_name, value="\n".join(days[i]), inline=False)
            else:
                embed.add_field(name=day_name, value="(no tasks)", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(CalendarUI(bot))

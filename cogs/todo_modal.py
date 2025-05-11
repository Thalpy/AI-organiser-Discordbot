from discord.ext import commands
from discord import app_commands
import discord
import datetime
import psycopg2
from config import DB_CONFIG

# Temporary cache to store first modal values
USER_TASK_CACHE = {}

# Store temporary mirror info
USER_MIRROR_CACHE = {}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class TaskModal(discord.ui.Modal, title="📝 New Task"):
    def __init__(self, user_id, task_name):
        super().__init__()
        self.user_id = user_id
        self.task_name = task_name

        self.datetime_str = discord.ui.TextInput(label="Schedule (MM/DD HH:MM)", required=False)
        self.duration = discord.ui.TextInput(label="Duration in minutes (default 15)", required=False)
        self.deadline = discord.ui.TextInput(label="Deadline (YYYY-MM-DD HH:MM, optional)", required=False)
        self.location = discord.ui.TextInput(label="Location or URL (optional)", required=False)

        self.add_item(self.datetime_str)
        self.add_item(self.duration)
        self.add_item(self.deadline)
        self.add_item(self.location)

    async def on_submit(self, interaction: discord.Interaction):
        USER_TASK_CACHE[self.user_id] = {
            "task": self.task_name,
            "datetime_str": self.datetime_str.value.strip(),
            "duration": self.duration.value.strip(),
            "deadline": self.deadline.value.strip(),
            "location": self.location.value.strip(),
            "mirrored_users": []
        }

        await interaction.response.send_message(
            "✅ Task created. Would you like to configure more settings?",
            view=PostCreateOptions(self.user_id),
            ephemeral=True
        )

class MirrorUserView(discord.ui.View):
    def __init__(self, user_id, guild):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.guild = guild
        self.add_item(MirrorUserDropdown(user_id, guild))

class MirrorUserDropdown(discord.ui.Select):
    def __init__(self, user_id, guild):
        self.user_id = user_id
        self.guild = guild

        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in guild.members if not member.bot and member.id != user_id
        ][:25]  # Max options

        super().__init__(
            placeholder="Select a user to mirror with...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]

        await interaction.response.send_modal(MirrorTimeModal(self.user_id, selected_id))

class MirrorTimeModal(discord.ui.Modal, title="🕒 Mirror Time"):
    def __init__(self, user_id, mirror_user_id):
        super().__init__()
        self.user_id = user_id
        self.mirror_user_id = mirror_user_id

        self.datetime_str = discord.ui.TextInput(label="Date & Time (MM/DD HH:MM)", required=True)
        self.add_item(self.datetime_str)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            datetime_str = self.datetime_str.value.strip()
            mm, dd = map(int, datetime_str.split(" ")[0].split("/"))
            hh, mi = map(int, datetime_str.split(" ")[1].split(":"))
            scheduled = datetime.datetime(datetime.datetime.now().year, mm, dd, hh, mi)

            if self.user_id in USER_TASK_CACHE:
                USER_TASK_CACHE[self.user_id]["mirrored_users"].append({"user_id": str(self.mirror_user_id), "time": scheduled})

            # Optional: add default task to mirror user in DB
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO tasks (user_id, description, schedule_time, schedule_date, duration_minutes, priority, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.mirror_user_id,
                        f"Mirrored Task from <@{self.user_id}>",
                        scheduled.time(),
                        scheduled.date(),
                        15,
                        False,
                        'pending'
                    ))
                    conn.commit()

            await interaction.response.send_message(f"🔁 Task mirrored with <@{self.mirror_user_id}> at {scheduled}.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to parse input: {e}", ephemeral=True)

class PostCreateOptions(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id

    @discord.ui.button(label="⭐ Set Priority", style=discord.ButtonStyle.primary)
    async def set_priority(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your task.", ephemeral=True)
            return
        data = USER_TASK_CACHE.get(self.user_id)
        if data:
            data["priority"] = True
            await interaction.response.send_message("⭐ Priority enabled.", ephemeral=True)

    @discord.ui.button(label="👥 Mirror Task", style=discord.ButtonStyle.secondary)
    async def mirror_task(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Choose a user to mirror this task with:", view=MirrorUserView(self.user_id, interaction.guild), ephemeral=True)

    @discord.ui.button(label="✏️ Edit Settings", style=discord.ButtonStyle.success)
    async def edit_task(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your task.", ephemeral=True)
            return
        task = USER_TASK_CACHE.get(self.user_id)
        await interaction.response.send_modal(TaskModal(self.user_id, task["task"]))

    @discord.ui.button(label="✅ Confirm & Save", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = USER_TASK_CACHE.get(self.user_id)
        if not data:
            await interaction.response.send_message("❌ No task data to save.", ephemeral=True)
            return

        now = datetime.datetime.now()
        task = data["task"]
        datetime_str = data["datetime_str"]
        duration = int(data.get("duration") or 15)
        location = data.get("location") or None
        deadline_str = data.get("deadline") or None
        priority = data.get("priority", False)
        mirrored_users = data.get("mirrored_users", [])

        schedule_date, schedule_time, due_time = None, None, None
        deadline = None

        try:
            if datetime_str:
                mm, dd, timepart = datetime_str.split("/")[0], datetime_str.split("/")[1], datetime_str.split(" ")[1]
                hour, minute = map(int, timepart.split(":"))
                schedule_date = datetime.date(year=now.year, month=int(mm), day=int(dd))
                schedule_time = datetime.time(hour, minute)
                due_time = datetime.datetime.combine(schedule_date, schedule_time)

            if deadline_str:
                deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")

        except Exception as e:
            await interaction.response.send_message(f"❌ Invalid input: {e}", ephemeral=True)
            return

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (
                        user_id, description, schedule_time, schedule_date, duration_minutes,
                        priority, deadline, mirrored_users, location, due_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(self.user_id),
                    task,
                    schedule_time,
                    schedule_date,
                    duration,
                    priority,
                    deadline,
                    [m["user_id"] for m in mirrored_users] if mirrored_users else None,
                    location,
                    due_time
                ))
                conn.commit()

        USER_TASK_CACHE.pop(self.user_id, None)
        await interaction.response.send_message(f"✅ Task **{task}** saved to database.", ephemeral=True)

class TaskTodoModalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="todo", description="Add a new task")
    @app_commands.describe(task_name="Short name for the task")
    async def open_modal(self, interaction: discord.Interaction, task_name: str):
        await interaction.response.send_modal(TaskModal(interaction.user.id, task_name))

async def setup(bot):
    await bot.add_cog(TaskTodoModalCog(bot))
import os
import random
import asyncio
from datetime import timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
AI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID", "").strip()
STAFF_APPLICATION_CHANNEL_ID = os.getenv("STAFF_APPLICATION_CHANNEL_ID", "").strip()
ROLES_DEPARTMENT_CHANNEL_ID = os.getenv("ROLES_DEPARTMENT_CHANNEL_ID", "").strip()
BONUS_DEPARTMENT_CHANNEL_ID = os.getenv("BONUS_DEPARTMENT_CHANNEL_ID", "").strip()
EVENT_DEPARTMENT_CHANNEL_ID = os.getenv("EVENT_DEPARTMENT_CHANNEL_ID", "").strip()
STAFF_ADMIN_ROLE_ID = os.getenv("STAFF_ADMIN_ROLE_ID", "").strip()
STAFF_APPROVED_ROLE_ID = os.getenv("STAFF_APPROVED_ROLE_ID", "").strip()
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID", "").strip()
GOODBYE_CHANNEL_ID = os.getenv("GOODBYE_CHANNEL_ID", "").strip()
MOD_LOG_CHANNEL_ID = os.getenv("MOD_LOG_CHANNEL_ID", "").strip()
TICKET_LOG_CHANNEL_ID = os.getenv("TICKET_LOG_CHANNEL_ID", "").strip()
ROLES_DEPARTMENT_LOG_CHANNEL_ID = os.getenv("ROLES_DEPARTMENT_LOG_CHANNEL_ID", "").strip()
BONUS_DEPARTMENT_LOG_CHANNEL_ID = os.getenv("BONUS_DEPARTMENT_LOG_CHANNEL_ID", "").strip()
EVENT_DEPARTMENT_LOG_CHANNEL_ID = os.getenv("EVENT_DEPARTMENT_LOG_CHANNEL_ID", "").strip()

if not TOKEN or TOKEN == "put_your_discord_bot_token_here":
    raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class SpiderBot(commands.Bot):
    async def setup_hook(self):
        # Register persistent ticket buttons across restarts.
        self.add_view(TicketPanelView())
        self.add_view(StaffApplyPanelView())
        self.add_view(StaffReviewView())
        if TEST_GUILD_ID.isdigit():
            guild = discord.Object(id=int(TEST_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to test guild {TEST_GUILD_ID}.")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global commands.")

bot = SpiderBot(command_prefix="!", intents=intents)
bot.remove_command("help")

def is_admin(interaction: discord.Interaction) -> bool:
    return bool(interaction.guild and isinstance(interaction.user, discord.Member)
                and interaction.user.guild_permissions.administrator)

async def admin_check(interaction: discord.Interaction) -> bool:
    if not is_admin(interaction):
        raise app_commands.CheckFailure("This command is for server administrators.")
    return True

async def send_to_channel_id(guild: discord.Guild, channel_id: str, message: str):
    """Send a log only to the explicitly configured channel ID."""
    if not channel_id.isdigit():
        return
    channel = guild.get_channel(int(channel_id))
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(message)
        except discord.Forbidden:
            print(f"Missing permission to send to configured channel ID {channel_id}.")

async def send_log(guild: discord.Guild, message: str):
    await send_to_channel_id(guild, MOD_LOG_CHANNEL_ID, message)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Henry Knox"))
    print(f"Spider 🕷️ online as {bot.user} (ID: {bot.user.id})")
@bot.event
async def on_member_join(member: discord.Member):
    # Configure WELCOME_CHANNEL_ID in hosting Environment Variables.
    channel = member.guild.get_channel(int(WELCOME_CHANNEL_ID)) if WELCOME_CHANNEL_ID.isdigit() else None
    if channel:
        embed = discord.Embed(
            title="🕷️ A new member joined!",
            description=f"Welcome {member.mention} to **{member.guild.name}**!",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass
    role = discord.utils.get(member.guild.roles, name="Member")
    if role and role < member.guild.me.top_role:
        try:
            await member.add_roles(role, reason="Spider automatic member role")
        except discord.Forbidden:
            pass

@bot.event
async def on_member_remove(member: discord.Member):
    channel = member.guild.get_channel(int(GOODBYE_CHANNEL_ID)) if GOODBYE_CHANNEL_ID.isdigit() else None
    if channel:
        try:
            await channel.send(f"👋 **{discord.utils.escape_markdown(member.display_name)}** left the server.")
        except discord.Forbidden:
            pass

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    # AI chat: mention Spider or use /ask. Requires OPENAI_API_KEY.
    if bot.user and bot.user in message.mentions:
        if not AI_KEY:
            await message.reply("🕷️ AI chat isn't configured yet. Add `OPENAI_API_KEY` to `.env` and restart me.", mention_author=False)
            return
        prompt = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not prompt:
            prompt = "Introduce yourself as Spider, a helpful Discord assistant."
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=AI_KEY)
            response = await client.responses.create(
                model=AI_MODEL,
                input=[
                    {"role": "system", "content": "You are Spider, a friendly, concise assistant in a Discord server. Follow safety rules."},
                    {"role": "user", "content": prompt[:4000]},
                ],
                max_output_tokens=500,
            )
            answer = response.output_text.strip() or "I couldn't create a reply just now."
            for start in range(0, len(answer), 1900):
                await message.reply(answer[start:start+1900], mention_author=False)
        except Exception:
            await message.reply("⚠️ AI request failed. Check your API key, model name, billing, and console logs.", mention_author=False)
    await bot.process_commands(message)



# ---------------- STAFF APPLICATION SYSTEM ----------------
STAFF_QUESTIONS = [
    "What is your name?",
    "What is your game ID?",
    "What is your timezone?",
    "What is your rank?",
]
DEPARTMENTS = {
    "roles": ("Roles Department", ROLES_DEPARTMENT_CHANNEL_ID),
    "bonus": ("Bonus Department", BONUS_DEPARTMENT_CHANNEL_ID),
    "event": ("Event Department", EVENT_DEPARTMENT_CHANNEL_ID),
}

def staff_reviewer(member: discord.Member) -> bool:
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    return STAFF_ADMIN_ROLE_ID.isdigit() and any(r.id == int(STAFF_ADMIN_ROLE_ID) for r in member.roles)

class StaffApplyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Roles Department", value="roles", description="Apply to the Roles team", emoji="🎭"),
            discord.SelectOption(label="Bonus Department", value="bonus", description="Apply to the Bonus team", emoji="🎁"),
            discord.SelectOption(label="Event Department", value="event", description="Apply to the Event team", emoji="🎉"),
        ]
        select = discord.ui.Select(placeholder="Choose Your Department", min_values=1, max_values=1,
                                   options=options, custom_id="spider:staff:department")
        select.callback = self.department_selected
        self.add_item(select)

    async def department_selected(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("Please choose a department from the server panel.", ephemeral=True)
        selected = interaction.data.get("values", [""])[0]
        if selected not in DEPARTMENTS:
            return await interaction.response.send_message("That department is not valid. Please try again.", ephemeral=True)
        department, channel_id = DEPARTMENTS[selected]
        await interaction.response.send_message(f"📩 I'll DM you the **{department}** application questions. Check your DMs.", ephemeral=True)
        try:
            dm = await interaction.user.create_dm()
            await dm.send(
                f"🕷️ **{interaction.guild.name} — {department} Application**\n"
                "Answer these questions one by one. Send `!cancel` at any time to cancel. You have 5 minutes per answer."
            )
        except discord.Forbidden:
            return
        questions = STAFF_QUESTIONS + [f"Why do you want to join {department}?"]
        answers = []
        for index, question in enumerate(questions, start=1):
            await dm.send(f"**Question {index} / {len(questions)}**\n{question}")
            def check(message):
                return message.author.id == interaction.user.id and isinstance(message.channel, discord.DMChannel)
            try:
                reply = await bot.wait_for("message", check=check, timeout=300)
            except asyncio.TimeoutError:
                await dm.send("⌛ Application timed out. Choose your department again to restart.")
                return
            if reply.content.strip().lower() == "!cancel":
                await dm.send("Application cancelled.")
                return
            answer = reply.content.strip()
            if not answer:
                await dm.send("Please send a non-empty answer. Choose your department again to retry.")
                return
            answers.append(answer[:1000])

        if not channel_id.isdigit():
            await dm.send(f"⚠️ The **{department}** review channel is not configured yet. Please contact a server admin.")
            print(f"{selected.upper()}_DEPARTMENT_CHANNEL_ID is not configured.")
            return
        review_channel = bot.get_channel(int(channel_id))
        if not isinstance(review_channel, discord.TextChannel):
            await dm.send(f"⚠️ The **{department}** review channel could not be found. Please contact a server admin.")
            print(f"Configured channel for {department} was not found or is not accessible.")
            return
        embed = discord.Embed(
            title=f"📝 New Application — {department}",
            description=f"Applicant: {interaction.user.mention}\nUser ID: `{interaction.user.id}`\nDepartment: **{department}**",
            color=discord.Color.blurple()
        )
        for question, answer in zip(questions, answers):
            embed.add_field(name=question[:256], value=answer[:1024], inline=False)
        embed.set_footer(text=f"Spider Staff Application | Department: {selected} | Applicant ID: {interaction.user.id}")
        try:
            await review_channel.send(embed=embed, view=StaffReviewView())
            department_log_id = {
                "roles": ROLES_DEPARTMENT_LOG_CHANNEL_ID,
                "bonus": BONUS_DEPARTMENT_LOG_CHANNEL_ID,
                "event": EVENT_DEPARTMENT_LOG_CHANNEL_ID,
            }[selected]
            await send_to_channel_id(interaction.guild, department_log_id,
                f"📥 New **{department}** application received from {interaction.user.mention} (`{interaction.user.id}`). Review channel: {review_channel.mention}")
            await dm.send(f"✅ Your **{department}** application has been sent to its review channel. You'll receive a DM after the admin team's decision.")
        except discord.Forbidden:
            await dm.send(f"⚠️ I cannot post in the configured {department} review channel. Please contact a server admin.")

class StaffReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _review(self, interaction: discord.Interaction, approved: bool):
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not staff_reviewer(interaction.user):
            return await interaction.response.send_message("Only server admins or the configured staff-review role can decide applications.", ephemeral=True)
        message = interaction.message
        if not message or not message.embeds:
            return await interaction.response.send_message("Application details weren't found.", ephemeral=True)
        footer = message.embeds[0].footer.text or ""
        marker = "Applicant ID: "
        if marker not in footer:
            return await interaction.response.send_message("Applicant ID wasn't found in this application.", ephemeral=True)
        try:
            applicant_id = int(footer.rsplit(marker, 1)[1])
        except ValueError:
            return await interaction.response.send_message("Applicant ID is invalid.", ephemeral=True)
        decision = "approved" if approved else "rejected"
        embed = message.embeds[0]
        if embed.title and ("APPROVED" in embed.title or "REJECTED" in embed.title):
            return await interaction.response.send_message("This application already has a decision.", ephemeral=True)
        embed.title = ("✅ Application APPROVED — " if approved else "❌ Application REJECTED — ") + (embed.title or "Staff Application").replace("📝 New Application — ", "")
        embed.color = discord.Color.green() if approved else discord.Color.red()
        embed.add_field(name="Decision", value=f"{decision.title()} by {interaction.user.mention}", inline=False)
        for item in self.children:
            item.disabled = True
        await message.edit(embed=embed, view=self)
        role_note = ""
        if approved:
            if not STAFF_APPROVED_ROLE_ID.isdigit():
                role_note = " ⚠️ STAFF_APPROVED_ROLE_ID is not configured, so no role was assigned."
            else:
                role = interaction.guild.get_role(int(STAFF_APPROVED_ROLE_ID))
                member = interaction.guild.get_member(applicant_id)
                if role is None:
                    role_note = " ⚠️ The configured staff role was not found."
                elif member is None:
                    role_note = " ⚠️ The applicant is no longer a server member, so the role could not be assigned."
                elif interaction.guild.me and role >= interaction.guild.me.top_role:
                    role_note = " ⚠️ Move Spider's bot role above the configured staff role, then assign the role manually."
                else:
                    try:
                        await member.add_roles(role, reason=f"Staff application approved by {interaction.user}")
                        role_note = f" Role **{role.name}** assigned."
                    except (discord.Forbidden, discord.HTTPException):
                        role_note = " ⚠️ Role assignment failed; check Manage Roles permission and role hierarchy."
        try:
            applicant = await bot.fetch_user(applicant_id)
            dept = (message.embeds[0].title or "Staff Application").replace("📝 New Application — ", "").replace("Application APPROVED — ", "").replace("Application REJECTED — ", "")
            if approved:
                await applicant.send(f"🎉 Your **{dept}** application for **{interaction.guild.name}** has been approved!{role_note}")
            else:
                await applicant.send(f"Thank you for applying to **{dept}** in **{interaction.guild.name}**. Unfortunately, your application was not approved this time.")
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass
        await interaction.response.send_message(f"Application marked {decision}.{role_note} The applicant was DM'd if their DMs are open.", ephemeral=True)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅", custom_id="spider:staff:approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._review(interaction, True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌", custom_id="spider:staff:reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._review(interaction, False)

@bot.tree.command(name="staff_panel", description="Post the Choose Your Department staff application panel")
@app_commands.check(admin_check)
async def staff_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🕷️ Choose Your Department",
        description=("Select one department below to apply. Spider will DM you five questions, "
                     "then send your application to that department's private review channel.\n\n"
                     "🎭 Roles Department\n🎁 Bonus Department\n🎉 Event Department"),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Spider Staff Applications")
    await interaction.channel.send(embed=embed, view=StaffApplyPanelView())
    await interaction.response.send_message("Department application panel posted.", ephemeral=True)


@bot.tree.command(name="supporter_thanks", description="Post the Henry Knox supporter thank-you message")
@app_commands.describe(member="Member to thank", method="What they added to their profile: vanity link or server tag")
@app_commands.check(admin_check)
async def supporter_thanks(interaction: discord.Interaction, member: discord.Member, method: str):
    method_clean = method.strip().lower()
    if method_clean not in {"vanity link", "server tag", "tag", "vanity", "link"}:
        return await interaction.response.send_message(
            'Use method "vanity link" or "server tag".',
            ephemeral=True
        )
    embed = discord.Embed(
        description=(
            f" tysm for {member.mention} for putting our **Vanity / Tag** in your profile 🦇⚡\n"
            "Tysm for Put Our Vanity / Tag In your profile, Now you're certified member of our family 🦇"
        ),
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Supporter thank-you message posted.", ephemeral=True)

@bot.tree.command(name="help", description="Show Spider's commands and setup tips")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🕷️ Spider — Command Guide", color=discord.Color.dark_purple())
    embed.add_field(name="Moderation", value="`/ban` `/kick` `/timeout` `/untimeout` `/purge`", inline=False)
    embed.add_field(name="Server tools", value="`/ticket_panel` `/staff_panel` `/giveaway` `/end_giveaway` `/embed` `/ask`", inline=False)
    embed.add_field(name="Automatic systems", value="Configure `WELCOME_CHANNEL_ID`, `GOODBYE_CHANNEL_ID`, and `MOD_LOG_CHANNEL_ID` in hosting Environment Variables; create a role named `Member`.", inline=False)
    embed.set_footer(text="Commands require suitable Discord permissions and bot role hierarchy.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from this server")
@app_commands.check(admin_check)
@app_commands.describe(member="Member to ban", reason="Reason for the ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.user or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("I can't ban yourself or a member with an equal/higher role.", ephemeral=True)
    try:
        await member.ban(reason=f"{reason} | By {interaction.user}")
        await interaction.response.send_message(f"🔨 Banned {member.mention}. Reason: {reason}", ephemeral=True)
        await send_log(interaction.guild, f"🔨 **Ban:** {member} (`{member.id}`) — {reason} — by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I lack permission or my role is too low to ban that member.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member from this server")
@app_commands.check(admin_check)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.user or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("I can't kick yourself or a member with an equal/higher role.", ephemeral=True)
    try:
        await member.kick(reason=f"{reason} | By {interaction.user}")
        await interaction.response.send_message(f"👢 Kicked {member.mention}. Reason: {reason}", ephemeral=True)
        await send_log(interaction.guild, f"👢 **Kick:** {member} (`{member.id}`) — {reason} — by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I lack permission or my role is too low to kick that member.", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a member for up to 28 days")
@app_commands.check(admin_check)
@app_commands.describe(member="Member to timeout", minutes="Duration in minutes (1–40320)", reason="Reason")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str = "No reason provided"):
    if member == interaction.user or member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("I can't timeout yourself or a member with an equal/higher role.", ephemeral=True)
    try:
        await member.timeout(timedelta(minutes=minutes), reason=f"{reason} | By {interaction.user}")
        await interaction.response.send_message(f"⏳ Timed out {member.mention} for {minutes} minutes. Reason: {reason}", ephemeral=True)
        await send_log(interaction.guild, f"⏳ **Timeout:** {member} (`{member.id}`) for {minutes}m — {reason} — by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I lack permission or my role is too low to timeout that member.", ephemeral=True)

@bot.tree.command(name="untimeout", description="Remove a member's timeout")
@app_commands.check(admin_check)
async def untimeout(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.top_role >= interaction.user.top_role and member != interaction.user:
        return await interaction.response.send_message("That member has an equal/higher role than you.", ephemeral=True)
    try:
        await member.timeout(None, reason=f"{reason} | By {interaction.user}")
        await interaction.response.send_message(f"✅ Timeout removed for {member.mention}.", ephemeral=True)
        await send_log(interaction.guild, f"✅ **Untimeout:** {member} — {reason} — by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("I lack permission or my role is too low.", ephemeral=True)

@bot.tree.command(name="purge", description="Delete recent messages in this channel")
@app_commands.check(admin_check)
@app_commands.describe(amount="Number of messages to delete (1–100)")
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("Use this in a text channel.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("I need Manage Messages permission.", ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="spider:ticket:create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("Use this button in a server.", ephemeral=True)
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.id}")
        if existing:
            return await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True)
        staff = discord.utils.get(guild.roles, name="Support")
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.id}", overwrites=overwrites,
                topic=f"Spider ticket opened by {interaction.user} ({interaction.user.id})"
            )
            await channel.send(
                f"{interaction.user.mention} welcome! Describe your issue here.",
                view=TicketCloseView()
            )
            await send_to_channel_id(guild, TICKET_LOG_CHANNEL_ID,
                f"🎫 Ticket opened: {channel.mention} by {interaction.user.mention} (`{interaction.user.id}`).")
            await interaction.response.send_message(f"🎫 Your ticket is ready: {channel.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I need Manage Channels and channel permissions to create tickets.", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=86400)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("ticket-"):
            return await interaction.response.send_message("This isn't a Spider ticket channel.", ephemeral=True)
        allowed = channel.permissions_for(interaction.user).manage_channels
        opener_id = int(channel.name.removeprefix("ticket-")) if channel.name.removeprefix("ticket-").isdigit() else None
        if not allowed and interaction.user.id != opener_id:
            return await interaction.response.send_message("Only the ticket opener or staff can close this ticket.", ephemeral=True)
        await interaction.response.send_message("🔒 Closing this ticket in a moment.")
        await send_to_channel_id(channel.guild, TICKET_LOG_CHANNEL_ID,
            f"🔒 Ticket closing: {channel.name} (channel ID `{channel.id}`), closed by {interaction.user.mention} (`{interaction.user.id}`).")
        await asyncio.sleep(3)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.Forbidden:
            if not interaction.response.is_done():
                await interaction.followup.send("I can't close this ticket because I lack Manage Channels permission. Please contact an admin.", ephemeral=True)
            else:
                try:
                    await interaction.followup.send("I can't close this ticket because I lack Manage Channels permission. Please contact an admin.", ephemeral=True)
                except discord.HTTPException:
                    pass
        except discord.HTTPException as exc:
            try:
                await interaction.followup.send(f"Ticket could not be closed (Discord error {exc.code}). Please contact an admin.", ephemeral=True)
            except discord.HTTPException:
                pass

@bot.tree.command(name="ticket_panel", description="Post the support ticket panel")
@app_commands.check(admin_check)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Spider Support",
        description="Click **Create Ticket** to open a private support channel. Please don't spam tickets.",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("Ticket panel posted.", ephemeral=True)

@bot.tree.command(name="giveaway", description="Start a simple giveaway")
@app_commands.check(admin_check)
@app_commands.describe(prize="Giveaway prize", minutes="How long it should run (1–10080)")
async def giveaway(interaction: discord.Interaction, prize: str, minutes: app_commands.Range[int, 1, 10080]):
    end_time = discord.utils.utcnow() + timedelta(minutes=minutes)
    embed = discord.Embed(title="🎉 GIVEAWAY", description=f"**Prize:** {prize}\nClick 🎉 to enter!\nEnds: <t:{int(end_time.timestamp())}:R>", color=discord.Color.gold())
    view = GiveawayView()
    await interaction.response.send_message("Giveaway created.", ephemeral=True)
    message = await interaction.channel.send(embed=embed, view=view)
    view.message = message
    view.prize = prize
    view.end_time = end_time
    bot.loop.create_task(view.finish_after(minutes * 60))

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entries = set()
        self.message = None
        self.prize = "the prize"
        self.end_time = None

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.success, emoji="🎉")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entries:
            return await interaction.response.send_message("You're already entered!", ephemeral=True)
        self.entries.add(interaction.user.id)
        await interaction.response.send_message("🎉 You're entered into the giveaway!", ephemeral=True)

    async def finish_after(self, seconds: int):
        await asyncio.sleep(seconds)
        if not self.message:
            return
        try:
            if self.entries:
                winner_id = random.choice(list(self.entries))
                await self.message.channel.send(f"🎉 Congratulations <@{winner_id}>! You won **{self.prize}**.")
                embed = self.message.embeds[0]
                embed.title = "🎉 GIVEAWAY ENDED"
                await self.message.edit(embed=embed, view=None)
            else:
                await self.message.channel.send(f"Giveaway for **{self.prize}** ended with no entries.")
                await self.message.edit(view=None)
        except (discord.NotFound, discord.Forbidden):
            pass

@bot.tree.command(name="end_giveaway", description="End a giveaway early by message ID")
@app_commands.check(admin_check)
async def end_giveaway(interaction: discord.Interaction, message_id: str):
    await interaction.response.send_message(
        "Early ending by ID isn't enabled in this starter build; wait for the timer to finish.",
        ephemeral=True
    )

@bot.tree.command(name="embed", description="Send a custom embed in this channel")
@app_commands.check(admin_check)
@app_commands.describe(title="Embed title", description="Embed description", color="Hex color such as #7B2CBF")
async def embed_command(interaction: discord.Interaction, title: str, description: str, color: str = "#7B2CBF"):
    raw = color.lstrip("#")
    try:
        if len(raw) != 6:
            raise ValueError
        embed_color = discord.Color(int(raw, 16))
    except ValueError:
        return await interaction.response.send_message("Color must be a six-digit hex code, e.g. `#7B2CBF`.", ephemeral=True)
    em = discord.Embed(title=title[:256], description=description[:4000], color=embed_color)
    em.set_footer(text="Spider 🕷️")
    await interaction.channel.send(embed=em)
    await interaction.response.send_message("Embed sent.", ephemeral=True)

@bot.tree.command(name="ask", description="Ask Spider AI a question")
@app_commands.describe(question="What do you want to ask Spider?")
async def ask(interaction: discord.Interaction, question: str):
    if not AI_KEY:
        return await interaction.response.send_message("AI isn't configured. Add `OPENAI_API_KEY` to `.env` and restart the bot.", ephemeral=True)
    await interaction.response.defer(thinking=True)
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=AI_KEY)
        response = await client.responses.create(
            model=AI_MODEL,
            input=[
                {"role": "system", "content": "You are Spider, a friendly, concise assistant in a Discord server. Follow safety rules."},
                {"role": "user", "content": question[:4000]},
            ],
            max_output_tokens=700,
        )
        answer = response.output_text.strip() or "I couldn't create a reply just now."
        await interaction.followup.send(answer[:1900])
    except Exception:
        await interaction.followup.send("⚠️ AI request failed. Check API key, model, API billing, and console logs.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) or "You don't have permission to use this command."
    elif isinstance(error, app_commands.MissingPermissions):
        message = "You don't have the required Discord permissions."
    else:
        print(f"Command error: {error!r}")
        message = "Something went wrong. Check the bot console for details."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass

bot.run(TOKEN)

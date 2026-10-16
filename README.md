# Spider 🕷️ Discord Bot

Python / discord.py starter project with:
- Ban, kick, timeout, untimeout, purge
- Welcome and goodbye messages
- Automatic `Member` role
- Private support ticket panel and close button
- Giveaway entry button and timed winner selection
- Custom embed messages
- Optional AI chat via OpenAI API

## 1. Create your Discord application
1. Open https://discord.com/developers/applications and click **New Application**.
2. Name it **Spider**.
3. Open **Bot** and add/reset the bot token. Keep it secret.
4. Under **Bot > Privileged Gateway Intents**, enable **Server Members Intent** and **Message Content Intent**.
5. Open **OAuth2 > URL Generator**. Select scopes `bot` and `applications.commands`.
6. Select permissions needed: View Channels, Send Messages, Embed Links, Read Message History, Manage Messages, Manage Channels, Ban Members, Kick Members, Moderate Members, Manage Roles. Invite it to your server.
7. In your server's role settings, move the Spider bot role above the `Member` role and any roles it needs to moderate. Discord role hierarchy still applies.

## 2. Install Python dependencies
Use Python 3.10 or newer. In this folder, run:

### Windows
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `DISCORD_TOKEN` to your bot token. Never share this file or commit it to GitHub.

## 3. Optional AI chat
Set `OPENAI_API_KEY` in `.env` and optionally `OPENAI_MODEL` to a model available to your API account. API access/billing may be separate from a ChatGPT subscription. If blank, non-AI features still work.

## 4. Run Spider
```bash
python bot.py
```
Keep the terminal/process running. For always-on hosting, use a trusted VPS or Python hosting service and store secrets in environment variables.

## 5. First-time server setup
- Choose your own welcome and goodbye channels, then set `WELCOME_CHANNEL_ID` and `GOODBYE_CHANNEL_ID` in hosting Environment Variables.
- Set `MOD_LOG_CHANNEL_ID` for moderation logs and `TICKET_LOG_CHANNEL_ID` for ticket open/close logs.
- Set `ROLES_DEPARTMENT_LOG_CHANNEL_ID`, `BONUS_DEPARTMENT_LOG_CHANNEL_ID`, and `EVENT_DEPARTMENT_LOG_CHANNEL_ID` for separate audit logs per department. These are separate from each department’s application review channel.
- Create a role named `Member` for auto-role.
- Optionally create a role named `Support`; it will be able to view tickets.
- Run `/ticket_panel` in the channel where you want the ticket panel.
- Use `/help` to see slash commands.

## Commands
- `/ban member reason`
- `/kick member reason`
- `/timeout member minutes reason`
- `/untimeout member reason`
- `/purge amount`
- `/ticket_panel`
- `/staff_panel` — posts a Staff Application panel; applicants answer 5 questions in DM and admins approve/reject in a private review channel.
- `/giveaway prize minutes`
- `/end_giveaway message_id` (currently a placeholder; see limitations below)
- `/embed title description color`
- `/ask question`
- `/help`

## Important starter-build notes
- Admin-only commands check the Discord Administrator permission. Discord bot permissions and role hierarchy must also permit the action.
- Giveaway entries and timers are in memory only. A bot restart will lose active giveaway state. Do not rely on this starter giveaway system for high-stakes prizes.
- `/end_giveaway` is a placeholder in this starter build; early ending is not implemented yet.
- Ticket transcripts, ticket persistence, configurable channel IDs, anti-raid, and a web dashboard are not included yet.
- For production use, add persistent storage, rate limits, structured logging, automated tests, and proper operational monitoring.

## Staff application system setup
1. Create a private text channel named `#staff-applications`.
2. Give the bot permission to view/send messages and embed links there.
3. Enable Developer Mode in Discord, right-click the channel, and copy its ID.
4. Add `STAFF_APPLICATION_CHANNEL_ID` to your `.env` locally or your cloud host's environment variables.
5. Optional: add `STAFF_ADMIN_ROLE_ID` with the numeric ID of the staff-review role. Server Administrators and members with Manage Server can review too.
6. Run `/staff_panel` in the channel where you want members to apply.
7. Applicants must allow DMs from server members. Answers are sent to the private review channel. Admins click Approve or Reject; Spider then DMs the applicant.

Privacy note: keep `#staff-applications` private and grant access only to the people who should read applications. This starter does not automatically assign a staff role on approval; an admin should assign the role manually.

## Automatic staff role on approval
1. Enable Discord Developer Mode.
2. Copy the ID of the staff role you want to assign.
3. Add `STAFF_APPROVED_ROLE_ID` to Render Environment Variables with that role ID.
4. Ensure Spider has **Manage Roles** permission and move Spider's bot role above that staff role.
5. Redeploy. When an authorized reviewer clicks Approve, Spider attempts to assign the role and reports any permission/configuration problem.

## Bio links and Discord Server Tags
The standard Discord bot API does not provide a reliable event/API to read members' personal bios or detect profile Server Tag changes. Spider therefore cannot reliably auto-notify when someone adds your invite link to their bio or equips a Server Tag. Do not use self-bots or scrape private profile data. A supported alternative is a `/supporter` or `/tag-proof` command/button where members voluntarily submit a link or screenshot in a configured channel; a staff reviewer can verify it.


## Presence and supporter thank-you
- Spider sets its Discord activity to **Listening to Henry Knox**.
- `/supporter_thanks member:<member> method:<vanity link|server tag>` posts the requested thank-you message. This is a manual/admin verification command; the official Discord bot API does not reliably expose personal bio edits or Server Tag equip events, so Spider cannot automatically detect those profile changes.


## Render deployment (Python Discord bot)
1. Push this folder to a GitHub repository. Keep `.env` out of Git; commit `.env.example` only.
2. In Render, create a **Background Worker** connected to the repository (a Discord Gateway bot is a continuously running process, not an HTTP website).
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Add environment variables in Render: `DISCORD_TOKEN` (required), `STAFF_APPLICATION_CHANNEL_ID` (for applications), and optionally `STAFF_ADMIN_ROLE_ID`, `STAFF_APPROVED_ROLE_ID`, `TEST_GUILD_ID`, `WELCOME_CHANNEL_ID`, `GOODBYE_CHANNEL_ID`, `MOD_LOG_CHANNEL_ID`, `TICKET_LOG_CHANNEL_ID`, `ROLES_DEPARTMENT_CHANNEL_ID`, `BONUS_DEPARTMENT_CHANNEL_ID`, `EVENT_DEPARTMENT_CHANNEL_ID`, `ROLES_DEPARTMENT_LOG_CHANNEL_ID`, `BONUS_DEPARTMENT_LOG_CHANNEL_ID`, `EVENT_DEPARTMENT_LOG_CHANNEL_ID`, `OPENAI_API_KEY`, and `OPENAI_MODEL`.
6. Deploy and inspect Logs. A successful start prints `Spider 🕷️ online as ...`.

Render service availability and pricing depend on the current plan. Confirm that the selected worker plan supports continuous operation before relying on it for 24/7 uptime.


## Department staff applications
Use `/staff_panel` to post a **Choose Your Department** dropdown. Applicants select Roles, Bonus, or Event Department and answer five questions by DM. Configure these environment variables with the IDs of the three private review text channels:

- `ROLES_DEPARTMENT_CHANNEL_ID`
- `BONUS_DEPARTMENT_CHANNEL_ID`
- `EVENT_DEPARTMENT_CHANNEL_ID`

The bot needs View Channel and Send Messages in each review channel. Keep `STAFF_ADMIN_ROLE_ID` configured for who can approve/reject applications, and `STAFF_APPROVED_ROLE_ID` for the role assigned on approval. Welcome and goodbye messages use the channel IDs you set in `WELCOME_CHANNEL_ID` and `GOODBYE_CHANNEL_ID`; no channel name is hard-coded.

After updating `bot.py` on your host, restart the bot and run `/staff_panel` again to post the new dropdown panel.

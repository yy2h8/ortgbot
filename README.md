# Context-Aware Telegram Group Conversation Bot

Stores group history, analyzes short-term trends and longer-term group context, and generates in-character replies and follow-ups. Powered by OpenRouter API.

### Project goals
- Context aware AI bot for igniting group chat conversations
- Hexagonal (ports and adapters) architecture
- Privacy minded
- Low operating cost
- Async throughout
- Designed to be run on [Pi Zero 2W](https://github.com/yy2h8/pizero2w-buildroot) via long-polling
- Minimum third party dependencies

### Features
- Replies generated via OpenRouter API provided with group context.
- Generates replies when someone replies to the bot, mentions the bot, or says the configured trigger word.
- Bot can randomly reply to any message based on configured probability.
- After a bot reply there is a chance for a follow-up message.
- By default bot embodies a generic persona. Can be customized per group with a command.
- Exposes per-group settings for trigger word, language, and persona.
- Periodically summarizes current conversation trends.
- Periodically rolls trends into a longer-lived group context profile.
- Tracks OpenRouter request usage and cost estimates.
- Abuse prevention with sliding window rate limiting.

### How it works
* Once the bot is added to a telegram group chat it starts listening to all messages (only text). Messages are sanitized first and then stored in SQLite.
* Periodic trends analysis is used for summarizing messages into a text paragraph capturing current trends. `MESSAGE_LIMIT` setting determines the number of messages required for this. After a successful analysis all group messages are deleted from the database.
* Periodic context analysis uses accumulated trends to generate group's profile and vibes as a single paragraph. `MAX_TRENDS_FOR_CONTEXT` setting controls the number of trends required for analysis. After a successful analysis all group trends and previous context are deleted from the database.
* When generating an AI reply the message triggering the reply is provided in the prompt (along with the chain of replies if available). The context and latest trend (if available) are appended to the prompt as well.

### Privacy concerns

The application is using OpenRouter API for both generating replies and analyzing conversations.

It is undesirable to send users' personal information to third party services, especially since some OpenRouter providers may use request data to train their models.

Therefore all incoming messages are sanitized (before storing):
1. Emails replaced with `[EMAIL]`
2. Phone numbers (7–15 digits) replaced with `[PHONE]`
3. URLs replaced with `[URL]`
4. Bot mentions (e.g. @mybot) removed entirely
5. User mentions (e.g. @username) replaced with `[MENTION]`

When generating a reply or analyzing a conversation all users are anonymized:
```
user_1 (14:02): hello everyone
user_2 (14:03): hey what's up
you: not much!
user_1 (14:04): nice
```
No real names, usernames, or Telegram IDs ever reach the AI.

#### Known limitations
* Names mentioned in message text - "Hey John, call me!" would still reach the AI as-is
* Implicit identifiers - things like "I live on Baker Street" or "my employee ID is 4821" wouldn't be caught
* Even if sanitized, messages and their senders are stored in the deployed database. The `MESSAGE_LIMIT` setting is aimed to minimize stored data.

---

## Bot Commands

| Command | Admin Only | Notes |
| --- | --- | --- |
| `/settrigger <word>` | Yes | Stores the trigger word. |
| `/trigger` | No | Shows the current trigger word. |
| `/setlanguage <language>` | Yes | Stores a free-form language label used in prompts. |
| `/language` | No | Shows the current language. |
| `/setpersona [text]` | Yes | Sets or clears persona. Max length: `400`. Empty text clears the persona. |
| `/persona` | No | Shows the current persona. |
| `/health` | Yes | Returns uptime, CPU, temperature, and RAM usage. |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Telegram bot token from `@BotFather`
- OpenRouter API key

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.ini.example config.ini
```

Fill in at least:

```ini
[telegram]
bot_token = YOUR_BOT_TOKEN_HERE

[openrouter]
api_key = YOUR_OPENROUTER_API_KEY_HERE
free_model = nvidia/nemotron-3-super-120b-a12b:free
paid_model = mistralai/mistral-nemo
```

At least one of `free_model` or `paid_model` must be configured.

### Run

```bash
python -m src.poller
```

The database schema is initialized automatically on first startup.

---

## Configuration

`config.ini.example` reflects the current settings surface.

Main sections:

- `[telegram]`: bot token.
- `[openrouter]`: API key and model IDs.
- `[database]`: SQLite path and inactive-record cleanup window.
- `[rate_limits]`: per-user, per-group, global API limits, and cleanup window.
- `[analytics]`: message batch size and max trends per context refresh.
- `[behavior]`: default language, trigger word, reply probability, follow-up probability.
- `[logging]`: level and rotating log file path.

Current defaults from code:

| Setting | Default | Notes |
| --- | --- | --- |
| `sqlite_path` | `/var/lib/ortgbot.db` | Path for storing the sqlite database file |
| `inactive_records_cleanup_days` | `30` | How old inactive records should be for cleanup |
| `rate_limits_cleanup_window_hours` | `24` | How old rate limit entries should be for cleanup |
| `per_user_replies_per_hour` | `20` | Abuse preventing per user reply limit |
| `per_group_replies_per_day` | `200` | Daily per group reply limit |
| `per_bot_replies_per_hour` | `5` | Max replies to the same bot per group per hour |
| `global_api_calls_per_day` | `1000` | Global api calls rate limit for cost control |
| `message_limit` | `30` | Number of messages required for a full trend analysis. Indirectly controls maximum number of messages stored per group. |
| `max_trends_for_context` | `5` | Number of trends required for a full context analysis |
| `bot_language` | `English` | Language selection for replies and analytics. Injected into prompts. |
| `trigger_word` | `bro` | Word that triggers a reply |
| `reply_probability` | `0.15` | Probability of a random reply to any message |
| `follow_up_probability` | `0.05` | Probability of a follow-up to a reply |
| `log_level` | `WARNING` | Python logging level|
| `log_file` | `/var/log/ortgbot.log` | Path for storing timed rotating logs |

---

## Implementation notes

### Application lifecycle

`src/poller.py` starts the whole application in one process:

1. Loads settings from `config.ini` or `/etc/ortgbot/config.ini`.
2. Starts queued file logging.
3. Builds the Dishka container and initializes the SQLite schema.
4. Starts the PTB polling application.
5. Starts APScheduler jobs.
6. Waits forever until interrupted, then shuts everything down.

### Architecture

Dependencies flow inward:

```text
infrastructure -> application -> domain
```

- `src/domain/`: entities, DTOs, constants, and pure functions.
- `src/application/`: ports, orchestration services, and use cases.
- `src/infrastructure/`: SQLite repositories, Telegram/OpenRouter adapters, lifecycle wiring.

Detailed project and module documentation lives in:

- `AGENTS.md`: architectural rules and development guidance.

### Periodic jobs

Configured in `src/infrastructure/adapters/incoming/apscheduler_handlers.py`:

| Job | Schedule | Purpose |
| --- | --- | --- |
| Trends analysis | Every 15 minutes | Analyze non-generated messages into `ai_group_trends`. |
| Context analysis | Every 30 minutes | Analyze trends into `ai_group_contexts`. |
| Rate limiter cleanup | Every 30 minutes | Delete expired rate-limit rows. |
| Database cleanup | Daily at 03:00 UTC | Delete inactive groups, left members, and orphaned records. |

### Storage

SQLite schema lives in `src/infrastructure/core/schema_sqlite.sql`.

Main tables:

- `telegram_groups`
- `telegram_group_members`
- `telegram_messages`
- `ai_group_trends`
- `ai_group_contexts`
- `openrouter_requests`
- `rate_limit_entries`

---

## Rationale

This application is intended to be deployed on a buildroot linux environment for Raspberry Pi Zero 2W.

The Pi Zero 2W features an `armv7l` architecture processor. Buildroot is configured to utilize the `musl` libc. There are not so many pip packages supporting this combination, so it was chosen to only depend on pure Python wheels.

- SQLite is a natural fit for embedded deployment (no extra process for database server)
- Long-polling over webhook was chosen due to dynamic IP
- Ports and adapters architecture allows for changing infrastructure easily

> `S99ortgbot` contains a simple init.d-style launcher script for the intended deployment. It starts `python3 -m src.poller` from `/root/ortgbot` and tracks a PID file in `/var/run/ortgbot.pid`.

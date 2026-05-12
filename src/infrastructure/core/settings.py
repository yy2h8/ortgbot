import configparser
from pathlib import Path
from typing import NamedTuple


# Default config locations (in priority order)
CONFIG_PATHS = [
    Path("config.ini"),  # Current directory
    Path("/etc/ortgbot/config.ini"),
]


class Settings(NamedTuple):
    telegram_bot_token: str
    openrouter_api_key: str
    free_model_id: str | None
    paid_model_id: str | None
    sqlite_db_path: str
    inactive_records_cleanup_days: int
    rate_limits_cleanup_window_hours: int
    per_user_replies_per_hour: int
    per_group_replies_per_day: int
    global_api_calls_per_day: int
    message_limit: int
    max_trends_for_context: int
    bot_language: str
    follow_up_probability: float
    reply_probability: float
    trigger_word: str
    log_level: str
    log_file: str


def _find_config_file() -> Path:
    for path in CONFIG_PATHS:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"No config file found. Searched: {[str(p) for p in CONFIG_PATHS]}\n"
        f"Create config.ini in the current directory (see config.ini.example for template)"
    )


def _validate_required(
    config: configparser.ConfigParser, section: str, key: str
) -> str:
    value = config.get(section, key, fallback="")
    if not value or not value.strip():
        raise ValueError(
            f"Required configuration missing: [{section}] {key}\n"
            f"Please set this value in your config.ini file"
        )

    return value.strip()


def load_settings(config_path: Path | None = None) -> Settings:
    path = config_path or _find_config_file()

    config = configparser.ConfigParser()
    config.read(path)

    free_model = config.get("openrouter", "free_model", fallback=None)
    paid_model = config.get("openrouter", "paid_model", fallback=None)
    if not free_model and not paid_model:
        raise ValueError(
            "At least one model must be configured in [openrouter] section: "
            "free_model and/or paid_model"
        )

    settings = Settings(
        telegram_bot_token=_validate_required(config, "telegram", "bot_token"),
        openrouter_api_key=_validate_required(config, "openrouter", "api_key"),
        free_model_id=free_model.strip() if free_model else None,
        paid_model_id=paid_model.strip() if paid_model else None,
        sqlite_db_path=config.get(
            "database", "sqlite_path", fallback="/var/lib/ortgbot.db"
        ),
        inactive_records_cleanup_days=config.getint(
            "database", "inactive_records_cleanup_days", fallback=30
        ),
        rate_limits_cleanup_window_hours=config.getint(
            "rate_limits", "rate_limits_cleanup_window_hours", fallback=24
        ),
        per_user_replies_per_hour=config.getint(
            "rate_limits", "per_user_replies_per_hour", fallback=20
        ),
        per_group_replies_per_day=config.getint(
            "rate_limits", "per_group_replies_per_day", fallback=200
        ),
        global_api_calls_per_day=config.getint(
            "rate_limits", "global_api_calls_per_day", fallback=1000
        ),
        message_limit=config.getint("analytics", "message_limit", fallback=30),
        max_trends_for_context=config.getint(
            "analytics", "max_trends_for_context", fallback=5
        ),
        follow_up_probability=config.getfloat(
            "behavior", "follow_up_probability", fallback=0.05
        ),
        reply_probability=config.getfloat(
            "behavior", "reply_probability", fallback=0.15
        ),
        bot_language=config.get("behavior", "bot_language", fallback="English"),
        trigger_word=config.get("behavior", "trigger_word", fallback="bro"),
        log_level=config.get("logging", "level", fallback="WARNING"),
        log_file=config.get("logging", "log_file", fallback="/var/log/ortgbot.log"),
    )

    return settings

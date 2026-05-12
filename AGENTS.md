# Architectural Guide for AI Development

This file provides LLM assistants with comprehensive guidance for working on this codebase. It consolidates architectural principles, design patterns, and development workflows into a single authoritative source.

---

## What: Project Overview

**Context-aware Telegram bot** implementing hexahonal architecture patterns for maintainability, testability, and domain clarity. The bot analyzes group conversations, detects trends, and generates contextual AI responses (powered by OpenRouter). Optimized for **embedded deployment on Raspberry Pi Zero 2W** (Busybox only buildroot with python, 512MB RAM).

### Architectural Foundation

The codebase deliberately follows established software engineering principles rather than framework-specific conventions.

**Core Architectural Patterns:**

- **Clean Architecture**: Dependency inversion and layered architecture (Martin)
- **SOLID Principles**: Single responsibility, dependency inversion, interface segregation (Martin)
- **Enterprise Application Patterns**: Repository, Service Layer, Domain Services (Fowler)
- **Hexagonal Architecture (Ports & Adapters)**: Incoming/outgoing adapter split (Cockburn)

### Technology Stack

Deliberately minimal third-party dependency.

- **Python 3.12+** - Modern async/await throughout
- **python-telegram-bot (PTB)** - Telegram Bot API framework
- **SQLite with WAL mode** - Embedded database, no server required
- **OpenRouter API** - Multi-model AI integration (free/paid fallback)
- **APScheduler** - Lightweight periodic task scheduling
- **Aiosqlite** - Async SQLite driver
- **httpx** - Async HTTP client
- **Dishka** - Type-safe dependency injection framework

**No external infrastructure dependencies** (no Redis, no PostgreSQL, no task queue servers).

---

## Project Structure

```
src/
  poller.py                              # Application entry point (async main)

  domain/                                # Inner layer - zero external dependencies
    entities.py                          # All domain entities (NamedTuple)
    dto.py                               # Data transfer objects (NamedTuple)
    exceptions.py                        # Domain-specific exceptions
    constants/
      bot_messages.py                    # User-facing message templates
      defaults.py                        # Shared default values like limits and thresholds
      prompt_templates.py                # PromptTemplate with render() method
    services/                            # Pure functions (no I/O, no side effects)
      conversation_formatting.py
      formatting.py
      message_sanitization.py
      suitability.py

  application/                           # Middle layer - business orchestration
    ports/                               # Abstract interfaces (ABC)
      telegram_bot.py                    # TelegramBotPort
      openrouter_client.py               # OpenRouterClient
      openrouter_request_repository.py
      rate_limiter.py                    # RateLimiter
      task_queue.py                      # TaskQueue
      telegram_group_repository.py
      telegram_message_repository.py
      telegram_group_member_repository.py
      group_context_repository.py
      group_trend_repository.py
    services/                            # Orchestration services (OOP)
      ai_service.py                      # AIService - free/paid model fallback
      analytics_service.py               # AnalyticsService - trends & context analysis
      group_service.py                   # GroupService - suitability & periodic tasks
      message_generation_service.py      # MessageGenerationService - reply/follow-up
      telegram_service.py                # TelegramService - message handling orchestration
    use_cases/                           # Thin use case wrappers
      chat_message.py
      reply_to_message.py
      follow_up_message.py
      group_joined.py
      bot_left_group.py
      member_left_group.py
      periodic_trends_analysis.py
      periodic_context_analysis.py
      set_trigger_word.py
      get_trigger_word.py
      set_language.py
      get_language.py
      set_persona.py
      get_persona.py

  infrastructure/                        # Outer layer - framework & I/O
    core/
      settings.py                        # Settings NamedTuple + INI config loader
      database.py                        # AiosqliteDatabase (single connection)
      logging.py                         # QueueHandler + TimedRotatingFileHandler setup
      schema_sqlite.sql                  # SQLite schema with indexes
      dishka_providers.py                # All Dishka Provider classes
      dishka_lifecycle.py                # Container init/shutdown
      ptb_lifecycle.py                   # PTB Application init/shutdown
      apscheduler_lifecycle.py           # Scheduler init/shutdown
      ptb_util.py                        # Decorators (only_in_group_chat, only_for_group_admin)
    adapters/
      incoming/                          # Adapters receiving external events
        ptb_handlers.py                  # PTB handler functions + setup_handlers()
        apscheduler_handlers.py          # APScheduler job functions + setup_handlers()
      outgoing/                          # Adapters calling external services
        httpx_openrouter_client.py       # OpenRouter API client
        ptb_telegram_bot.py              # Telegram bot message sender
        aiosqlite_rate_limiter.py        # SQLite-backed sliding window rate limiter
        database_cleanup.py              # Periodic cleanup of inactive groups & members
        asyncio_task_queue.py            # asyncio.create_task based background queue
        health_check.py                  # System health reporting (CPU, RAM, temp, uptime)
        repositories/                    # SQLite repository implementations
          aiosqlite_telegram_group_repository.py
          aiosqlite_telegram_message_repository.py
          aiosqlite_telegram_group_member_repository.py
          aiosqlite_group_context_repository.py
          aiosqlite_group_trend_repository.py
          aiosqlite_openrouter_request_repository.py
```

---

## Why: Architecture Rationale

### Clean Architecture Principles

**Dependencies flow inward:**

```
Infrastructure → Application → Domain
    (outer)        (middle)     (inner)
```

**Critical Rule**: Never import from outer layers into inner layers. The domain layer has **zero** dependencies on application, infrastructure, or external libraries (only Python stdlib).

**Benefits:**

1. **Business logic independence**: Domain layer is framework-agnostic
2. **Testability**: Core logic can be tested without infrastructure
3. **Flexibility**: Swap implementations (SQLite vs PostgreSQL, aiogram vs python-telegram-bot)
4. **Clarity**: Clear boundaries between technical concerns and business rules
5. **Maintainability**: Changes to infrastructure don't affect domain logic

### Hexagonal Architecture (Ports & Adapters)

The infrastructure layer splits adapters into two categories:

- **Incoming adapters** (`infrastructure/adapters/incoming/`): Receive external events and translate them to use case calls. These are PTB handlers and APScheduler jobs.
- **Outgoing adapters** (`infrastructure/adapters/outgoing/`): Implement ports to call external services. These are HTTP clients, repository implementations, and service adapters.

### Layer-Specific Design Philosophy

**Domain Layer** (Pythonic, Functional):
- **NamedTuple** for all entities and DTOs
- `create()` class methods as factory methods on entities
- `_replace()` for entity mutations (NamedTuple built-in)
- Pure functions for business logic in `services/`
- Module-level compiled regex patterns for performance
- No side effects - same input always produces same output
- `PromptTemplate` with `render(**kwargs)` using `str.format_map()` substitution

**Application Layer** (OOP-centric):
- Use cases as thin classes delegating to services (can contain simple logic)
- Application services as classes for complex orchestration
- Ports using ABC with `@abstractmethod`
- Services receive configuration values via constructor (from Settings)
- `AIService` implements free/paid model fallback pattern
- `GroupService` uses `AsyncIterator[Group]` generators for suitability filtering
- `TelegramService` handles message lifecycle (create, reply, follow-up)

**Infrastructure Layer** (Pythonic with Adapters):
- Adapter classes implementing Ports
- Lifecycle modules (`*_lifecycle.py`) with init/shutdown pairs
- Single `dishka_providers.py` file with all Provider classes
- Settings loaded from INI file via `configparser`

---

### Development Workflow

**IMPORTANT: Understand existing patterns first**

Before implementing any feature:

1. **Read similar code** - Find existing patterns in the codebase
2. **Follow layer boundaries** - Respect Clean Architecture flow

**Adding New Features - Follow This Sequence:**

1. **Define Domain Entity** (if needed)
   ```python
   # src/domain/entities.py - ALL entities in this single file
   from typing import NamedTuple
   from datetime import datetime, timezone

   class NewEntity(NamedTuple):
       entity_id: int | None
       name: str
       created_at: datetime

       @classmethod
       def create(
           cls,
           name: str,
           created_at: datetime | None = None,
           entity_id: int | None = None,
       ) -> "NewEntity":
           return cls(
               entity_id=entity_id,
               name=name,
               created_at=created_at or datetime.now(timezone.utc),
           )
   ```

2. **Create Port (Interface)**
   ```python
   # src/application/ports/new_entity_repository.py
   from abc import ABC, abstractmethod
   from src.domain.entities import NewEntity

   class NewEntityRepository(ABC):
       @abstractmethod
       async def find_by_id(self, entity_id: int) -> NewEntity | None:
           """Docstring describing operation."""
           raise NotImplementedError("Method 'find_by_id' not implemented")
   ```

3. **Implement Use Case** (usually thin wrapper delegating to a service, but can contain logic if it's simple)
   ```python
   # src/application/use_cases/create_new_entity.py
   import logging
   from src.application.services.new_entity_service import NewEntityService

   class CreateNewEntityUseCase:
       def __init__(self, service: NewEntityService, logger: logging.Logger):
           self.service = service
           self.logger = logger

       async def execute(self, name: str) -> NewEntity:
           self.logger.info(f"Creating new entity: {name}")
           result = await self.service.create_entity(name)
           self.logger.info(f"Successfully created entity: {name}")
           return result
   ```

4. **Implement Infrastructure Repository**
   ```python
   # src/infrastructure/adapters/outgoing/repositories/aiosqlite_new_entity_repository.py
   from src.domain.entities import NewEntity
   from src.application.ports.new_entity_repository import NewEntityRepository
   from src.infrastructure.core.database import AiosqliteDatabase

   class AiosqliteNewEntityRepository(NewEntityRepository):
       def __init__(self, db: AiosqliteDatabase, logger: logging.Logger):
           self._db = db
           self.logger = logger

       async def find_by_id(self, entity_id: int) -> NewEntity | None:
           async with self._db.get_connection() as conn:
               cursor = await conn.execute(
                   "SELECT entity_id, name, created_at FROM entities WHERE entity_id = ?",
                   (entity_id,),
               )
               row = await cursor.fetchone()
               return NewEntity.create(
                   entity_id=row["entity_id"],
                   name=row["name"],
                   created_at=datetime.fromtimestamp(row["created_at"], tz=timezone.utc),
               ) if row else None
   ```

5. **Wire in Dishka Provider**
   ```python
   # src/infrastructure/core/dishka_providers.py
   # Add to the appropriate Provider class:

   # In RepositoryProvider:
   @provide
   def get_new_entity_repository(
       self, db: AiosqliteDatabase
   ) -> NewEntityRepository:
       return AiosqliteNewEntityRepository(
           db=db,
           logger=_get_logger("new_entity_repo"),
       )

   # In UseCaseProvider:
   @provide
   def get_create_new_entity_use_case(
       self, service: NewEntityService
   ) -> CreateNewEntityUseCase:
       return CreateNewEntityUseCase(
           service=service,
           logger=_get_logger("create_new_entity_use_case"),
       )
   ```

6. **Add Incoming Adapter** (if needed)
   ```python
   # src/infrastructure/adapters/incoming/ptb_handlers.py
   # Add handler function, then register in setup_handlers()

   async def handle_new_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
       container = context.bot_data["container"]
       use_case: CreateNewEntityUseCase = await container.get(CreateNewEntityUseCase)
       result = await use_case.execute(name="...")
       await update.message.reply_text(f"Created: {result.name}")
   ```

---

## Key Domain Concepts

### Entities (`src/domain/entities.py`)

All entities use `NamedTuple` with a `create()` factory classmethod. The optional `*_id` field (e.g., `telegram_group_id`, `ai_group_context_id`) is `None` for new entities and populated after persistence.

| Entity | Primary Key | Purpose |
|--------|------------|---------|
| `Group` | `telegram_group_id` | Telegram group with language, trigger_word, persona, is_active |
| `GroupMember` | `telegram_group_member_id` | Group member with activity tracking |
| `Message` | `telegram_message_id` | Chat message (human or bot-generated) |
| `GroupContext` | `ai_group_context_id` | AI-generated group context summary |
| `GroupTrend` | `ai_group_trend_id` | AI-generated conversation trend analysis |
| `Request` | `openrouter_request_id` | OpenRouter API call tracking with cost |

### DTOs (`src/domain/dto.py`)

| DTO | Purpose |
|-----|---------|
| `TelegramMessage` | Incoming message data from Telegram (NamedTuple) |
| `OpenRouterResponse` | AI API response with usage stats (NamedTuple) |
| `Prompt` | Rendered prompt pair with `system` and `user` fields |

### Exceptions (`src/domain/exceptions.py`)

| Exception | Purpose |
|-----------|---------|
| `OpenRouterRateLimitError` | OpenRouter API 429 rate limit |
| `InternalRateLimitError` | Internal sliding window rate limit exceeded |

### Domain Constants (`src/domain/constants/`)

- `bot_messages.py`: User-facing message strings with `{placeholder}` formatting via `str.format_map()`
- `prompt_templates.py`: `PromptTemplate` NamedTuple with `render(**kwargs)`, uses `{var}` placeholder syntax via `str.format_map()`

### Domain Services (`src/domain/services/`)

- `suitability.py`: Pure functions evaluating group readiness for analysis
  - `evaluate_trends_suitability()` - enough messages for trend analysis (initial threshold: `INITIAL_TRENDS_THRESHOLD = 10`)
  - `evaluate_context_suitability()` - enough trends for context analysis
  - `evaluate_reply_suitability()` - message triggers bot reply (reply, mention, or trigger word)
- `message_sanitization.py`: `sanitize_for_ai_prompt()` - normalizes text, replaces PII (email/phone/URL), removes bot mentions and trigger words
- `conversation_formatting.py`: `format_conversation_for_prompt()` - formats message list into anonymized conversation with `[msg_N] user_N: content` format
- `formatting.py`: `truncate_for_prompt()` (max 300 chars), `strip_paired_quotes()`, `format_trends_for_prompt()`

---

## Key Application Patterns

### Free/Paid Model Fallback

`AIService.request_with_paid_fallback()` tries the free model first, falls back to paid on `OpenRouterRateLimitError`. Non-rate-limit errors on the free model do **not** trigger fallback. All requests are tracked in the `openrouter_requests` table with cost estimates. Model IDs are plain strings configured in `config.ini`.

### Suitability Evaluation Pattern

`suitability.py` contains pure functions that evaluate whether a group is ready for analysis:
- `evaluate_trends_suitability()` - enough messages for trend analysis
- `evaluate_context_suitability()` - enough trends for context analysis
- `evaluate_reply_suitability()` - message triggers bot reply (reply, mention, or trigger word)

### Periodic Analysis Pipeline

1. **Trends Analysis** (every 15 min): Collect non-generated messages -> analyze via AI -> store `GroupTrend` -> cleanup messages
2. **Context Analysis** (every 30 min): Collect all trends -> analyze via AI -> store `GroupContext` -> cleanup old trends
3. **Rate Limiter Cleanup** (every 30 min): Delete expired rate limit entries older than configurable window (`rate_limits_cleanup_window_hours`)
4. **Database Cleanup** (daily at 3 AM UTC): Delete inactive groups and left members older than configurable threshold (`inactive_records_cleanup_days`), plus orphaned records with NULL foreign keys. `openrouter_requests` are preserved for analytics.

### Infrastructure-Only Periodic Tasks

Some periodic tasks are purely infrastructure concerns and **do not** go through the application layer (no ports, no use cases, no services). These adapters are resolved directly from the Dishka container in the APScheduler handler:

- **`AiosqliteRateLimiter.cleanup_expired_entries()`**: Deletes stale rate limit entries
- **`DatabaseCleanup.cleanup()`**: Deletes inactive groups, left members, and orphaned records

This pattern is appropriate for tasks that are database maintenance concerns with no business logic.

### Background Task Queue

`AsyncioTaskQueue` uses `asyncio.create_task()` for fire-and-forget background work. Tasks resolve use cases lazily from the Dishka container at execution time via late imports to avoid circular dependencies.

### PTB Handler Decorators

- `@only_in_group_chat`: Filters to group/supergroup messages only
- `@only_for_group_admin`: Checks user is admin before allowing command execution

### Settings Pattern

`Settings` is a `NamedTuple` (18 fields) loaded from `config.ini` via `configparser`. Configuration values are passed to services via constructor injection, not accessed globally.

Key configurable settings and defaults:

| Setting | Default | Purpose |
|---------|---------|---------|
| `inactive_records_cleanup_days` | `30` | Age threshold for database cleanup |
| `rate_limits_cleanup_window_hours` | `24` | Window for rate limiter entry expiration |
| `global_api_calls_per_day` | `1000` | Daily API call budget |
| `per_user_replies_per_hour` | `20` | Per-user hourly reply limit |
| `per_group_replies_per_day` | `200` | Per-group daily reply limit |
| `message_limit` | `30` | Messages per trend analysis batch |
| `max_trends_for_context` | `5` | Trends per context analysis batch |
| `follow_up_probability` | `0.05` | Probability of random follow-up after reply |
| `reply_probability` | `0.15` | Probability of random reply to any message |
| `bot_language` | `"English"` | Default language for new groups |
| `trigger_word` | `"bro"` | Default trigger word for new groups |

### Bot Commands

| Command | Admin Only | Purpose |
|---------|-----------|---------|
| `/settrigger <word>` | Yes | Set group trigger word |
| `/trigger` | No | Show current trigger word |
| `/setlanguage <lang>` | Yes | Set group language |
| `/language` | No | Show current language |
| `/setpersona [text]` | Yes | Set/clear group persona (max 400 chars) |
| `/persona` | No | Show current persona |
| `/health` | Yes | Show system health (CPU, RAM, temp, uptime) |

---

## Architectural Rules (STRICT)

### 1. Layer Dependency Rules

**ALLOWED:**
```python
# Infrastructure imports from application + domain
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.domain.entities import Group

# Application imports from domain
from src.domain.entities import Message
from src.domain.services.message_sanitization import sanitize_for_ai_prompt

# Domain imports only from Python stdlib
import re
from typing import NamedTuple
from datetime import datetime
```

**FORBIDDEN:**
```python
# Domain importing from application or infrastructure
from src.application.ports.telegram_group_repository import ...  # NEVER
from src.infrastructure.core.database import ...  # NEVER

# Application importing from infrastructure
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_telegram_group_repository import ...  # NEVER
```

### 2. Entity Rules (NamedTuple, not dataclass)

**CORRECT:**
```python
# ALL entities are NamedTuple in entities.py
class Group(NamedTuple):
    tg_id: int
    title: str
    telegram_group_id: int | None

    @classmethod
    def create(cls, tg_id: int, title: str, ...) -> "Group":
        return cls(tg_id=tg_id, title=title, ...)

# Mutations create new instances via _replace()
updated_group = group._replace(title="New Title")
```

**INCORRECT:**
```python
@dataclass(frozen=True)  # WRONG - use NamedTuple, not dataclass
class Group:
    title: str

group.title = "New Title"  # WRONG - NamedTuple is immutable
```

### 3. Async/Await Rules

**CORRECT:**
```python
async def process_message(self, dto: TelegramMessage) -> None:
    group = await self.group_repo.find_by_tg_id(dto.chat_tg_id)
    message = await self.message_repo.create(message_entity)
```

**INCORRECT:**
```python
def process_message(self, dto: TelegramMessage) -> None:
    group = await self.group_repo.find_by_tg_id(dto.chat_tg_id)  # Mixing sync/async
```

**Rule**: Any method calling `await` must be `async`.

### 4. Repository Pattern Rules

**CORRECT:**
```python
# Port (application layer)
class TelegramGroupRepository(ABC):
    @abstractmethod
    async def find_by_tg_id(self, tg_id: int) -> Group | None:
        raise NotImplementedError("Method 'find_by_tg_id' not implemented")

# Implementation (infrastructure layer)
class AiosqliteTelegramGroupRepository(TelegramGroupRepository):
    async def find_by_tg_id(self, tg_id: int) -> Group | None:
        # SQLite-specific implementation
```

**INCORRECT:**
```python
# Direct database access from use case
class ChatMessageUseCase:
    async def execute(self, dto: TelegramMessage):
        # NEVER do this - bypasses repository pattern
        async with self.db.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM groups ...")
```

**Rule**: Never access database outside repositories.

### 5. Pure Function Rules (Domain Services)

**CORRECT:**
```python
# Module-level pure function
def sanitize_for_ai_prompt(text: str | None, trigger_word: str) -> str:
    """Pure function - no side effects, deterministic."""
    if not text:
        return ""
    sanitized = text.strip()
    # ... pure transformations
    return sanitized
```

**INCORRECT:**
```python
def sanitize_for_ai_prompt(text: str | None, trigger_word: str) -> str:
    """Impure - has side effects!"""
    self.logger.info(f"Sanitizing: {text}")  # Side effect!
    self.metrics.increment("sanitizations")  # Side effect!
    return text.strip()
```

**Rule**: Domain services must be pure functions (no I/O, no logging, no state mutation).

### 6. Dependency Injection Rules (Dishka)

**CORRECT:**
```python
# Provider registration using dishka Provider classes
class RepositoryProvider(Provider):
    scope = Scope.APP

    @provide
    def get_telegram_group_repository(
        self, db: AiosqliteDatabase
    ) -> TelegramGroupRepository:
        return AiosqliteTelegramGroupRepository(
            db=db,
            logger=_get_logger("telegram_group_repo"),
        )

# Type-safe resolution from container
use_case: ChatMessageUseCase = await container.get(ChatMessageUseCase)
```

**INCORRECT:**
```python
# Hardcoded dependency - no DI
class ChatMessageUseCase:
    def __init__(self):
        self.database = AiosqliteDatabase("/var/lib/ortgbot.db")  # Hardcoded!
        self.repo = AiosqliteTelegramGroupRepository(self.database)  # Concrete class!
```

**Rule**: All dependencies injected via Dishka Provider classes, depend on abstractions (ports). The provider file is `src/infrastructure/core/dishka_providers.py`.

### 7. Import Path Rules

**Correct import paths:**

```python
# Domain entities (flat file, not a package)
from src.domain.entities import Group, Message, GroupMember, GroupContext, GroupTrend, Request

# Domain DTOs
from src.domain.dto import TelegramMessage, OpenRouterResponse, Prompt

# Domain exceptions
from src.domain.exceptions import OpenRouterRateLimitError, InternalRateLimitError

# Domain services
from src.domain.services.message_sanitization import sanitize_for_ai_prompt
from src.domain.services.conversation_formatting import format_conversation_for_prompt
from src.domain.services.formatting import truncate_for_prompt, strip_paired_quotes, format_trends_for_prompt
from src.domain.services.suitability import evaluate_trends_suitability, evaluate_context_suitability, evaluate_reply_suitability

# Domain constants
from src.domain.constants.bot_messages import RATE_LIMITED
from src.domain.constants.prompt_templates import REPLY_TO_MESSAGE_TEMPLATE

# Application ports
from src.application.ports.telegram_bot import TelegramBotPort
from src.application.ports.openrouter_client import OpenRouterClient
from src.application.ports.rate_limiter import RateLimiter
from src.application.ports.task_queue import TaskQueue

# Infrastructure adapters
from src.infrastructure.adapters.incoming.ptb_handlers import setup_handlers
from src.infrastructure.adapters.outgoing.httpx_openrouter_client import HttpxOpenRouterClient
from src.infrastructure.adapters.outgoing.database_cleanup import DatabaseCleanup
from src.infrastructure.adapters.outgoing.repositories.aiosqlite_telegram_group_repository import AiosqliteTelegramGroupRepository

# Infrastructure core
from src.infrastructure.core.database import AiosqliteDatabase
from src.infrastructure.core.settings import Settings, load_settings
from src.infrastructure.core.dishka_lifecycle import get_container, init_container
```

---

## Best Practices

### 1. Security: Avoid Over-Engineering

Only add what's directly requested:

**DO:**
- Fix the specific bug
- Add the requested feature
- Follow existing patterns

**DON'T:**
- Add unrequested features
- Refactor surrounding code
- Add "improvements" beyond scope
- Add error handling for scenarios that can't happen
- Create abstractions for one-time operations

**Example:**
```python
# GOOD: Simple, focused fix
async def get_group(self, tg_id: int) -> Group | None:
    return await self.group_repo.find_by_tg_id(tg_id)

# BAD: Over-engineered with unnecessary abstractions
async def get_group_with_caching_and_retry(
    self,
    tg_id: int,
    cache_ttl: int = 300,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Group | None:
    # Premature optimization!
    # Added features that weren't requested!
```

### 2. Error Handling at Boundaries

Catch infrastructure errors and translate:

```python
# Repository catches database errors
class AiosqliteGroupRepository(TelegramGroupRepository):
    async def find_by_tg_id(self, tg_id: int) -> Group | None:
        try:
            async with self._db.get_connection() as conn:
                cursor = await conn.execute(...)
                row = await cursor.fetchone()
                return Group.create(...) if row else None
        except Exception as e:
            self.logger.error(f"Error finding group by tg_id {tg_id}: {e}")
            raise

# Use case assumes clean domain objects
class ChatMessageUseCase:
    async def execute(self, dto: TelegramMessage) -> None:
        group = await self.service.find_or_create_group(dto.chat_tg_id, dto.chat_title)
        # group is either Group or None - service handles the logic
```

### 3. Performance: Use Pythonic Patterns

**Module-level compiled regex:**
```python
# GOOD: Compiled once at module load
_EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

def sanitize(text: str) -> str:
    return _EMAIL_PATTERN.sub('[EMAIL]', text)

# BAD: Recompiled every function call
def sanitize(text: str) -> str:
    pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    return pattern.sub('[EMAIL]', text)
```

**Async generators for batch suitability filtering:**
```python
# GOOD: Batch-fetches data, then yields suitable items one at a time
async def find_suitable_groups_for_trends_analysis(self) -> AsyncIterator[Group]:
    groups = await self.group_repo.find_active_groups()
    # ... batch queries for all groups at once
    for group in groups:
        if evaluate_trends_suitability(...):
            yield group
```

### 4. Container Resolution Pattern

Always resolve dependencies by type, not by string key:

```python
# GOOD: Type-safe resolution
container = context.bot_data["container"]
use_case: ChatMessageUseCase = await container.get(ChatMessageUseCase)

# BAD: String-based lookup
use_case = container.get("chat_message_use_case")
```

### 5. Testing Strategy

The test suite covers domain and application layers with **257 unit tests** across 12 test files. Infrastructure adapters are not unit-tested (they require real I/O).

**Test structure:**

```
tests/
  conftest.py                          # Entity factories + port mock fixtures
  unit/
    domain/                            # Synchronous tests (pure functions)
      test_entities.py                 # entity create() factory defaults
      test_prompt_templates.py         # render(), substitution, validation
      test_message_sanitization.py     # PII replacement, trigger word removal
      test_suitability.py              # evaluate_* boundary conditions
      test_conversation_formatting.py  # anonymization, truncation, reply chains
      test_formatting.py               # trend formatting, quote stripping, truncation
    application/                       # Async tests (mocked ports)
      test_ai_service.py              # request tracking and fallback logic
      test_analytics_service.py       # analyze_trends, analyze_context, prompt routing
      test_group_service.py           # suitability filtering and cleanup behavior
      test_message_generation_service.py  # reply and follow-up prompt generation
      test_telegram_service.py        # message lifecycle, random replies, rate limiting
      test_use_cases.py               # use case delegation and command behavior
```

**Running tests:**

```bash
pytest tests/ -v                       # Full suite
pytest tests/unit/domain/ -v           # Domain only
pytest tests/unit/application/ -v      # Application only
pytest tests/unit/domain/test_message_sanitization.py -v  # Single file
```

**Testing conventions:**

- **Domain tests**: Plain `def test_*()` (synchronous) — pure functions, no mocks needed
- **Application tests**: `async def test_*()` with `@pytest.mark.asyncio` — constructor-injected mock dependencies
- **Mock only ports** (ABCs). Never mock domain services or pure functions — call them directly
- **Entity factories**: Use `make_group()`, `make_message()`, etc. from `conftest.py` — never call `Entity.create()` with raw args in tests
- **Async generator mocks**: Use `async_iter([items])` from `conftest.py` to wrap lists for `async for` iteration
- **For `random.random()` / `random.uniform()`**: Use `unittest.mock.patch` targeting the module where it's called (e.g., `"src.application.services.telegram_service.random"`)
- **For time-sensitive tests**: Construct explicit `datetime` values relative to a fixed "now" — do not mock `datetime.now()`

**Adding tests for new features:**

1. Domain: Add test file in `tests/unit/domain/`, call pure functions directly
2. Application service: Add test file in `tests/unit/application/`, instantiate service with `AsyncMock(spec=PortClass)` dependencies
3. Use cases: Add tests to `tests/unit/application/test_use_cases.py`, mock the services the use case delegates to
4. If new entity: Add `make_*()` factory to `conftest.py`
5. If new port: Add `@pytest.fixture` returning `AsyncMock(spec=NewPort)` to `conftest.py`

### 6. Late Import Pattern for Circular Dependencies

Use late imports inside functions to break circular dependency chains:

```python
# In asyncio_task_queue.py and apscheduler_handlers.py:
async def _reply_to_message_async(self, telegram_message_id: str) -> None:
    from src.infrastructure.core.dishka_lifecycle import get_container
    container = get_container()
    use_case = await container.get(ReplyToMessageUseCase)
    await use_case.execute(telegram_message_id)
```

import pytest
import logging
from unittest.mock import AsyncMock, patch

from src.application.services.group_service import GroupService
from src.application.services.analytics_service import AnalyticsService
from src.application.ports.telegram_group_repository import TelegramGroupRepository
from src.application.ports.telegram_message_repository import TelegramMessageRepository
from src.application.ports.group_context_repository import GroupContextRepository
from src.application.ports.group_trend_repository import GroupTrendRepository
from src.application.ports.telegram_bot import TelegramBotPort
from tests.conftest import make_group, make_group_trend, make_group_context


def _make_group_service(
    group_repo=None,
    message_repo=None,
    trend_repo=None,
    context_repo=None,
    analytics_service=None,
    telegram_bot=None,
    message_limit=20,
    max_trends_for_context=5,
):
    return GroupService(
        group_repo=group_repo or AsyncMock(spec=TelegramGroupRepository),
        message_repo=message_repo or AsyncMock(spec=TelegramMessageRepository),
        trend_repo=trend_repo or AsyncMock(spec=GroupTrendRepository),
        context_repo=context_repo or AsyncMock(spec=GroupContextRepository),
        analytics_service=analytics_service or AsyncMock(spec=AnalyticsService),
        telegram_bot=telegram_bot or AsyncMock(spec=TelegramBotPort),
        message_limit=message_limit,
        max_trends_for_context=max_trends_for_context,
        logger=logging.getLogger("test"),
    )


# ---------------------------------------------------------------------------
# find_suitable_groups_for_trends_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_suitability_no_active_groups():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[])

    service = _make_group_service(group_repo=group_repo)
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_trends_suitability_group_with_no_prior_trend_enough_messages():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}  # no trend for group 10

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {10: 10}  # == INITIAL_TRENDS_THRESHOLD

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == [group]


@pytest.mark.asyncio
async def test_trends_suitability_group_with_no_prior_trend_not_enough_messages():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {10: 5}  # below threshold

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_trends_suitability_group_with_complete_prior_trend_enough_messages():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    latest_trend = make_group_trend(telegram_group_id=10, analysis_message_count=20)
    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {10: latest_trend}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {10: 20}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == [group]


@pytest.mark.asyncio
async def test_trends_suitability_mixed_groups():
    group_suitable = make_group(telegram_group_id=1)
    group_not_suitable = make_group(telegram_group_id=2)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(
        return_value=[group_suitable, group_not_suitable]
    )

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}  # no prior trends

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    # group 1 has enough messages, group 2 does not
    message_repo.count_non_generated_for_groups.return_value = {1: 15, 2: 3}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == [group_suitable]


@pytest.mark.asyncio
async def test_trends_suitability_batch_queries_called_once():
    """Verifies that batch methods are called once for all groups, not once per group."""
    g1 = make_group(telegram_group_id=1)
    g2 = make_group(telegram_group_id=2)
    g3 = make_group(telegram_group_id=3)

    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[g1, g2, g3])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
    )
    [g async for g in service.find_suitable_groups_for_trends_analysis()]

    trend_repo.find_latest_for_groups.assert_called_once()
    message_repo.count_non_generated_for_groups.assert_called_once()


@pytest.mark.asyncio
async def test_trends_suitability_group_ids_passed_to_batch_methods():
    g1 = make_group(telegram_group_id=10)
    g2 = make_group(telegram_group_id=20)

    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[g1, g2])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
    )
    [g async for g in service.find_suitable_groups_for_trends_analysis()]

    called_ids = trend_repo.find_latest_for_groups.call_args[0][0]
    assert set(called_ids) == {10, 20}


@pytest.mark.asyncio
async def test_trends_suitability_group_with_incomplete_prior_trend_new_messages_available():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    incomplete_trend = make_group_trend(telegram_group_id=10, analysis_message_count=5)
    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {10: incomplete_trend}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {10: 12}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == [group]


@pytest.mark.asyncio
async def test_trends_suitability_group_with_incomplete_prior_trend_no_new_messages():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    incomplete_trend = make_group_trend(telegram_group_id=10, analysis_message_count=5)
    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {10: incomplete_trend}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {10: 5}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_trends_suitability_group_missing_from_message_counts():
    group = make_group(telegram_group_id=99)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == []


@pytest.mark.asyncio
@patch("src.application.services.group_service.evaluate_trends_suitability")
async def test_trends_suitability_continues_after_exception(mock_evaluate):
    g_err = make_group(telegram_group_id=1)
    g_ok = make_group(telegram_group_id=2)

    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[g_err, g_ok])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.find_latest_for_groups.return_value = {}

    message_repo = AsyncMock(spec=TelegramMessageRepository)
    message_repo.count_non_generated_for_groups.return_value = {1: 15, 2: 15}

    call_count = [0]

    def side_effect(msg_count, latest_trend, limit):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("test error")
        return True

    mock_evaluate.side_effect = side_effect

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    results = [g async for g in service.find_suitable_groups_for_trends_analysis()]

    assert results == [g_ok]


# ---------------------------------------------------------------------------
# find_suitable_groups_for_context_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_suitability_no_active_groups():
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[])

    service = _make_group_service(group_repo=group_repo)
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_context_suitability_group_with_no_prior_context_enough_trends():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {10: 3}  # > 1, enough for first context

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}  # no prior context

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == [group]


@pytest.mark.asyncio
async def test_context_suitability_group_not_enough_trends():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {10: 1}  # not enough (need > 1)

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_context_suitability_mixed_groups():
    group_suitable = make_group(telegram_group_id=1)
    group_not_suitable = make_group(telegram_group_id=2)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(
        return_value=[group_suitable, group_not_suitable]
    )

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {1: 5, 2: 1}  # group 2 not enough

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == [group_suitable]


@pytest.mark.asyncio
async def test_context_suitability_batch_queries_called_once():
    g1 = make_group(telegram_group_id=1)
    g2 = make_group(telegram_group_id=2)

    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[g1, g2])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {}

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    [g async for g in service.find_suitable_groups_for_context_analysis()]

    trend_repo.count_for_groups.assert_called_once()
    context_repo.find_for_groups.assert_called_once()


@pytest.mark.asyncio
async def test_context_suitability_group_ids_passed_to_batch_methods():
    g1 = make_group(telegram_group_id=10)
    g2 = make_group(telegram_group_id=20)

    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[g1, g2])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {}

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
    )
    [g async for g in service.find_suitable_groups_for_context_analysis()]

    trend_called_ids = trend_repo.count_for_groups.call_args[0][0]
    context_called_ids = context_repo.find_for_groups.call_args[0][0]
    assert set(trend_called_ids) == {10, 20}
    assert set(context_called_ids) == {10, 20}


@pytest.mark.asyncio
async def test_context_suitability_group_with_incomplete_prior_context_new_trends():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    prior_context = make_group_context(telegram_group_id=10, analysis_trends_count=2)
    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {10: prior_context}

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {10: 4}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == [group]


@pytest.mark.asyncio
async def test_context_suitability_group_with_incomplete_prior_context_no_new_trends():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    prior_context = make_group_context(telegram_group_id=10, analysis_trends_count=2)
    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {10: prior_context}

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {10: 2}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_context_suitability_group_with_complete_prior_context_enough_trends():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    prior_context = make_group_context(telegram_group_id=10, analysis_trends_count=5)
    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {10: prior_context}

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {10: 5}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == [group]


@pytest.mark.asyncio
async def test_context_suitability_group_with_complete_prior_context_not_enough_trends():
    group = make_group(telegram_group_id=10)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    prior_context = make_group_context(telegram_group_id=10, analysis_trends_count=5)
    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {10: prior_context}

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {10: 3}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == []


@pytest.mark.asyncio
async def test_context_suitability_group_missing_from_trends_counts():
    group = make_group(telegram_group_id=99)
    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[group])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {}

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == []


@pytest.mark.asyncio
@patch("src.application.services.group_service.evaluate_context_suitability")
async def test_context_suitability_continues_after_exception(mock_evaluate):
    g_ok = make_group(telegram_group_id=1)
    g_err = make_group(telegram_group_id=2)

    group_repo = AsyncMock(spec=TelegramGroupRepository)
    group_repo.find_active_groups = AsyncMock(return_value=[g_err, g_ok])

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    trend_repo.count_for_groups.return_value = {1: 5, 2: 5}

    context_repo = AsyncMock(spec=GroupContextRepository)
    context_repo.find_for_groups.return_value = {}

    call_count = [0]

    def side_effect(trends_count, prev_ctx, max_trends):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("test error")
        return True

    mock_evaluate.side_effect = side_effect

    service = _make_group_service(
        group_repo=group_repo,
        trend_repo=trend_repo,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    results = [g async for g in service.find_suitable_groups_for_context_analysis()]

    assert results == [g_ok]


# ---------------------------------------------------------------------------
# process_group_trends_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_trends_analysis_creates_trend():
    group = make_group(telegram_group_id=1)
    new_trend = make_group_trend(telegram_group_id=1, analysis_message_count=5)

    analytics_service = AsyncMock(spec=AnalyticsService)
    analytics_service.analyze_trends.return_value = new_trend

    trend_repo = AsyncMock(spec=GroupTrendRepository)

    service = _make_group_service(
        analytics_service=analytics_service,
        trend_repo=trend_repo,
        message_limit=20,
    )
    await service.process_group_trends_analysis(group)

    analytics_service.analyze_trends.assert_called_once_with(group)
    trend_repo.create.assert_called_once_with(new_trend)


@pytest.mark.asyncio
async def test_process_trends_analysis_cleanup_on_complete_trend():
    group = make_group(telegram_group_id=1)
    new_trend = make_group_trend(telegram_group_id=1, analysis_message_count=20)

    analytics_service = AsyncMock(spec=AnalyticsService)
    analytics_service.analyze_trends.return_value = new_trend

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    message_repo = AsyncMock(spec=TelegramMessageRepository)

    service = _make_group_service(
        analytics_service=analytics_service,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    await service.process_group_trends_analysis(group)

    trend_repo.delete_incomplete_trends.assert_called_once_with(1, 20)
    message_repo.delete_all_for_group.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_process_trends_analysis_no_cleanup_on_incomplete_trend():
    group = make_group(telegram_group_id=1)
    new_trend = make_group_trend(telegram_group_id=1, analysis_message_count=5)

    analytics_service = AsyncMock(spec=AnalyticsService)
    analytics_service.analyze_trends.return_value = new_trend

    trend_repo = AsyncMock(spec=GroupTrendRepository)
    message_repo = AsyncMock(spec=TelegramMessageRepository)

    service = _make_group_service(
        analytics_service=analytics_service,
        trend_repo=trend_repo,
        message_repo=message_repo,
        message_limit=20,
    )
    await service.process_group_trends_analysis(group)

    trend_repo.delete_incomplete_trends.assert_not_called()
    message_repo.delete_all_for_group.assert_not_called()


# ---------------------------------------------------------------------------
# process_group_context_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_context_analysis_creates_context():
    group = make_group(telegram_group_id=1)
    new_context = make_group_context(telegram_group_id=1, analysis_trends_count=3)

    analytics_service = AsyncMock(spec=AnalyticsService)
    analytics_service.analyze_context.return_value = new_context

    context_repo = AsyncMock(spec=GroupContextRepository)

    service = _make_group_service(
        analytics_service=analytics_service,
        context_repo=context_repo,
        max_trends_for_context=5,
    )
    await service.process_group_context_analysis(group)

    analytics_service.analyze_context.assert_called_once_with(group)
    context_repo.delete_old_contexts.assert_called_once_with(1)
    context_repo.create.assert_called_once_with(new_context)


@pytest.mark.asyncio
async def test_process_context_analysis_cleanup_on_complete_context():
    group = make_group(telegram_group_id=1)
    new_context = make_group_context(telegram_group_id=1, analysis_trends_count=5)

    analytics_service = AsyncMock(spec=AnalyticsService)
    analytics_service.analyze_context.return_value = new_context

    context_repo = AsyncMock(spec=GroupContextRepository)
    trend_repo = AsyncMock(spec=GroupTrendRepository)

    service = _make_group_service(
        analytics_service=analytics_service,
        context_repo=context_repo,
        trend_repo=trend_repo,
        max_trends_for_context=5,
    )
    await service.process_group_context_analysis(group)

    trend_repo.delete_all_for_group.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_process_context_analysis_no_cleanup_on_incomplete_context():
    group = make_group(telegram_group_id=1)
    new_context = make_group_context(telegram_group_id=1, analysis_trends_count=3)

    analytics_service = AsyncMock(spec=AnalyticsService)
    analytics_service.analyze_context.return_value = new_context

    context_repo = AsyncMock(spec=GroupContextRepository)
    trend_repo = AsyncMock(spec=GroupTrendRepository)

    service = _make_group_service(
        analytics_service=analytics_service,
        context_repo=context_repo,
        trend_repo=trend_repo,
        max_trends_for_context=5,
    )
    await service.process_group_context_analysis(group)

    trend_repo.delete_all_for_group.assert_not_called()

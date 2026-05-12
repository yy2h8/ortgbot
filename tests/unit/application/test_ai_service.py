import pytest
from unittest.mock import AsyncMock
from datetime import timedelta

from src.application.services.ai_service import AIService
from src.domain.exceptions import OpenRouterRateLimitError, InternalRateLimitError
from tests.conftest import make_openrouter_response


def _make_ai_service(
    openrouter_client=None,
    request_repo=None,
    rate_limiter=None,
    global_api_calls_per_day=500,
):
    return AIService(
        openrouter_client=openrouter_client or AsyncMock(),
        request_repo=request_repo or AsyncMock(),
        rate_limiter=rate_limiter or AsyncMock(),
        logger=_get_logger(),
        global_api_calls_per_day=global_api_calls_per_day,
    )


def _get_logger():
    import logging
    return logging.getLogger("test")


@pytest.mark.asyncio
async def test_request_success(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    response = make_openrouter_response()
    mock_openrouter_client.request.return_value = response

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    result = await service.request(
        model_id="test/model",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    assert result == response
    mock_openrouter_request_repo.create.assert_called_once()
    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.success is True


@pytest.mark.asyncio
async def test_request_tracking_fields(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    response = make_openrouter_response(prompt_tokens=100, completion_tokens=50, cost=0.002)
    mock_openrouter_client.request.return_value = response

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    await service.request(
        model_id="test/model",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.cost_estimate_usd == 0.002
    assert call_args.processing_time_ms >= 0


@pytest.mark.asyncio
async def test_request_error_tracking(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.side_effect = Exception("fail")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(Exception, match="fail"):
        await service.request(
            model_id="test/model",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.success is False
    assert call_args.error_message == "fail"


@pytest.mark.asyncio
async def test_request_with_paid_fallback_free_success(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    response = make_openrouter_response()
    mock_openrouter_client.request.return_value = response

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    result = await service.request_with_paid_fallback(
        free_model_id="free/model",
        paid_model_id="paid/model",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    assert result == response
    assert mock_openrouter_client.request.call_count == 1
    mock_openrouter_request_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_request_with_paid_fallback_free_rate_limited_paid_success(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    paid_response = make_openrouter_response(content="paid response")
    mock_openrouter_client.request.side_effect = [
        OpenRouterRateLimitError("rate limited"),
        paid_response,
    ]

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    result = await service.request_with_paid_fallback(
        free_model_id="free/model",
        paid_model_id="paid/model",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    assert result == paid_response
    assert mock_openrouter_client.request.call_count == 2


@pytest.mark.asyncio
async def test_request_with_paid_fallback_both_fail(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.side_effect = [
        OpenRouterRateLimitError("free limited"),
        Exception("paid error"),
    ]

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(Exception, match="paid error"):
        await service.request_with_paid_fallback(
            free_model_id="free/model",
            paid_model_id="paid/model",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    assert mock_openrouter_client.request.call_count == 2
    mock_openrouter_request_repo.create.assert_called_once()
    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.success is False


@pytest.mark.asyncio
async def test_request_with_paid_fallback_non_rate_limit_error(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.side_effect = Exception("generic error")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(Exception, match="generic error"):
        await service.request_with_paid_fallback(
            free_model_id="free/model",
            paid_model_id="paid/model",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    assert mock_openrouter_client.request.call_count == 1
    mock_openrouter_request_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limiter_called_first(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.return_value = make_openrouter_response()

    service = _make_ai_service(
        mock_openrouter_client,
        mock_openrouter_request_repo,
        mock_rate_limiter,
        global_api_calls_per_day=500,
    )

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    await service.request_with_paid_fallback(
        free_model_id="free/model",
        paid_model_id="paid/model",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    mock_rate_limiter.check.assert_called_with(
        key="global_api_calls",
        limit=500,
        window=timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_internal_rate_limit_propagates_without_tracking(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_rate_limiter.check.side_effect = InternalRateLimitError("rate limited")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(InternalRateLimitError):
        await service.request_with_paid_fallback(
            free_model_id="free/model",
            paid_model_id="paid/model",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    mock_openrouter_request_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_request_internal_rate_limit_propagates_without_tracking(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_rate_limiter.check.side_effect = InternalRateLimitError("daily limit")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(InternalRateLimitError):
        await service.request(
            model_id="test/model",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    mock_openrouter_client.request.assert_not_called()
    mock_openrouter_request_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_request_openrouter_rate_limit_reraises_without_tracking(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.side_effect = OpenRouterRateLimitError("429")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(OpenRouterRateLimitError):
        await service.request(
            model_id="test/model",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    mock_openrouter_request_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_request_error_tracking_includes_request_payload(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.side_effect = Exception("timeout")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="system prompt", user="user prompt")
    with pytest.raises(Exception, match="timeout"):
        await service.request(
            model_id="test/model",
            group_id=1,
            prompt=prompt,
            max_tokens=200,
            temperature=0.7,
        )

    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.request_payload == {
        "system_prompt": "system prompt",
        "user_prompt": "user prompt",
        "max_tokens": 200,
        "temperature": 0.7,
    }


@pytest.mark.asyncio
async def test_request_success_tracking_includes_response_fields(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    response = make_openrouter_response(
        raw_response={"id": "resp_123"},
        request_payload={"model": "test/model"},
    )
    mock_openrouter_client.request.return_value = response

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    await service.request(
        model_id="test/model",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.response_content == {"id": "resp_123"}
    assert call_args.request_payload == {"model": "test/model"}


@pytest.mark.asyncio
async def test_request_model_id_stored_in_success_tracking(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.return_value = make_openrouter_response()

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    await service.request(
        model_id="vendor/specific-model-v2",
        group_id=1,
        prompt=prompt,
        max_tokens=100,
        temperature=0.5,
    )

    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.model_openrouter_id == "vendor/specific-model-v2"


@pytest.mark.asyncio
async def test_request_model_id_stored_in_error_tracking(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter):
    mock_openrouter_client.request.side_effect = Exception("fail")

    service = _make_ai_service(mock_openrouter_client, mock_openrouter_request_repo, mock_rate_limiter)

    from src.domain.dto import Prompt
    prompt = Prompt(system="sys", user="usr")
    with pytest.raises(Exception, match="fail"):
        await service.request(
            model_id="vendor/specific-model-v2",
            group_id=1,
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

    call_args = mock_openrouter_request_repo.create.call_args[0][0]
    assert call_args.model_openrouter_id == "vendor/specific-model-v2"

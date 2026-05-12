import pytest

from src.domain.constants.prompt_templates import PromptTemplate
from src.domain.dto import Prompt


def _make_template(system="{a} {b}", user="{a} {b}", template_vars=None):
    return PromptTemplate(
        system_template=system,
        user_template=user,
        template_vars=template_vars or ["a", "b"],
    )


def test_render_substitutes_all_vars_in_system():
    tpl = _make_template()
    result = tpl.render(a="hello", b="world")
    assert "hello" in result.system
    assert "world" in result.system


def test_render_substitutes_all_vars_in_user():
    tpl = _make_template()
    result = tpl.render(a="hello", b="world")
    assert "hello" in result.user
    assert "world" in result.user


def test_render_raises_value_error_on_missing_var():
    tpl = _make_template()
    with pytest.raises(ValueError, match="a"):
        tpl.render(b="world")


def test_render_raises_value_error_on_none_var():
    tpl = _make_template()
    with pytest.raises(ValueError, match="a"):
        tpl.render(a=None, b="world")


def test_render_raises_on_partial_vars():
    tpl = _make_template(system="{a} {b} {c}", user="{a} {b} {c}", template_vars=["a", "b", "c"])
    with pytest.raises(ValueError, match="c"):
        tpl.render(a="x", b="y")


def test_render_returns_prompt_dto():
    tpl = _make_template()
    result = tpl.render(a="hello", b="world")
    assert isinstance(result, Prompt)
    assert hasattr(result, "system")
    assert hasattr(result, "user")

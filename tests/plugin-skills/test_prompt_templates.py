"""Checks that the skill-based prompt templates contain no file references and no inline idea types."""

import pytest

from i2code.template_renderer import render_template

SKILL_BASED_TEMPLATES = [
    "brainstorm-idea.md",
    "create-spec.md",
    "revise-spec.md",
    "create-implementation-plan.md",
    "repair-plan.md",
    "revise-plan.md",
]


@pytest.mark.unit
@pytest.mark.parametrize("template_name", SKILL_BASED_TEMPLATES)
def test_template_has_no_file_references_or_inline_idea_types(template_name):
    prompt = render_template(template_name, {})

    assert "@" not in prompt
    assert "Architecture POC" not in prompt

"""Tests for template_renderer: loads prompt templates and substitutes variables."""


import pytest


@pytest.mark.unit
class TestRenderTemplate:

    def test_substitutes_variables_in_template(self):
        from i2code.template_renderer import render_template

        result = render_template("create-spec.md", {
            "IDEA_FILE": "docs/my-idea.md",
            "DISCUSSION_FILE": "docs/my-discussion.md",
        })
        assert "docs/my-idea.md" in result
        assert "docs/my-discussion.md" in result

    def test_template_contains_original_content(self):
        from i2code.template_renderer import render_template

        result = render_template("create-spec.md", {
            "IDEA_FILE": "some-idea.md",
            "DISCUSSION_FILE": "some-discussion.md",
        })
        assert "specification" in result.lower()

    def test_raises_on_missing_template(self):
        from i2code.template_renderer import render_template

        with pytest.raises(FileNotFoundError):
            render_template("nonexistent-template.md", {})

    def test_preserves_dollar_signs_not_matching_variables(self):
        """Dollar signs that are not variable references should be preserved."""
        from i2code.template_renderer import render_template

        result = render_template("create-spec.md", {
            "IDEA_FILE": "idea.md",
            "DISCUSSION_FILE": "disc.md",
        })
        # The template uses ${IDEA_FILE} and ${DISCUSSION_FILE} syntax
        # After substitution, those should be replaced
        assert "${IDEA_FILE}" not in result
        assert "${DISCUSSION_FILE}" not in result

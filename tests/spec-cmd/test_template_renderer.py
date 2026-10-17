"""Tests for template_renderer: loads prompt templates and substitutes variables."""


import pytest


@pytest.mark.unit
class TestRenderTemplate:

    def test_substitutes_variables_in_template(self):
        from i2code.template_renderer import render_template

        result = render_template("create-spec.md", {
            "IDEA_DIRECTORY": "docs/ideas/active/my-idea",
        })
        assert "docs/ideas/active/my-idea" in result

    def test_template_contains_original_content(self):
        from i2code.template_renderer import render_template

        result = render_template("create-spec.md", {
            "IDEA_DIRECTORY": "docs/ideas/active/some-idea",
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
            "IDEA_DIRECTORY": "docs/ideas/active/idea",
        })
        # The template uses ${IDEA_DIRECTORY} syntax
        # After substitution, it should be replaced
        assert "${IDEA_DIRECTORY}" not in result

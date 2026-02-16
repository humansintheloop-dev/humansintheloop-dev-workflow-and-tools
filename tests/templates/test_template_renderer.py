"""Tests for the shared template renderer."""

import pytest

SAMPLE_PACKAGE = "tests.templates.sample_pkg"


@pytest.mark.unit
class TestRenderTemplate:

    def test_loads_and_renders_template(self):
        """Should load a .j2 file from {package}.templates and render variables."""
        from i2code.templates.template_renderer import render_template

        result = render_template("greeting.j2", package=SAMPLE_PACKAGE, name="World")

        assert result == "Hello, World!"

    def test_missing_template_raises_error(self):
        """Should raise FileNotFoundError for a nonexistent template."""
        from i2code.templates.template_renderer import render_template

        with pytest.raises(FileNotFoundError):
            render_template("nonexistent.j2", package=SAMPLE_PACKAGE)

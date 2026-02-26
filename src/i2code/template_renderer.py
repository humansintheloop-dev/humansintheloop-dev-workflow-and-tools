"""Template renderer: loads prompt templates and substitutes $VARIABLE placeholders."""

from pathlib import Path
from string import Template


_TEMPLATES_DIR = Path(__file__).parent / "prompt-templates"


def render_template(template_name: str, variables: dict[str, str]) -> str:
    """Load a prompt template and substitute $VARIABLE placeholders.

    Args:
        template_name: Filename within src/i2code/prompt-templates/
        variables: Mapping of variable names to values

    Returns:
        Rendered template string

    Raises:
        FileNotFoundError: If the template file does not exist
    """
    template_path = _TEMPLATES_DIR / template_name
    if not template_path.is_file():
        raise FileNotFoundError(f"Template not found: {template_path}")
    template_text = template_path.read_text()
    return Template(template_text).safe_substitute(variables)

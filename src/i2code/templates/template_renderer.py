"""Load and render Jinja2 templates from a caller's templates subpackage."""

import importlib.resources

import jinja2


def render_template(template_name: str, *, package: str, **kwargs) -> str:
    """Load a Jinja2 template by name and render it with the given arguments.

    Args:
        template_name: Template filename (e.g. "task_execution.j2")
        package: The caller's package (pass __package__). Templates are loaded
            from a ``templates`` subpackage beneath it.
        **kwargs: Template variables.

    Returns:
        The rendered template string.
    """
    templates = importlib.resources.files(f"{package}.templates")
    source = templates.joinpath(template_name).read_text(encoding="utf-8")
    return jinja2.Template(source).render(**kwargs)

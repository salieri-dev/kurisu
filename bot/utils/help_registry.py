"""Central registry for command help information."""

from functools import wraps

# This dictionary will store help info from all plugins
command_help: dict[str, dict] = {}


def command_handler(
    commands: list[str],
    description: str,
    group: str,
    arguments: str | None = None,
):
    """
    Decorator to register command help information.

    Args:
        commands: List of command names (without /).
        description: A brief explanation of what the command does.
        group: The category for the command (e.g., 'Нейронки', 'Рандом').
        arguments: Optional string describing the arguments (e.g., "[тема]").
    """

    def decorator(func):
        # Register help info for each command in the list
        for cmd in commands:
            command_help[cmd] = {
                "description": description,
                "arguments": arguments,
                "group": group,
            }

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator

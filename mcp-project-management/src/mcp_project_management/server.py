"""MCP Project Management Server — entry point."""

from . import prompts  # noqa: F401 — register prompts
from . import resources  # noqa: F401 — register resources
from .tools import mcp


def main() -> None:
    """Run the MCP server (stdio transport by default)."""
    mcp.run()


if __name__ == "__main__":
    main()

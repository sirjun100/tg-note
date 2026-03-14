"""MCP Server — entry point for Tasks and Joplin tools."""

from .tools import mcp


def main() -> None:
    """Run the MCP server (stdio transport by default)."""
    mcp.run()


if __name__ == "__main__":
    main()

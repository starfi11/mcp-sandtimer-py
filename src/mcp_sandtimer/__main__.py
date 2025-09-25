"""Executable entrypoint for running the MCP server."""
from .server import serve


def main() -> None:
    serve()


if __name__ == "__main__":
    main()

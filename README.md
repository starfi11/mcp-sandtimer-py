# MCP Sandtimer Server

A lightweight Python server that exposes the desktop **sandtimer** application through the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol). The process speaks JSON-RPC 2.0 over STDIO so that ChatGPT or any MCP-capable client can spin up named countdown timers by delegating to the sandtimer TCP listener on `127.0.0.1:61420`.

## Why it exists

Many AI assistants now understand the MCP handshake and tool contract. This project bridges that ecosystem with the existing Windows sandtimer utility:

- 🧩 Implements the full MCP initialization and tool flow without depending on any MCP framework.
- ⏱️ Offers three purpose-built tools—`start_timer`, `reset_timer`, and `cancel_timer`—with robust input validation and helpful text responses.
- 🔌 Proxies each tool call to the sandtimer process using a minimal TCP client so the GUI updates instantly.
- 📦 Can be packaged as a single-file Windows executable via GitHub Actions + PyInstaller for easy distribution.

## Repository layout

```
src/
└── mcp_sandtimer/
    ├── __init__.py          # package metadata and version
    ├── __main__.py          # console script entry point
    └── server.py            # MCP server, tool registry, TCP bridge
```

## Getting started

### Prerequisites
- Python 3.9 or newer.
- The sandtimer desktop app running locally and listening on port `61420` (default behaviour of the upstream project).

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Running the MCP server
With sandtimer already running:

```bash
python -m mcp_sandtimer
```

The server stays attached to STDIO, so it can be launched directly by ChatGPT, Cursor, or any MCP-aware client process.

### Available tools

| Tool | Arguments | Description |
| --- | --- | --- |
| `start_timer` | `label` (string), `time` (seconds, ≥ 1) | Create or restart a named timer window for the specified duration. |
| `reset_timer` | `label` (string) | Reset a timer back to its original duration. |
| `cancel_timer` | `label` (string) | Close the timer window entirely. |

## Using with Cursor (example)

Configure `.cursor/mcp.json` to launch the server from your local checkout:

```json
{
  "mcpServers": {
    "sandtimer": {
      "command": "python",
      "args": ["-m", "mcp_sandtimer"],
      "env": {
        "PYTHONPATH": "absolute\\\path\\\to\\\mcp-sandtimer-py\\\src",
        "SANDTIMER_HOST": "127.0.0.1",
        "SANDTIMER_PORT": "61420"
      }
    }
  }
}
```

> **Note:** The current implementation always connects to `127.0.0.1:61420`; the `SANDTIMER_HOST` and `SANDTIMER_PORT` variables are shown for convenience when wrapping the entry point with your own launcher.

## How it works

1. The MCP client starts the server process and performs the JSON-RPC `initialize` handshake over STDIO.
2. `server.py` registers the three timer tools and exposes `tools/list` and `tools/call` endpoints required by the MCP spec.
3. When a tool is invoked, the server validates arguments, forwards a JSON payload to the sandtimer TCP listener, and returns a human-readable confirmation string.
4. Any networking failure (for example, sandtimer not running) is propagated back to the MCP client as a structured error response.

## Releases

Pushing a git tag that starts with `v` triggers the workflow in [`.github/workflows/release.yml`](.github/workflows/release.yml): it builds a single-file Windows executable with PyInstaller and attaches the artifact to the GitHub release created for that tag.

## Demo

A quick demonstration of the integration in action:

![sandtimer-mcp](https://luweiphoto.oss-cn-wuhan-lr.aliyuncs.com/202509251732398.gif)

## License

Distributed under the MIT License. See [LICENSE](LICENSE).

# mcp-sandtimer-py

An MCP local server for sandtimer. After setup, you can control the local timer from chats in MCP clients like Cursor.

## How it works and tech stack

* Flow: The client talks to this process over STDIO using JSON-RPC 2.0 for MCP init and tool calls. This process forwards requests to the sandtimer TCP listener at `127.0.0.1:61420`, so the GUI updates instantly.
* Tools: `start_timer`, `reset_timer`, `cancel_timer`. Validates inputs and returns plain text results.
* Stack: Python 3.9+. MCP handshake and tool routing are hand-rolled. Optional single-file packaging via PyInstaller.

## Demo

![sandtimer-mcp](https://luweiphoto.oss-cn-wuhan-lr.aliyuncs.com/202509251732398.gif)

## Example config (Cursor)

Create `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "sandtimer": {
      "command": "python",
      "args": ["-m", "mcp_sandtimer"],
      "env": {
        "PYTHONPATH": "absolute\\path\\to\\mcp-sandtimer-py\\src",
        "SANDTIMER_HOST": "127.0.0.1",
        "SANDTIMER_PORT": "61420"
      }
    }
  }
}
```

> Note: The current build always connects to `127.0.0.1:61420`. The env vars help if you wrap the entry point yourself.

## Note

sandtimer is a separate repository that provides the desktop timer. This project is the MCP-side local bridge.

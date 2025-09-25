
# MCP Sandtimer Server

This repository contains a Python implementation of a local [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server that exposes the **sandtimer** desktop application through MCP tools. The server forwards JSON commands to the sandtimer TCP listener running on `127.0.0.1:61420`, allowing ChatGPT or any MCP compatible client to control the GUI timer application.

## Features

- Implements the MCP handshake and tool interfaces entirely over STDIO.
- Provides three tools: `start_timer`, `reset_timer`, and `cancel_timer`.
- Validates user input and forwards commands to sandtimer using TCP sockets.
- Packaged as a standalone executable for Windows via PyInstaller during tagged releases.

## Project Structure

```
src/
└── mcp_sandtimer/
    ├── init.py
    ├── main.py
    └── server.py
````

## Running locally

Create a virtual environment and install the project in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
````

Run the MCP server (ensure that the sandtimer application is already running and listening on the default port):

```bash
python -m mcp_sandtimer
```

The server communicates using STDIO, so it can be launched by ChatGPT or any MCP-compatible client. The included tools are:

| Tool           | Parameters                                   | Description                                             |
| -------------- | -------------------------------------------- | ------------------------------------------------------- |
| `start_timer`  | `label` (string), `time` (number of seconds) | Creates or restarts a timer with the provided duration. |
| `reset_timer`  | `label` (string)                             | Resets an existing timer to its original duration.      |
| `cancel_timer` | `label` (string)                             | Cancels and closes the timer window.                    |

## Using in Cursor

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



## Demo

This GIF shows the server in use:

![sandtimer-mcp](https://luweiphoto.oss-cn-wuhan-lr.aliyuncs.com/202509251732398.gif)

## Sandtimer integration

Each tool invocation generates a JSON command that is sent to the sandtimer process through TCP. The commands follow this shape:

```json
{ "cmd": "start", "label": "example", "time": 60 }
```

```json
{ "cmd": "reset", "label": "example" }
```

```json
{ "cmd": "cancel", "label": "example" }
```

If the sandtimer service is not reachable, the MCP tool will return an error to the client.

## Packaging and releases

When a tag starting with `v` (for example `v1.0.0`) is pushed, GitHub Actions automatically:

1. Checks out the repository on a Windows runner.
2. Installs the project dependencies and PyInstaller.
3. Builds a single-file executable containing the MCP server and its dependencies.
4. Uploads the resulting executable as an asset attached to the GitHub release that GitHub automatically creates for the tag.

The workflow definition lives in [`.github/workflows/release.yml`](.github/workflows/release.yml).

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.

```
::contentReference[oaicite:0]{index=0}
```

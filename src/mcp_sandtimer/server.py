"""Core logic for the sandtimer MCP server."""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from . import __version__

JsonDict = Dict[str, Any]


class MCPError(Exception):
    """Base error for MCP responses."""


class ToolExecutionError(MCPError):
    """Raised when a tool cannot be executed."""


@dataclass
class Tool:
    """Represents a registered tool."""

    name: str
    description: str
    schema: JsonDict
    handler: Callable[[JsonDict], str]


class SandtimerClient:
    """Thin TCP client responsible for talking to the sandtimer service."""

    def __init__(self, host: str = "127.0.0.1", port: int = 61420, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send(self, payload: JsonDict) -> None:
        message = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
            conn.sendall(message)

    def start(self, label: str, seconds: int) -> None:
        self._send({"cmd": "start", "label": label, "time": seconds})

    def reset(self, label: str) -> None:
        self._send({"cmd": "reset", "label": label})

    def cancel(self, label: str) -> None:
        self._send({"cmd": "cancel", "label": label})


class MCPServer:
    """A very small MCP compatible JSON-RPC server."""

    protocol_version = "2024-05-14"

    def __init__(self, client: Optional[SandtimerClient] = None) -> None:
        self._client = client or SandtimerClient()
        self._tools: Dict[str, Tool] = {}
        self._initialized = False
        self._write_lock = threading.Lock()
        self._register_builtin_tools()
        self._pending_ready_notification: Optional[JsonDict] = None

    def _register_builtin_tools(self) -> None:
        self.register_tool(
            Tool(
                name="start_timer",
                description="Start or restart a named sand timer.",
                schema={
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Human readable timer name.",
                        },
                        "time": {
                            "type": "number",
                            "description": "Duration of the timer in seconds.",
                            "minimum": 1,
                        },
                    },
                    "required": ["label", "time"],
                },
                handler=self._handle_start_timer,
            )
        )

        self.register_tool(
            Tool(
                name="reset_timer",
                description="Reset an existing sand timer to its original duration.",
                schema={
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Timer name to reset.",
                        }
                    },
                    "required": ["label"],
                },
                handler=self._handle_reset_timer,
            )
        )

        self.register_tool(
            Tool(
                name="cancel_timer",
                description="Cancel and close a sand timer window.",
                schema={
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Timer name to cancel.",
                        }
                    },
                    "required": ["label"],
                },
                handler=self._handle_cancel_timer,
            )
        )

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    # Tool handlers -----------------------------------------------------------------
    def _handle_start_timer(self, arguments: JsonDict) -> str:
        label = self._validate_label(arguments.get("label"))
        seconds_value = arguments.get("time")
        if not isinstance(seconds_value, (int, float)):
            raise ToolExecutionError("'time' must be a number of seconds.")
        seconds = int(seconds_value)
        if seconds <= 0:
            raise ToolExecutionError("'time' must be greater than zero.")
        try:
            self._client.start(label, seconds)
        except OSError as exc:  # pragma: no cover - network interaction
            raise ToolExecutionError(f"Failed to reach sandtimer service: {exc}") from exc
        return f"Timer '{label}' started for {seconds} seconds."

    def _handle_reset_timer(self, arguments: JsonDict) -> str:
        label = self._validate_label(arguments.get("label"))
        try:
            self._client.reset(label)
        except OSError as exc:  # pragma: no cover - network interaction
            raise ToolExecutionError(f"Failed to reach sandtimer service: {exc}") from exc
        return f"Timer '{label}' reset."

    def _handle_cancel_timer(self, arguments: JsonDict) -> str:
        label = self._validate_label(arguments.get("label"))
        try:
            self._client.cancel(label)
        except OSError as exc:  # pragma: no cover - network interaction
            raise ToolExecutionError(f"Failed to reach sandtimer service: {exc}") from exc
        return f"Timer '{label}' canceled."

    @staticmethod
    def _validate_label(label: Any) -> str:
        if not isinstance(label, str) or not label.strip():
            raise ToolExecutionError("'label' must be a non-empty string.")
        return label.strip()

    # JSON-RPC plumbing --------------------------------------------------------------
    def serve_forever(self) -> None:
        """Start serving requests over STDIO."""
        stdin = sys.stdin
        while True:
            line = stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                self._send_error(None, code=-32700, message="Parse error")
                continue
            response = self._handle_message(message)
            if response is not None:
                self._write_json(response)

    def _handle_message(self, message: JsonDict) -> Optional[JsonDict]:
        if not isinstance(message, dict):
            return self._make_error(None, -32600, "Invalid request")

        message_id = message.get("id")
        method = message.get("method")
        if method:
            params = message.get("params", {})
            if not isinstance(params, dict):
                params = {}
            if method == "initialize":
                result = self._handle_initialize(params)
                if message_id is not None:
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": result,
                    }
                return None
            if method == "tools/list":
                result = self._handle_tools_list()
                if message_id is not None:
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": result,
                    }
                return None
            if method == "tools/call":
                if message_id is None:
                    return None
                try:
                    result = self._handle_tools_call(params)
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": {
                            "content": [
                                {"type": "text", "text": result}
                            ]
                        },
                    }
                except ToolExecutionError as exc:
                    return self._make_error(message_id, -32002, str(exc))
                except Exception as exc:  # pragma: no cover - safeguard
                    return self._make_error(message_id, -32099, f"Unexpected error: {exc}")
            if method in {"ping", "shutdown"}:
                if message_id is not None:
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": {"time": time.time()} if method == "ping" else {},
                    }
                return None
            if method.startswith("notifications/"):
                return None
            if message_id is not None:
                return self._make_error(message_id, -32601, f"Method '{method}' not found")
            return None
        # If it is a response, ignore.
        return None

    def _handle_initialize(self, params: JsonDict) -> JsonDict:
        protocol_version = params.get("protocolVersion") or self.protocol_version
        self._initialized = True
        self._pending_ready_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/server/ready",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {"list": True, "call": True}},
            },
        }
        return {
            "protocolVersion": protocol_version,
            "serverInfo": {"name": "sandtimer-mcp", "version": __version__},
            "capabilities": {
                "tools": {"list": True, "call": True},
            },
        }

    def _handle_tools_list(self) -> JsonDict:
        tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.schema,
            }
            for tool in self._tools.values()
        ]
        return {"tools": tools}

    def _handle_tools_call(self, params: JsonDict) -> str:
        if not self._initialized:
            raise ToolExecutionError("Server has not been initialized yet.")
        name = params.get("name")
        if not isinstance(name, str):
            raise ToolExecutionError("Invalid tool name.")
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ToolExecutionError("Tool arguments must be an object.")
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"Tool '{name}' is not available.")
        return tool.handler(arguments)

    def _make_error(self, message_id: Any, code: int, message: str) -> JsonDict:
        return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}

    def _send_error(self, message_id: Any, code: int, message: str) -> None:
        self._write_json(self._make_error(message_id, code, message))

    def _write_json(self, payload: JsonDict) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        with self._write_lock:
            sys.stdout.write(text + "\n")
            sys.stdout.flush()
        self._flush_pending_notifications()

    def _flush_pending_notifications(self) -> None:
        if self._pending_ready_notification is not None:
            notification = self._pending_ready_notification
            self._pending_ready_notification = None
            with self._write_lock:
                sys.stdout.write(json.dumps(notification, ensure_ascii=False) + "\n")
                sys.stdout.flush()


def serve() -> None:
    """Entry point helper used by the CLI."""
    server = MCPServer()
    server.serve_forever()


__all__ = ["MCPServer", "serve"]

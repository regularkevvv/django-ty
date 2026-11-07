"""Framed LSP test client for installed companion qualification."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path


class Client:
    def __init__(
        self,
        command: list[str],
        root: Path,
        stderr: Path,
        *,
        server_request_handler: Callable[[Client, dict], bool] | None = None,
    ):
        self.log = stderr.open("wb")
        self.process = subprocess.Popen(
            command,
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log,
            env={**os.environ, "TY_UV": "0", "TY_MAX_PARALLELISM": "1"},
        )
        self.messages: queue.Queue = queue.Queue()
        self.notifications: list[dict] = []
        self.server_requests: list[dict] = []
        self.server_request_handler = server_request_handler
        self.next_id = 1
        self.timings: list[dict] = []
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            while True:
                headers = {}
                while (line := self.process.stdout.readline()) not in (b"\r\n", b"\n"):
                    if not line:
                        raise EOFError("server closed stdout")
                    key, value = line.decode().split(":", 1)
                    headers[key.lower()] = value.strip()
                self.messages.put(
                    json.loads(self.process.stdout.read(int(headers["content-length"])))
                )
        except Exception as error:
            self.messages.put(error)

    def send(self, message: dict):
        encoded = json.dumps({"jsonrpc": "2.0", **message}).encode()
        self.process.stdin.write(
            f"Content-Length: {len(encoded)}\r\n\r\n".encode() + encoded
        )
        self.process.stdin.flush()

    def notify(self, method: str, params: dict | None = None):
        self.send({"method": method, "params": params or {}})

    def _handle_server_request(self, message: dict):
        self.server_requests.append(message)
        # Returning True also permits deliberately deferring a response while a
        # protocol test drives another request. Existing clients use defaults.
        if self.server_request_handler and self.server_request_handler(self, message):
            return
        result = None
        if message["method"] == "workspace/configuration":
            result = [None] * len(message["params"]["items"])
        self.send({"id": message["id"], "result": result})

    def request(self, method: str, params: dict | None = None, *, retries: int = 2):
        started = time.perf_counter()
        ident = self.next_id
        self.next_id += 1
        self.send({"id": ident, "method": method, "params": params})
        while True:
            message = self.messages.get(timeout=120)
            if isinstance(message, Exception):
                raise message
            if "method" in message:
                if "id" in message:
                    self._handle_server_request(message)
                else:
                    self.notifications.append(message)
                continue
            assert message["id"] == ident, message
            self.timings.append(
                {"method": method, "seconds": time.perf_counter() - started}
            )
            if "error" in message:
                if (
                    retries
                    and method == "textDocument/diagnostic"
                    and message["error"]["code"] in {-32801, -32802}
                ):
                    return self.request(method, params, retries=retries - 1)
                raise RuntimeError(f"{method}: {message['error']}")
            return message["result"]

    def close(self):
        if self.process.poll() is not None:
            self.log.close()
            return
        try:
            self.request("shutdown")
            self.notify("exit")
            assert self.process.wait(timeout=10) == 0
        finally:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait()
            self.log.close()

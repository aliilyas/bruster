#!/usr/bin/env python3
"""Exercise the actual Linux Docker image over MCP; only Python's stdlib is needed."""

import argparse
import base64
import http.server
import json
import pathlib
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid


PAGE = b"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Bruster Docker test</title>
<style>body { font: 20px sans-serif; padding: 20px; } input, button { font: inherit; }</style>
<h1>Container browser fixture</h1>
<label>Name <input id="name"></label>
<button id="submit" onclick="document.querySelector('#result').textContent =
    'Hello, ' + document.querySelector('#name').value">Greet</button>
<p id="result">Waiting</p></html>"""


class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *_):
        pass


def docker(*args, timeout=30):
    return subprocess.check_output(["docker", *args], text=True, timeout=timeout).strip()


class Server:
    def __init__(self, image):
        self.name = "bruster-test-" + uuid.uuid4().hex[:12]
        self.stderr = tempfile.TemporaryFile(mode="w+t")
        self.started = time.monotonic()
        self.process = subprocess.Popen(
            [
                "docker", "run", "--rm", "-i", "--name", self.name,
                "--memory=512m", "--cpus=2", "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--add-host=host.docker.internal:host-gateway", image,
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            text=True, bufsize=1,
        )
        self.lines = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self.read_stdout, daemon=True).start()

    def read_stdout(self):
        try:
            for line in self.process.stdout:
                self.lines.put(line)
        finally:
            self.lines.put(None)

    def send(self, message):
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        self.process.stdin.flush()

    def rpc(self, method, params=None, timeout=30):
        self.next_id += 1
        self.send({"id": self.next_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{method}: no response within {timeout}s")
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError(f"{method}: no response within {timeout}s") from error
            if line is None:
                raise RuntimeError(f"{method}: container closed stdout")
            message = json.loads(line)  # Fails if startup diagnostics pollute MCP stdout.
            assert message.get("jsonrpc") == "2.0", message
            if message.get("id") == self.next_id:
                assert "error" not in message, message
                return message["result"]
            assert "id" not in message and "method" in message, message

    def initialize(self):
        result = self.rpc("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "bruster-docker-test", "version": "1"},
        })
        assert result["serverInfo"]["name"] == "bruster", result
        assert result["protocolVersion"] == "2025-06-18", result
        assert "tools" in result["capabilities"], result
        elapsed = time.monotonic() - self.started
        self.send({"method": "notifications/initialized"})
        return round(elapsed, 3)

    def tool(self, name, **arguments):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        assert not result.get("isError", False), (name, result)
        return result

    def text(self, name, **arguments):
        return "".join(item["text"] for item in self.tool(name, **arguments)["content"]
                       if item["type"] == "text")

    def wait(self, expected=0):
        status = self.process.wait(timeout=10)
        assert status == expected, f"container exited {status}, expected {expected}"

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        try:
            if self.process.poll() is None:
                subprocess.run(["docker", "rm", "-f", self.name],
                               capture_output=True, timeout=15, check=False)
                self.process.wait(timeout=10)
            if error is not None:
                self.stderr.seek(0)
                print(self.stderr.read(), file=sys.stderr)
        finally:
            self.process.stdin.close()
            self.process.stdout.close()
            self.stderr.close()


def exercise(image, url, https):
    metadata = json.loads(docker("image", "inspect", image))[0]
    assert metadata["Config"]["User"] == "10001:10001", metadata["Config"]["User"]
    results = {
        "image": image, "architecture": metadata["Architecture"],
        "image_size_mib": round(metadata["Size"] / 1024 ** 2, 1),
        "memory_limit_mib": 512,
    }
    with Server(image) as server:
        results["initialize_seconds"] = server.initialize()
        assert docker("exec", server.name, "id", "-u") == "10001"
        tools = server.rpc("tools/list")["tools"]
        names = {tool["name"] for tool in tools}
        assert {"navigate", "snapshot", "fill", "click", "screenshot", "close"} <= names
        assert all(tool["inputSchema"]["type"] == "object" for tool in tools)
        results["tools"] = len(tools)
        assert server.rpc("ping") == {}

        started = time.monotonic()
        server.tool("navigate", url=url, timeout=15000)
        assert server.text("title") == "Bruster Docker test"
        server.tool("fill", selector="#name", value="Docker")
        server.tool("click", selector="#submit")
        assert server.text("text", selector="#result") == "Hello, Docker"
        assert "Hello, Docker" in server.text("snapshot")
        assert server.text("eval", expression="6 * 7") == "42"

        server.tool("resize", width=640, height=480)
        screenshot = server.tool("screenshot")["content"]
        image_content = next(item for item in screenshot if item["type"] == "image")
        assert image_content["mimeType"] == "image/png"
        png = base64.b64decode(image_content["data"], validate=True)
        assert png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR"
        dimensions = struct.unpack(">II", png[16:24])
        assert dimensions == (640, 480), dimensions
        results["screenshot_pixels"] = list(dimensions)

        tab = json.loads(server.text("new_tab", url=url, timeout=15000))["tab"]
        assert len(json.loads(server.text("tabs"))) == 2
        assert server.text("title", tab=tab) == "Bruster Docker test"
        server.tool("close_tab", tab=tab)
        assert len(json.loads(server.text("tabs"))) == 1
        results["browser_checks_seconds"] = round(time.monotonic() - started, 3)

        if https:
            server.tool("navigate", url="https://example.com/", timeout=20000)
            assert server.text("title") == "Example Domain"
            results["https"] = "passed"
        results["memory_usage"] = docker("stats", "--no-stream", "--format", "{{.MemUsage}}", server.name)
        server.tool("close")
        server.wait()
        results["mcp_close"] = "passed"

    # EOF and SIGTERM must also work with Xvfb and WebKit child processes alive.
    with Server(image) as server:
        server.initialize()
        server.tool("title")
        started = time.monotonic()
        server.process.stdin.close()
        server.wait()
        results["eof_shutdown_seconds"] = round(time.monotonic() - started, 3)
    with Server(image) as server:
        server.initialize()
        server.tool("title")
        started = time.monotonic()
        docker("stop", "--time", "5", server.name, timeout=15)
        server.wait(expected=143)  # SIGTERM, not a forced SIGKILL (137).
        results["sigterm_shutdown_seconds"] = round(time.monotonic() - started, 3)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="bruster:local")
    parser.add_argument("--https", action="store_true", help="also navigate to https://example.com")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    fixture = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    try:
        result = exercise(args.image, f"http://host.docker.internal:{fixture.server_port}/", args.https)
    finally:
        fixture.shutdown()
        fixture.server_close()
    report = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
    print(report, end="")
    print("PASS: Docker MCP, browser, and shutdown checks")


if __name__ == "__main__":
    main()

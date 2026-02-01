import argparse
import subprocess
import sys
import time

import requests


def wait_for_server(api_base: str, timeout: int) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{api_base}/api/v1/worker/status", timeout=5)
            response.raise_for_status()
            return
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(1)
    raise SystemExit(f"Server did not become ready: {last_error}")


def start_server(args: argparse.Namespace) -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")
    process = subprocess.Popen(cmd)
    try:
        wait_for_server(args.api, args.server_timeout)
    except Exception:
        process.terminate()
        raise
    return process


def prompt_if_missing(value: str | None, label: str) -> str:
    if value:
        return value
    entered = input(f"{label}: ").strip()
    if not entered:
        raise SystemExit(f"{label} is required.")
    return entered


def parse_list(values: list[str] | None, label: str) -> list[str]:
    if values:
        return [value.strip() for value in values if value.strip()]
    entered = input(f"{label} (comma-separated, optional): ").strip()
    if not entered:
        return []
    return [value.strip() for value in entered.split(",") if value.strip()]


def add_server_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api", default="http://localhost:8001", help="API base URL")
    parser.add_argument("--host", default="0.0.0.0", help="Uvicorn host")
    parser.add_argument("--port", type=int, default=8001, help="Uvicorn port")
    parser.add_argument(
        "--server-timeout",
        type=int,
        default=30,
        help="Seconds to wait for API server to boot",
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Skip starting uvicorn (assume it is already running)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Start uvicorn with reload enabled",
    )

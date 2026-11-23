"""Isolated real HTTP server lifecycle for smoke tests."""

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    """Ask the operating system for an available loopback port."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def server_environment(directory):
    """Override database and media locations without touching working data."""
    return os.environ | {
        "DJANGO_DEBUG": "true",
        "DJANGO_SETTINGS_MODULE": "core.settings",
        "DJANGO_DB_PATH": str(Path(directory) / "test.sqlite3"),
        "DJANGO_MEDIA_ROOT": str(Path(directory) / "media"),
        "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost",
    }


def migrate(environment):
    """Create a fresh database using the committed migrations."""
    command = [sys.executable, "manage.py", "migrate", "--noinput"]
    subprocess.run(
        command, cwd=ROOT, env=environment, check=True, stdout=subprocess.DEVNULL
    )


def await_ready(process, base):
    """Wait briefly for the actual server process to answer HTTP."""
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("HTTP server exited before becoming ready.")
        try:
            with urlopen(base + "base-info/", timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError("HTTP server did not become ready within ten seconds.")


@contextmanager
def running_process(port, environment):
    """Always reap the local server, including on failed checks."""
    process = launch_server(port, environment)
    try:
        yield process
    finally:
        process.terminate()
        process.wait(timeout=10)


def launch_server(port, environment):
    """Launch a development server with isolated paths."""
    address = f"127.0.0.1:{port}"
    command = [sys.executable, "manage.py", "runserver", address, "--noreload"]
    return subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@contextmanager
def live_server():
    """Yield an isolated HTTP base URL and discard all test data on exit."""
    with TemporaryDirectory(prefix="coderr-http-") as directory:
        environment = server_environment(directory)
        migrate(environment)
        port = free_port()
        with running_process(port, environment) as process:
            base = f"http://127.0.0.1:{port}/api/"
            await_ready(process, base)
            yield base

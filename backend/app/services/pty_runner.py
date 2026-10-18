"""Runs a command inside a real pty so interactive LeRobot CLIs (which use input(),
live cursor-redraw tables, and Ctrl+C) behave exactly as they would in a terminal, and
broadcasts the raw bytes to any number of connected websocket viewers.

POSIX uses the stdlib pty module; Windows uses ConPTY via pywinpty."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from winpty import PtyProcess
else:
    import fcntl
    import pty
    import struct
    import termios

SCROLLBACK_LIMIT = 400_000  # bytes kept for late-joining viewers


@dataclass
class RunHandle:
    id: str
    kind: str
    argv: list[str]
    cwd: str
    status: str = "running"  # running | exited | failed | stopped
    exit_code: int | None = None
    created_at: float = field(default_factory=time.time)
    master_fd: int | None = None
    pid: int | None = None
    win_proc: Any = None  # winpty.PtyProcess on Windows
    _buffer: bytearray = field(default_factory=bytearray)
    _subscribers: set[asyncio.Queue] = field(default_factory=set)
    _done_event: asyncio.Event = field(default_factory=asyncio.Event)

    def snapshot(self) -> bytes:
        return bytes(self._buffer)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def _feed(self, data: bytes) -> None:
        self._buffer.extend(data)
        if len(self._buffer) > SCROLLBACK_LIMIT:
            del self._buffer[: len(self._buffer) - SCROLLBACK_LIMIT]
        for q in list(self._subscribers):
            q.put_nowait(data)

    def _finish(self, status: str, exit_code: int | None) -> None:
        self.status = status
        self.exit_code = exit_code
        self._done_event.set()
        marker = f"\r\n\x1b[2m[process {status}{'' if exit_code is None else f', exit code {exit_code}'}]\x1b[0m\r\n".encode()
        self._feed(marker)
        for q in list(self._subscribers):
            q.put_nowait(None)  # sentinel: stream closed


class PtyRunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RunHandle] = {}

    def get(self, run_id: str) -> RunHandle | None:
        return self._runs.get(run_id)

    def list(self) -> list[RunHandle]:
        return list(self._runs.values())

    async def start(self, kind: str, argv: list[str], cwd: Path, env: dict | None = None) -> RunHandle:
        run_id = uuid.uuid4().hex[:12]

        full_env = os.environ.copy()
        full_env["TERM"] = "xterm-256color"
        full_env["PYTHONUNBUFFERED"] = "1"
        full_env["PYTHONIOENCODING"] = "utf-8"
        if env:
            full_env.update(env)

        if IS_WINDOWS:
            handle = self._start_windows(run_id, kind, argv, cwd, full_env)
        else:
            handle = await self._start_posix(run_id, kind, argv, cwd, full_env)
        self._runs[run_id] = handle
        return handle

    def _start_windows(self, run_id: str, kind: str, argv: list[str], cwd: Path, full_env: dict) -> RunHandle:
        proc = PtyProcess.spawn(argv, cwd=str(cwd), env=full_env, dimensions=(32, 120))
        handle = RunHandle(id=run_id, kind=kind, argv=argv, cwd=str(cwd), pid=proc.pid, win_proc=proc)
        loop = asyncio.get_running_loop()

        # pywinpty only offers blocking reads, so pump output from a thread back into the loop.
        def _reader() -> None:
            while True:
                try:
                    data = proc.read(65536)
                except (EOFError, OSError):
                    break
                if data:
                    loop.call_soon_threadsafe(handle._feed, data.encode("utf-8", errors="replace"))
            while proc.isalive():
                time.sleep(0.05)
            returncode = proc.exitstatus
            loop.call_soon_threadsafe(handle._finish, "exited" if returncode == 0 else "failed", returncode)

        threading.Thread(target=_reader, daemon=True).start()
        return handle

    async def _start_posix(self, run_id: str, kind: str, argv: list[str], cwd: Path, full_env: dict) -> RunHandle:
        master_fd, slave_fd = pty.openpty()
        _set_winsize(master_fd, rows=32, cols=120)

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=str(cwd),
            env=full_env,
            start_new_session=True,
        )
        os.close(slave_fd)

        handle = RunHandle(id=run_id, kind=kind, argv=argv, cwd=str(cwd), master_fd=master_fd, pid=proc.pid)

        loop = asyncio.get_running_loop()
        os.set_blocking(master_fd, False)

        def _on_readable() -> None:
            try:
                data = os.read(master_fd, 65536)
            except OSError:
                data = b""
            if data:
                handle._feed(data)
            else:
                loop.remove_reader(master_fd)

        loop.add_reader(master_fd, _on_readable)

        async def _wait_and_close() -> None:
            returncode = await proc.wait()
            # Drain any remaining bytes buffered in the pty after the child exits.
            with contextlib.suppress(OSError):
                while True:
                    chunk = os.read(master_fd, 65536)
                    if not chunk:
                        break
                    handle._feed(chunk)
            with contextlib.suppress(ValueError):
                loop.remove_reader(master_fd)
            with contextlib.suppress(OSError):
                os.close(master_fd)
            handle._finish("exited" if returncode == 0 else "failed", returncode)

        asyncio.create_task(_wait_and_close())
        return handle

    def write(self, run_id: str, data: bytes) -> bool:
        handle = self.get(run_id)
        if handle is None or handle.status != "running":
            return False
        if handle.win_proc is not None:
            with contextlib.suppress(EOFError, OSError):
                handle.win_proc.write(data.decode("utf-8", errors="replace"))
            return True
        if handle.master_fd is None:
            return False
        with contextlib.suppress(OSError):
            os.write(handle.master_fd, data)
        return True

    def resize(self, run_id: str, rows: int, cols: int) -> None:
        handle = self.get(run_id)
        if handle is None:
            return
        if handle.win_proc is not None:
            with contextlib.suppress(Exception):
                handle.win_proc.setwinsize(rows, cols)
            return
        if handle.master_fd is None:
            return
        with contextlib.suppress(OSError):
            _set_winsize(handle.master_fd, rows, cols)

    def stop(self, run_id: str, force: bool = False) -> bool:
        handle = self.get(run_id)
        if handle is None or handle.status != "running" or handle.pid is None:
            return False

        if handle.win_proc is not None:
            if force:
                # Kill the whole tree (console scripts spawn a child python.exe).
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(handle.pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                # Ctrl+C typed into the console raises KeyboardInterrupt, same as SIGINT on POSIX.
                with contextlib.suppress(EOFError, OSError):
                    handle.win_proc.sendintr()
            return True

        sig = signal.SIGKILL if force else signal.SIGINT
        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(handle.pid), sig)
        return True


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


registry = PtyRunRegistry()

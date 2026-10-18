"""Watches the serial ports so plugging in an arm's USB cable shows up as a live
ADDED event in the UI — the actual 'wire connector' moment, mirroring the manual
snapshot-diff trick LeRobot's own lerobot-find-port script uses.

Linux reads /dev/serial/by-id (stable, descriptive names); other OSes (Windows COM
ports, macOS /dev/tty.*) go through pyserial, the same library LeRobot talks to the
motors with."""

from __future__ import annotations

import asyncio
import sys

from serial.tools import list_ports

from app.config import PORT_POLL_INTERVAL_S, SERIAL_BY_ID_DIR


def _pyserial_snapshot() -> list[dict]:
    ports = []
    for info in sorted(list_ports.comports(), key=lambda i: i.device):
        if info.vid is None:  # skip built-in / Bluetooth ports, keep USB adapters
            continue
        desc = info.description if info.description and info.description != "n/a" else info.device
        label = desc if info.device in desc else f"{desc} ({info.device})"
        ports.append({"label": label, "path": info.device})
    return ports


def snapshot() -> list[dict]:
    if not sys.platform.startswith("linux"):
        return _pyserial_snapshot()
    if not SERIAL_BY_ID_DIR.is_dir():
        return []
    ports = []
    for entry in sorted(SERIAL_BY_ID_DIR.iterdir()):
        try:
            resolved = str((SERIAL_BY_ID_DIR / entry.name).resolve())
        except OSError:
            continue
        ports.append({"label": entry.name, "path": resolved})
    return ports


async def watch(queue: asyncio.Queue) -> None:
    """Pushes {"type": "added"|"removed", "label": ..., "path": ...} events until cancelled."""
    prev = {p["label"]: p for p in snapshot()}
    try:
        while True:
            await asyncio.sleep(PORT_POLL_INTERVAL_S)
            cur = {p["label"]: p for p in snapshot()}
            for label in cur.keys() - prev.keys():
                await queue.put({"type": "added", **cur[label]})
            for label in prev.keys() - cur.keys():
                await queue.put({"type": "removed", **prev[label]})
            prev = cur
    except asyncio.CancelledError:
        pass

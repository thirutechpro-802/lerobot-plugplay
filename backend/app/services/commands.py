"""Builds argv lists for the LeRobot CLI commands each block runs, and reports whether
the underlying install is even usable yet."""

from __future__ import annotations

import sys
from pathlib import Path

from app.config import EXE_SUFFIX, LEROBOT_PYTHON, LEROBOT_REPO, LEROBOT_VENV_BIN

BACKEND_DIR = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = BACKEND_DIR / "scripts" / "install_lerobot.py"


def _console_script(name: str) -> list[str]:
    """Prefer the installed console script (`lerobot-calibrate`), fall back to
    `python -m lerobot.scripts...` so this still works right after a fresh `pip install -e`
    before the venv's bin dir is fully populated on some platforms."""
    exe = LEROBOT_VENV_BIN / f"{name}{EXE_SUFFIX}"
    if exe.exists():
        return [str(exe)]
    module = "lerobot.scripts." + name.replace("-", "_")
    return [str(LEROBOT_PYTHON), "-m", module]


def install_argv() -> list[str]:
    # Run with the backend's own interpreter so the installer works without bash (Windows).
    return [sys.executable, str(INSTALL_SCRIPT), str(LEROBOT_REPO)]


def calibrate_argv(device_kind: str, robot_type: str, port: str, device_id: str) -> list[str]:
    """device_kind is 'robot' or 'teleop'."""
    assert device_kind in ("robot", "teleop")
    return [
        *_console_script("lerobot-calibrate"),
        f"--{device_kind}.type={robot_type}",
        f"--{device_kind}.port={port}",
        f"--{device_kind}.id={device_id}",
    ]


def teleoperate_argv(
    robot_type: str,
    robot_port: str,
    robot_id: str,
    teleop_type: str,
    teleop_port: str,
    teleop_id: str,
    fps: int = 30,
    display_data: bool = False,
) -> list[str]:
    return [
        *_console_script("lerobot-teleoperate"),
        f"--robot.type={robot_type}",
        f"--robot.port={robot_port}",
        f"--robot.id={robot_id}",
        f"--teleop.type={teleop_type}",
        f"--teleop.port={teleop_port}",
        f"--teleop.id={teleop_id}",
        f"--fps={fps}",
        f"--display_data={'true' if display_data else 'false'}",
    ]

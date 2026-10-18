"""Locates the LeRobot checkout + venv this app drives, and its calibration dir."""

import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
# venvs put executables in Scripts\*.exe on Windows, bin/* everywhere else.
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""


def _first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


LEROBOT_REPO = Path(
    os.environ.get("LEROBOT_REPO_PATH")
    or _first_existing(
        [
            Path.home() / "lerobot",
            Path(__file__).resolve().parents[3] / "lerobot",
        ]
    )
    or (Path.home() / "lerobot")
).expanduser()

LEROBOT_VENV = Path(os.environ.get("LEROBOT_VENV_PATH") or (LEROBOT_REPO / ".venv")).expanduser()
LEROBOT_VENV_BIN = LEROBOT_VENV / ("Scripts" if IS_WINDOWS else "bin")
LEROBOT_PYTHON = LEROBOT_VENV_BIN / f"python{EXE_SUFFIX}"

# Same default LeRobot itself uses (see src/lerobot/utils/constants.py), overridable the same way.
HF_LEROBOT_CALIBRATION = Path(
    os.environ.get("HF_LEROBOT_CALIBRATION") or (Path.home() / ".cache" / "huggingface" / "lerobot" / "calibration")
).expanduser()

# Linux only; other OSes enumerate ports through pyserial instead.
SERIAL_BY_ID_DIR = Path(os.environ.get("SERIAL_BY_ID_DIR") or "/dev/serial/by-id").expanduser()

PORT_POLL_INTERVAL_S = 0.4

"""Installs everything LeRobot needs for an SO-101 arm: system prerequisites (reported,
not auto-installed — they usually need sudo/admin), the Python venv, and the feetech motor
extra. Mirrors lerobot/AGENT_GUIDE.md §4.1. Safe to re-run. Works on Linux, macOS and Windows.

usage: python install_lerobot.py <lerobot-repo-path>
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def step(msg: str) -> None:
    print(f"\n\033[1;36m==> {msg}\033[0m", flush=True)


def ok(msg: str) -> None:
    print(f"\033[1;32m  ok:\033[0m {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"\033[1;33m  missing:\033[0m {msg}", flush=True)


def fail(msg: str, code: int = 1) -> None:
    print(f"\n\033[1;31m{msg}\033[0m", flush=True)
    sys.exit(code)


def run(argv: list[str], cwd: Path | None = None) -> int:
    return subprocess.call(argv, cwd=cwd)


def install_hint(apt_pkg: str, winget_id: str) -> str:
    return f"winget install {winget_id}" if IS_WINDOWS else f"sudo apt install {apt_pkg}"


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: install_lerobot.py <lerobot-repo-path>")
    repo = Path(sys.argv[1]).expanduser()

    if not (repo / ".git").is_dir():
        step("Cloning LeRobot (first run only)")
        if shutil.which("git") is None:
            fail(f'git is required to clone LeRobot — install it first (e.g. "{install_hint("git", "Git.Git")}").')
        if run(["git", "clone", "https://github.com/huggingface/lerobot.git", str(repo)]) != 0:
            sys.exit(1)

    step("Checking system prerequisites")
    if shutil.which("git"):
        ok("git found")
    else:
        fail("git not found — install it first.")
    if shutil.which("ffmpeg"):
        ok("ffmpeg found")
    else:
        warn("ffmpeg not found — optional, only needed later for recording camera datasets, not for calibration/teleoperation. Skipping.")
    if shutil.which("git-lfs"):
        ok("git-lfs found")
    else:
        warn("git-lfs not found — optional, only needed later for recording/sharing datasets, not for calibration/teleoperation. Skipping.")

    step("Setting up the Python environment")
    venv = repo / ".venv"
    venv_python = venv / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
    if shutil.which("uv"):
        ok("uv found, using it (recommended path)")
        status = run(["uv", "sync", "--locked", "--extra", "feetech"], cwd=repo)
    else:
        warn("uv not found — falling back to python -m venv + pip (slower, still works)")
        status = 0
        if not venv_python.exists():
            status = run([sys.executable, "-m", "venv", str(venv)])
        if status == 0:
            # `python -m pip` rather than the pip executable: on Windows pip can't replace its own .exe.
            status = run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
        if status == 0:
            status = run([str(venv_python), "-m", "pip", "install", "-e", ".[feetech]"], cwd=repo)

    if status != 0:
        fail("Install step failed (see errors above).", status)

    step("Verifying the install")
    status = run([str(venv_python), "-c", "import serial; import scservo_sdk; print('pyserial + feetech SDK import OK')"])

    # Deliberately not running `git lfs pull` here — it downloads LeRobot's full test-fixture
    # dataset (used only by its own test suite), which can be a large, unnecessary download for
    # someone who just wants to calibrate/teleoperate. Only fetch LFS assets if/when a future
    # dataset-recording block actually needs them.

    if status == 0:
        print("\n\033[1;32mLeRobot is installed and ready.\033[0m", flush=True)
    else:
        fail("Python packages installed but failed to import — check the errors above.", status)


if __name__ == "__main__":
    main()

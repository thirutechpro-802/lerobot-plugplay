# Get Set Robotics — LeRobot SO101 Action Graph

A plug-and-play, block-based interface for setting up a LeRobot SO-101 arm — built for **beginners**,
no robotics experience needed. Wire blocks together like connectors: Install → Calibrate → Teleoperate.

## Setup

### 1. Install prerequisites

Requires **git**, **Python 3.10+**, and **Node.js 18+**. Skip anything you already have.

**Linux (Ubuntu/Debian):**
```bash
sudo apt install -y git python3
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**macOS (with [Homebrew](https://brew.sh)):**
```bash
brew install git python node
```

**Windows:** install [Git](https://git-scm.com/downloads), [Python](https://www.python.org/downloads/)
(3.10+, tick **"Add python.exe to PATH"**), and [Node.js LTS](https://nodejs.org/) from their official
installers — or in one go from a terminal:
```powershell
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS
```

**Any OS, no sudo/admin needed:** use [nvm](https://github.com/nvm-sh/nvm) for Node.js:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# restart your terminal, then:
nvm install 20
```

Check everything is on `PATH`: `git --version && python3 --version && node -v && npm -v`

### 2. Clone and run

```bash
git clone https://github.com/gowrishankar12757-sudo/lerobot-plugplay.git
cd lerobot-plugplay
./start.sh        # Linux / macOS
start.bat         # Windows (or double-click start.bat in Explorer)
```

Open **http://127.0.0.1:5173**

## Steps

1. Click **Install now** on the Install block (sets up LeRobot automatically, first run only).
2. Plug in an arm, add a **Calibrate block**, pick its port, give it a name, click **Start calibration**
   and follow the on-screen prompts.
3. Repeat step 2 for the second arm (one Leader, one Follower).
4. Add a **Teleoperate block**, wire both calibrated arms into it, click **Start teleoperation**.

## Important

- **Linux "Permission denied" on the USB port?** Run `sudo usermod -aG dialout $USER`, then log out and
  back in.
- **Windows: arm doesn't show up?** It should appear as a `COM` port. If it doesn't, install the USB-serial
  driver for your motor bus board (usually CH340 or CP210x) and re-plug it. Close any other program
  (Feetech FD software, Arduino IDE, etc.) that has the COM port open.
- **Missing ffmpeg / git-lfs?** The Install block will flag it — only needed later for recording data.

## License

[Apache License 2.0](./LICENSE)

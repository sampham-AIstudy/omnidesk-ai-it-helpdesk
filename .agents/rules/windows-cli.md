---
description: "Optimizations for Windows CLI and Terminal Command Execution"
activation: always-on
---

# Windows CLI & Command Execution Optimization

## 1. Environment & Shell
- Operating System: Windows.
- Always execute native executables directly without bash wrappers (e.g. `git`, `npm`, `npx`, `python`).
- Always use the project Python virtualenv path directly:
  `.\.venv\Scripts\python.exe` (never use `source .venv/bin/activate` or `python3`).

## 2. Command Formatting & Syntax
- Do not use Linux-only commands/aliases (`export`, `cat`, `ls`, `grep`, `rm -rf`).
- Use Windows/PowerShell compatible equivalents or native tools (`Get-ChildItem`, `Remove-Item`, `ripgrep`).
- When running multiple commands, do not use `&&` in PowerShell; execute commands sequentially or separate with `;`.
- Always quote file paths that contain spaces.

## 3. Pytest & Testing on Windows
- Always append `--basetemp=./data/pytest_tmp` to pytest commands to prevent Windows Temp folder `PermissionError [WinError 5]`.
- Prefer running targeted test files rather than monolithic multi-suite runs to prevent test-runner timeout.

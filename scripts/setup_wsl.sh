#!/usr/bin/env bash
# Installs the system packages missing for this project on Ubuntu 26.04 (WSL2).
# Requires sudo. Run manually: bash scripts/setup_wsl.sh
# Already present (not touched): python3 3.14.4, git 2.53.0, PostgreSQL 18.6, NVIDIA driver.
set -euo pipefail

sudo apt-get update

# python3-venv: provides ensurepip, required for `python3 -m venv .venv` to bootstrap pip.
# python3-pip: system pip (project deps still go only inside .venv).
# zstd: the Ollama install script needs it to unpack its .tar.zst archive.
sudo apt-get install -y python3-venv python3-pip zstd

# GitHub CLI (gh) from the official Ubuntu repository.
sudo apt-get install -y gh

# Ollama: the official installer uses sudo internally (binary in /usr/local,
# systemd service, `ollama` user). It detects the NVIDIA GPU through WSL libs.
curl -fsSL https://ollama.com/install.sh | sh

# --- No sudo needed after this point (run as your user) ---
# ollama pull qwen3:4b
# ollama run qwen3:4b "hello"   # then check GPU usage with: ollama ps
# gh auth login

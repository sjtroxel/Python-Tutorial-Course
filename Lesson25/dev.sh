#!/usr/bin/env bash
# Lesson25 dev runner — one command that boots BOTH the Tailwind watcher and the
# Flask/waitress server together, the way `npm run dev` booted frontend + backend.
#
#   Usage:  ./dev.sh        (Ctrl+C stops both)
#
# Always run from this script's own folder, so it works no matter where you call it.
cd "$(dirname "$0")"

# 1) Start the Tailwind watcher in the BACKGROUND (the trailing & detaches it) and
#    remember its process id so we can stop it later.
./tailwindcss-linux-x64 -i ./static/src/input.css -o ./static/styles/output.css --watch &
TAILWIND_PID=$!

# 2) When this script exits (you press Ctrl+C), also kill the background watcher,
#    so you don't leave an orphan process running. `trap ... EXIT` = "run this on exit".
trap "kill $TAILWIND_PID 2>/dev/null" EXIT

# 3) Run the server in the FOREGROUND. This blocks and holds the terminal until
#    Ctrl+C, at which point the trap above cleans up the watcher.
.venv/bin/python server.py

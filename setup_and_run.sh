#!/bin/bash

echo "=== Checking virtual environment ==="
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "=== Activating virtual environment ==="
source venv/bin/activate

echo "=== Installing requirements ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Starting services in tmux ==="

# Start or attach to tmux session
tmux has-session -t discordbot 2>/dev/null

if [ $? != 0 ]; then
    tmux new-session -d -s discordbot -n auth 'python auth_server.py'
    tmux new-window -t discordbot -n bot 'python bot_main.py'
    echo "Started new tmux session 'discordbot' with two windows."
else
    echo "Session already exists. Attaching..."
fi

tmux attach-session -t discordbot

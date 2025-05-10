#!/bin/bash

SESSION="discordbot"

if tmux has-session -t $SESSION 2>/dev/null; then
    echo "Stopping tmux session: $SESSION"
    tmux kill-session -t $SESSION
    echo "✅ All services stopped."
else
    echo "❌ No tmux session named '$SESSION' found."
fi

@echo off
IF NOT EXIST "venv" (
    echo === Creating virtual environment ===
    python -m venv venv
)

echo === Activating virtual environment ===
call venv\Scripts\activate

echo === Installing requirements ===
pip install --upgrade pip
pip install -r requirements.txt

echo === Launching Auth Server ===
start "Auth Server" cmd /k python auth_server.py

echo === Launching Discord Bot ===
start "Discord Bot" cmd /k python bot_main.py

#!/usr/bin/env python3
"""
Development environment setup script for Discord Task Management Bot
This script sets up the complete development environment including virtual environment,
dependencies, pre-commit hooks, and database initialization.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: str, cwd: str = None) -> bool:
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Command failed: {command}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Exception running command '{command}': {e}")
        return False


def check_python_version():
    """Check if Python version is 3.11 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"❌ Python 3.11+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True


def setup_virtual_environment():
    """Create and activate virtual environment"""
    print("🔧 Setting up virtual environment...")
    
    # Remove existing .venv if it exists
    if Path(".venv").exists():
        print("📁 Removing existing .venv directory...")
        if os.name == 'nt':  # Windows
            run_command("rmdir /s /q .venv")
        else:  # Unix/Linux/macOS
            run_command("rm -rf .venv")
    
    # Create new virtual environment
    if not run_command(f"{sys.executable} -m venv .venv"):
        return False
    
    print("✅ Virtual environment created")
    return True


def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    
    # Determine pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = ".venv\\Scripts\\pip"
        python_path = ".venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        pip_path = ".venv/bin/pip"
        python_path = ".venv/bin/python"
    
    # Upgrade pip first
    if not run_command(f"{python_path} -m pip install --upgrade pip"):
        return False
    
    # Install production dependencies
    if not run_command(f"{pip_path} install -r requirements.txt"):
        return False
    
    # Install development dependencies
    if not run_command(f"{pip_path} install -r requirements-dev.txt"):
        return False
    
    print("✅ Dependencies installed")
    return True


def setup_pre_commit():
    """Set up pre-commit hooks"""
    print("🪝 Setting up pre-commit hooks...")
    
    # Determine pre-commit path based on OS
    if os.name == 'nt':  # Windows
        precommit_path = ".venv\\Scripts\\pre-commit"
    else:  # Unix/Linux/macOS
        precommit_path = ".venv/bin/pre-commit"
    
    if not run_command(f"{precommit_path} install"):
        return False
    
    print("✅ Pre-commit hooks installed")
    return True


def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    print("⚙️ Setting up environment configuration...")
    
    if not Path(".env").exists():
        if Path(".env.example").exists():
            # Copy .env.example to .env
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                dst.write(src.read())
            print("✅ Created .env file from .env.example")
            print("⚠️  Please edit .env file with your actual configuration values")
        else:
            print("❌ .env.example file not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True


def create_directories():
    """Create necessary directories"""
    print("📁 Creating project directories...")
    
    directories = [
        "logs",
        "uploads",
        "tests",
        "src",
        "credentials",
        "frontend",
        "nginx"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Project directories created")
    return True


def check_docker():
    """Check if Docker is available"""
    print("🐳 Checking Docker availability...")
    
    if run_command("docker --version"):
        print("✅ Docker is available")
        if run_command("docker-compose --version"):
            print("✅ Docker Compose is available")
            return True
        else:
            print("⚠️  Docker Compose not found, but Docker is available")
            return True
    else:
        print("⚠️  Docker not found - you can still develop without it")
        return True


def initialize_database():
    """Initialize database with Docker if available"""
    print("🗄️ Initializing database...")
    
    if run_command("docker-compose up -d postgres redis"):
        print("✅ Database services started with Docker")
        # Wait a moment for services to start
        import time
        time.sleep(5)
        return True
    else:
        print("⚠️  Could not start database with Docker")
        print("   Please ensure PostgreSQL and Redis are running manually")
        return True


def run_initial_tests():
    """Run initial tests to verify setup"""
    print("🧪 Running initial tests...")
    
    # Determine python path based on OS
    if os.name == 'nt':  # Windows
        python_path = ".venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_path = ".venv/bin/python"
    
    # Run a simple import test
    test_command = f"{python_path} -c \"import discord; import fastapi; import redis; print('✅ Core imports successful')\""
    
    if run_command(test_command):
        print("✅ Initial tests passed")
        return True
    else:
        print("⚠️  Some imports failed - check your installation")
        return True


def main():
    """Main setup function"""
    print("🚀 Discord Task Management Bot - Development Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup steps
    steps = [
        ("Virtual Environment", setup_virtual_environment),
        ("Dependencies", install_dependencies),
        ("Pre-commit Hooks", setup_pre_commit),
        ("Environment Config", create_env_file),
        ("Project Directories", create_directories),
        ("Docker Check", check_docker),
        ("Database Init", initialize_database),
        ("Initial Tests", run_initial_tests),
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}")
        print("-" * 30)
        if not step_func():
            failed_steps.append(step_name)
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 Setup Summary")
    print("=" * 50)
    
    if not failed_steps:
        print("✅ All setup steps completed successfully!")
        print("\n🚀 Next steps:")
        print("1. Edit .env file with your configuration")
        print("2. Start the Discord bot: python bot_main.py")
        print("3. Start the web API: uvicorn src.main:app --reload")
        print("4. Visit http://localhost:8000/docs for API documentation")
    else:
        print(f"⚠️  Setup completed with {len(failed_steps)} warnings:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\nYou may need to address these manually.")
    
    print("\n📚 Development Commands:")
    print("- Run tests: pytest")
    print("- Format code: black .")
    print("- Sort imports: isort .")
    print("- Type check: mypy cogs utils src")
    print("- Start services: docker-compose up -d")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
A2A Agent System Manager
Start all agents and services with a single command.
Press CTRL+C to stop all services cleanly.
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from typing import List, Dict, Optional

# ANSI color codes
class Color:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

# Project paths
PROJECT_ROOT = Path(__file__).parent.absolute()
A2A_ROOT = PROJECT_ROOT / "A2A-Framework"
DEMO_ROOT = PROJECT_ROOT / "demo-frontend"

# Service configurations
SERVICES = [
    {
        "name": "Referral Agent",
        "emoji": "🏥",
        "dir": A2A_ROOT / "referral_agent",
        "command": ["uv", "run", "."],
        "port": 10004,
        "wait": 8,
    },
    {
        "name": "Scheduling Agent",
        "emoji": "📅",
        "dir": A2A_ROOT / "scheduling_agent",
        "command": ["uv", "run", "."],
        "port": 10005,
        "wait": 8,
    },
    {
        "name": "Messaging Agent",
        "emoji": "💬",
        "dir": A2A_ROOT / "messaging_agent",
        "command": ["uv", "run", "."],
        "port": 10003,
        "wait": 8,
    },
    {
        "name": "Host Agent API",
        "emoji": "🤖",
        "dir": A2A_ROOT / "host_agent",
        "command": ["python3", "api_server.py"],
        "port": 8084,
        "wait": 10,
    },
    {
        "name": "Demo Backend",
        "emoji": "🔧",
        "dir": DEMO_ROOT / "backend",
        "command": ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        "port": 8000,
        "wait": 3,
    },
    {
        "name": "Demo Frontend",
        "emoji": "🌐",
        "dir": DEMO_ROOT / "frontend",
        "command": ["npm", "run", "dev", "--", "--host"],
        "port": 3000,
        "wait": 3,
    },
]

# Global list to track running processes
processes: List[subprocess.Popen] = []
shutdown_requested = False


def print_header():
    """Print startup header"""
    print(f"\n{Color.BLUE}{'='*60}{Color.NC}")
    print(f"{Color.BLUE}       A2A Agent System - Starting All Services{Color.NC}")
    print(f"{Color.BLUE}{'='*60}{Color.NC}\n")


def print_service_status(emoji: str, name: str, status: str, color: str, details: str = ""):
    """Print formatted service status"""
    status_text = f"{color}{status}{Color.NC}"
    print(f"{emoji} {name:20} {status_text}", end="")
    if details:
        print(f" {Color.CYAN}{details}{Color.NC}")
    else:
        print()


def check_port_available(port: int) -> bool:
    """Check if a port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0


def start_service(service: Dict) -> Optional[subprocess.Popen]:
    """Start a service and return the process"""
    name = service['name']
    emoji = service['emoji']
    directory = service['dir']
    command = service['command']
    port = service['port']

    print_service_status(emoji, name, "Starting...", Color.YELLOW)

    # Check if port is already in use
    if not check_port_available(port):
        print_service_status(emoji, name, "❌ FAILED", Color.RED,
                           f"Port {port} already in use")
        return None

    try:
        # Start the process
        process = subprocess.Popen(
            command,
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # Create new process group for clean shutdown
        )

        # Wait a bit for process to start
        time.sleep(1)

        # Check if process is still running
        if process.poll() is not None:
            print_service_status(emoji, name, "❌ FAILED", Color.RED,
                               "Process died immediately")
            return None

        print_service_status(emoji, name, "✅ RUNNING", Color.GREEN,
                           f"PID: {process.pid}, Port: {port}")
        return process

    except FileNotFoundError:
        print_service_status(emoji, name, "❌ FAILED", Color.RED,
                           f"Command not found: {command[0]}")
        return None
    except Exception as e:
        print_service_status(emoji, name, "❌ FAILED", Color.RED, str(e))
        return None


def shutdown_services(signum=None, frame=None):
    """Shutdown all services gracefully"""
    global shutdown_requested

    if shutdown_requested:
        return

    shutdown_requested = True

    print(f"\n\n{Color.YELLOW}{'='*60}{Color.NC}")
    print(f"{Color.YELLOW}       Shutting down all services...{Color.NC}")
    print(f"{Color.YELLOW}{'='*60}{Color.NC}\n")

    # Shutdown in reverse order
    for process, service in reversed(list(zip(processes, SERVICES))):
        if process and process.poll() is None:
            name = service['name']
            emoji = service['emoji']
            print_service_status(emoji, name, "Stopping...", Color.YELLOW)

            try:
                # Try graceful shutdown first
                process.terminate()

                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print_service_status(emoji, name, "✅ STOPPED", Color.GREEN)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    process.kill()
                    process.wait()
                    print_service_status(emoji, name, "⚠️  FORCE KILLED", Color.YELLOW)

            except Exception as e:
                print_service_status(emoji, name, "❌ ERROR", Color.RED, str(e))

    print(f"\n{Color.GREEN}{'='*60}{Color.NC}")
    print(f"{Color.GREEN}       All services stopped{Color.NC}")
    print(f"{Color.GREEN}{'='*60}{Color.NC}\n")

    sys.exit(0)


def monitor_services():
    """Monitor running services and handle their output"""
    print(f"\n{Color.BLUE}{'='*60}{Color.NC}")
    print(f"{Color.GREEN}       ✅ All services started successfully!{Color.NC}")
    print(f"{Color.BLUE}{'='*60}{Color.NC}\n")

    print(f"{Color.CYAN}Service URLs:{Color.NC}")
    for service in SERVICES:
        emoji = service['emoji']
        name = service['name']
        port = service['port']
        print(f"  {emoji} {name:20} http://localhost:{port}")

    print(f"\n{Color.YELLOW}Press CTRL+C to stop all services{Color.NC}\n")

    # Monitor processes
    try:
        while True:
            time.sleep(2)

            # Check if any process died unexpectedly
            for process, service in zip(processes, SERVICES):
                if process and process.poll() is not None:
                    name = service['name']
                    emoji = service['emoji']
                    returncode = process.returncode

                    if returncode != 0:
                        print(f"\n{Color.RED}❌ {emoji} {name} died unexpectedly (exit code: {returncode}){Color.NC}")
                        print(f"{Color.YELLOW}Shutting down all services...{Color.NC}\n")
                        shutdown_services()
                        return

    except KeyboardInterrupt:
        # CTRL+C pressed
        shutdown_services()


def main():
    """Main entry point"""
    global processes

    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, shutdown_services)
    signal.signal(signal.SIGTERM, shutdown_services)

    print_header()

    # Check if required directories exist
    if not A2A_ROOT.exists():
        print(f"{Color.RED}❌ A2A-Framework directory not found: {A2A_ROOT}{Color.NC}")
        sys.exit(1)

    if not DEMO_ROOT.exists():
        print(f"{Color.RED}❌ demo-frontend directory not found: {DEMO_ROOT}{Color.NC}")
        sys.exit(1)

    # Start all services
    for service in SERVICES:
        process = start_service(service)
        processes.append(process)

        # Wait for service to stabilize
        if process:
            time.sleep(service.get('wait', 2))

    # Check if any critical services failed
    if all(p is None for p in processes):
        print(f"\n{Color.RED}❌ All services failed to start{Color.NC}\n")
        sys.exit(1)

    # Monitor services
    monitor_services()


if __name__ == "__main__":
    main()
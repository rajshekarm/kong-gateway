"""
Utility functions for Kong deployment (Ubuntu + Docker Compose v2)
"""
import secrets
import string
import subprocess
import sys
import time
from typing import Dict, Optional


def generate_strong_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
# -----------------------------
# Core command runner
# -----------------------------
def run_command(
    cmd: list,
    env: Optional[Dict] = None,
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run shell command with structured logging and error handling
    """
    try:
        print(f"🔧 Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            env=env,
            check=check,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(result.stdout.strip())

        if result.stderr:
            print(result.stderr.strip())

        return result

    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        if e.stdout:
            print(e.stdout.strip())
        if e.stderr:
            print(e.stderr.strip())

        if check:
            sys.exit(1)

        return e


# -----------------------------
# Docker checks
# -----------------------------
def check_docker() -> bool:
    """
    Check if Docker is installed and usable by the current user
    """
    try:
        run_command(['docker', '--version'], check=True)

        result = run_command(['docker', 'ps'], check=False)
        if result.returncode != 0:
            print("⚠️ Docker is installed but permission denied")
            print("💡 Fix by running:")
            print("   sudo usermod -aG docker $USER")
            print("   logout & login again OR run: newgrp docker")
            return False

        print("✅ Docker is installed and running")
        return True

    except Exception:
        print("❌ Docker is not installed")
        return False


def check_docker_compose() -> bool:
    """
    Check if Docker Compose v2 is installed
    """
    try:
        run_command(['docker', 'compose', 'version'], check=True)
        print("✅ Docker Compose v2 is available")
        return True
    except Exception:
        print("❌ Docker Compose v2 is not installed")
        print("💡 Install with:")
        print("   sudo apt update && sudo apt install docker-compose-plugin -y")
        return False


# -----------------------------
# Kong helpers
# -----------------------------
def get_kong_container_id() -> Optional[str]:
    """
    Get the running Kong container ID
    """
    try:
        container_id = subprocess.check_output(
            ['docker', 'ps', '-qf', 'name=kong'],
            text=True
        ).strip()

        if not container_id:
            return None

        return container_id

    except Exception:
        return None

import requests
def health_check(max_attempts=30):
    for _ in range(max_attempts):
        result = subprocess.run(
            ["docker", "exec", "kong", "kong", "status"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True
        time.sleep(2)
    return False



def get_kong_logs(lines: int = 50):
    """
    Fetch Kong container logs safely
    """
    container_id = get_kong_container_id()

    if not container_id:
        print("❌ Kong container is not running")
        return

    print(f"📋 Kong logs (last {lines} lines):")
    run_command(
        ['docker', 'logs', '--tail', str(lines), container_id],
        check=False
    )

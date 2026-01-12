#!/usr/bin/env python3
"""
Bootstrap PostgreSQL for Kong Gateway (EC2 + Docker)

RESPONSIBILITIES:
- Install Docker & Docker Compose
- Start PostgreSQL container
- Wait for PostgreSQL readiness
- Verify DB connectivity

DOES NOT:
- Run Kong
- Run migrations
"""

import os
import sys
import time
import argparse
import subprocess

from secret_manager import KongSecretsManager
from config import config
from utils import check_docker, check_docker_compose, run_command


POSTGRES_CONTAINER = "kong-postgres"


# -----------------------------
# Dependency Installation
# -----------------------------

def install_dependencies():
    print("📦 Installing system dependencies...")

    commands = [
        ['sudo', 'apt-get', 'update'],
        ['sudo', 'apt-get', 'install', '-y',
         'docker.io', 'jq', 'postgresql-client'],
        ['sudo', 'systemctl', 'start', 'docker'],
        ['sudo', 'systemctl', 'enable', 'docker'],
        ['sudo', 'usermod', '-aG', 'docker', 'ubuntu'],
    ]

    for cmd in commands:
        run_command(cmd)

    print("✅ Dependencies installed")
    print("💡 Logout/login may be required for Docker group permissions")


def install_docker_compose():
    print("📦 Installing Docker Compose...")

    import platform
    system = platform.system()
    machine = platform.machine()

    run_command([
        'sudo', 'curl', '-L',
        f'https://github.com/docker/compose/releases/latest/download/docker-compose-{system}-{machine}',
        '-o', '/usr/local/bin/docker-compose'
    ])

    run_command(['sudo', 'chmod', '+x', '/usr/local/bin/docker-compose'])
    run_command(['sudo', 'ln', '-sf', '/usr/local/bin/docker-compose', '/usr/bin/docker-compose'], check=False)

    print("✅ Docker Compose installed")


# -----------------------------
# PostgreSQL Lifecycle
# -----------------------------

def start_postgres_container(secret):
    print("🐘 Starting PostgreSQL container...")

    # Check if container already exists
    result = subprocess.run(
        ['docker', 'ps', '-a', '--format', '{{.Names}}'],
        capture_output=True, text=True
    )

    if POSTGRES_CONTAINER in result.stdout:
        print("ℹ️ PostgreSQL container already exists")
        run_command(['docker', 'start', POSTGRES_CONTAINER], check=False)
        return

    run_command([
        'docker', 'run', '-d',
        '--name', POSTGRES_CONTAINER,
        '-p', f"{secret['port']}:5432",
        '-e', f"POSTGRES_USER={secret['username']}",
        '-e', f"POSTGRES_PASSWORD={secret['password']}",
        '-e', f"POSTGRES_DB={secret['dbname']}",
        '-v', 'kong-postgres-data:/var/lib/postgresql/data',
        'postgres:13'
    ])

    print("✅ PostgreSQL container started")


def wait_for_postgres(secret, timeout=60):
    print("⏳ Waiting for PostgreSQL to become ready...")

    start = time.time()

    while time.time() - start < timeout:
        result = subprocess.run(
            [
                'docker', 'exec', POSTGRES_CONTAINER,
                'pg_isready',
                '-U', secret['username']
            ],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ PostgreSQL is ready")
            return True

        time.sleep(2)

    print("❌ PostgreSQL did not become ready in time")
    return False


def verify_db_connectivity(secret):
    print("🔍 Verifying database connectivity...")

    cmd = [
        'docker', 'exec', POSTGRES_CONTAINER,
        'psql',
        '-U', secret['username'],
        '-d', secret['dbname'],
        '-c', 'SELECT 1;'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Database connectivity verified")
        return True

    print("❌ Database connectivity failed")
    print(result.stderr)
    return False


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Bootstrap PostgreSQL for Kong")
    parser.add_argument('--skip-dependencies', action='store_true')
    args = parser.parse_args()

    print("🚀 Starting PostgreSQL bootstrap")
    print("=" * 50)

    if not args.skip_dependencies:
        install_dependencies()
        install_docker_compose()

    if not check_docker():
        print("❌ Docker is not running")
        sys.exit(1)

    if not check_docker_compose():
        print("❌ Docker Compose not available")
        sys.exit(1)

    manager = KongSecretsManager(region=config.aws.region)
    secret = manager.get_secret(config.aws.secret_name)

    start_postgres_container(secret)

    if not wait_for_postgres(secret):
        sys.exit(1)

    if not verify_db_connectivity(secret):
        sys.exit(1)

    print("\n✅ PostgreSQL setup completed successfully")
    print("Next:")
    print("  python3 deploy.py start")


if __name__ == "__main__":
    main()

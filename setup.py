#!/usr/bin/env python3
"""
Bootstrap & initialize Kong Gateway on AWS EC2 (Ubuntu)

PRECONDITIONS:
- RDS PostgreSQL instance already exists
- Secrets Manager secret already exists (created by provision.py)
- EC2 has network access to RDS
"""

import sys
import argparse
import subprocess
from secrets_manager import KongSecretsManager
from config import config
from utils import check_docker, check_docker_compose, run_command


# -----------------------------
# Dependency Installation
# -----------------------------

def install_dependencies():
    print("📦 Installing system dependencies...")

    commands = [
        ['sudo', 'apt-get', 'update'],
        ['sudo', 'apt-get', 'install', '-y',
         'docker.io', 'jq', 'postgresql-client', 'wget'],
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
# Secret & RDS Validation
# -----------------------------

def ensure_secret_exists():
    print("🔐 Verifying Secrets Manager secret...")

    manager = KongSecretsManager(region=config.aws.region)

    try:
        secret = manager.get_secret(config.aws.secret_name)
        required_keys = {'username', 'password', 'host', 'port', 'dbname'}

        if not required_keys.issubset(secret.keys()):
            print("❌ Secret is missing required fields")
            sys.exit(1)

        print("✅ Secret found and valid")
        return secret

    except Exception as e:
        print(f"❌ Secret not found: {config.aws.secret_name}")
        print("💡 Run provision.py first")
        sys.exit(1)

def verify_db_connectivity(secret):
    print("🔍 Verifying database connectivity...")

    cmd = [
        'docker', 'run', '--rm', 'postgres:13',
        'psql',
        f"postgresql://{secret['username']}:{secret['password']}@"
        f"{secret['host']}:{secret['port']}/postgres",
        '-c', 'SELECT 1;'
    ]


def verify_rds_connectivity(secret):
    print("🔍 Verifying RDS connectivity...")

    cmd = [
        'docker', 'run', '--rm', 'postgres:13',
        'psql',
        f"postgresql://{secret['username']}:{secret['password']}@"
        f"{secret['host']}:{secret['port']}/postgres?sslmode=require",
        '-c', 'SELECT 1;'
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print("❌ Cannot connect to RDS")
            print(result.stderr)
            return False

        print("✅ RDS connectivity verified")
        return True

    except subprocess.TimeoutExpired:
        print("❌ Connection timeout")
        return False


# -----------------------------
# Database Initialization
# -----------------------------

def create_kong_database(secret):
    print("🗄️ Ensuring Kong database exists...")

    check_cmd = [
        'docker', 'run', '--rm', 'postgres:13',
        'psql',
        f"postgresql://{secret['username']}:{secret['password']}@"
        f"{secret['host']}:{secret['port']}/postgres",
        '-tAc', "SELECT 1 FROM pg_database WHERE datname='kong'"
    ]

    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if '1' in result.stdout:
        print("✅ Kong database already exists")
        return True

    create_cmd = [
        'docker', 'run', '--rm', 'postgres:13',
        'psql',
        f"postgresql://{secret['username']}:{secret['password']}@"
        f"{secret['host']}:{secret['port']}/postgres?sslmode=require",
        '-c', f"CREATE DATABASE kong OWNER {secret['username']}"
    ]

    result = subprocess.run(create_cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Kong database created")
        return True

    print("❌ Failed to create Kong database")
    print(result.stderr)
    return False


# -----------------------------
# Filesystem Setup
# -----------------------------

def setup_kong_directory():
    import os
    import shutil

    print(f"📁 Preparing Kong directory: {config.kong.working_dir}")
    os.makedirs(config.kong.working_dir, exist_ok=True)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir == config.kong.working_dir:
        return

    for file in [
        'docker-compose.yml',
        'config.py',
        'deploy.py',
        'secrets_manager.py',
        'utils.py',
        'requirements.txt'
    ]:
        src = os.path.join(current_dir, file)
        dst = os.path.join(config.kong.working_dir, file)

        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"📄 Copied {file}")


def download_rds_certificate():
    print("📥 Downloading RDS CA certificate...")
    run_command([
        'wget', '-q',
        'https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem',
        '-O', f'{config.kong.working_dir}/rds-ca.pem'
    ])
    print("✅ RDS certificate downloaded")


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Setup Kong Gateway")
    parser.add_argument('--skip-dependencies', action='store_true')
    parser.add_argument('--skip-db-creation', action='store_true')
    args = parser.parse_args()

    print("🚀 Starting Kong Gateway Setup")
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

    setup_kong_directory()

    secret = ensure_secret_exists()

    if not verify_db_connectivity(secret):
        print("❌ RDS connectivity failed")
        sys.exit(1)

    if not args.skip_db_creation:
        if not create_kong_database(secret):
            sys.exit(1)

    # download_rds_certificate()

    print("\n✅ Setup completed successfully")
    print("Next:")
    print(f"  cd {config.kong.working_dir}")
    print("  python3 deploy.py start")


if __name__ == "__main__":
    main()

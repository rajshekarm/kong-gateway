#!/usr/bin/env python3
"""
Deploy Kong Gateway (Ubuntu, Docker Compose v2, CI/CD safe)
"""

import os
import sys
import argparse

from secret_manager import KongSecretsManager
from config import config
from utils import (
    check_docker,
    check_docker_compose,
    run_command,
    health_check,
    get_kong_logs
)


# -----------------------------
# Database migrations
# -----------------------------
def run_migrations(credentials: dict):
    """
    Run Kong database migrations 
    """
    print("🔄 Running Kong migrations...")

    cmd = [
        'docker', 'run', '--rm',
        '-e', 'KONG_DATABASE=postgres',
        '-e', f"KONG_PG_HOST=10.0.0.13",
        '-e', f"KONG_PG_PORT={credentials['port']}",
        '-e', f"KONG_PG_USER={credentials['username']}",
        '-e', f"KONG_PG_PASSWORD={credentials['password']}",
        '-e', f"KONG_PG_DATABASE={credentials['dbname']}",
        # '-e', 'KONG_PG_SSL=on',
        # '-e', 'KONG_PG_SSL_VERIFY=on',
        # '-e', 'KONG_PG_SSL_CERT=/etc/ssl/certs/rds-ca.pem',
        # '-v', f'{config.kong.working_dir}/rds-ca.pem:/etc/ssl/certs/rds-ca.pem:ro',
        config.kong.kong_image,
        'sh', '-c',
        'kong migrations bootstrap'
    ]

    run_command(cmd)
    print("✅ Migrations completed")


# -----------------------------
# Kong lifecycle
# -----------------------------
def start_kong(credentials: dict):
    print("🚀 Starting Kong Gateway...")

    env = os.environ.copy()
    env.update({
        'POSTGRES_HOST': credentials['host'],
        'POSTGRES_PORT': str(credentials['port']),
        'POSTGRES_USER': credentials['username'],
        'POSTGRES_PASSWORD': credentials['password'],
        'POSTGRES_DB': credentials['dbname']
    })

    os.chdir(config.kong.working_dir)
    run_command(['docker', 'compose', 'up', '-d'], env=env)
    print("✅ Kong started")


def stop_kong():
    print("🛑 Stopping Kong...")
    os.chdir(config.kong.working_dir)
    run_command(['docker', 'compose', 'down', '--timeout', '30'], check=False)
    print("✅ Kong stopped")


def restart_kong(credentials: dict):
    print("🔄 Restarting Kong...")
    stop_kong()
    start_kong(credentials)


# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description='Deploy Kong Gateway')
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'restart', 'status', 'logs'],
        help='Action to perform'
    )
    parser.add_argument(
        '--skip-migrations',
        action='store_true',
        help='Skip database migrations'
    )
    parser.add_argument(
        '--log-lines',
        type=int,
        default=50,
        help='Number of log lines to show'
    )

    args = parser.parse_args()

    try:
        if args.action != 'logs':
            if not check_docker() or not check_docker_compose():
                print("❌ Docker or Docker Compose not available")
                sys.exit(1)

        manager = KongSecretsManager(region=config.aws.region)

        if args.action in ['start', 'restart']:
            credentials = manager.get_secret(config.aws.secret_name)

            if not args.skip_migrations:
                run_migrations(credentials)

            start_kong(credentials)

            if not health_check():
                print("❌ Kong failed health check — rolling back")
                get_kong_logs(args.log_lines)
                stop_kong()
                sys.exit(1)

            print("\n✅ Kong deployment successful!")

        elif args.action == 'stop':
            stop_kong()

        elif args.action == 'status':
            os.chdir(config.kong.working_dir)
            run_command(['docker', 'compose', 'ps'], check=False)
            health_check(max_attempts=1)

        elif args.action == 'logs':
            get_kong_logs(args.log_lines)

    except KeyboardInterrupt:
        print("\n⚠️ Deployment interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

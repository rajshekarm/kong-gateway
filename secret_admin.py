#!/usr/bin/env python3
"""
⚠️  ADMIN TOOL — DO NOT IMPORT ⚠️

Kong AWS Secrets Admin
----------------------------------
This script is for MANUAL, OPERATOR-DRIVEN secret management.

It is NOT safe for runtime usage.
It MUST NOT be imported by setup.py or deploy.py.

Use cases:
- Initial secret creation (post-RDS provisioning)
- Manual password rotation
- Emergency secret updates
- Secret cleanup

Run only during maintenance windows.
"""

import boto3
import json
import secrets
import string
import argparse
import sys
import time
from botocore.exceptions import ClientError


class KongSecretsAdmin:
    def __init__(self, region: str):
        self.secrets_client = boto3.client("secretsmanager", region_name=region)
        self.rds_client = boto3.client("rds", region_name=region)
        self.region = region

    # -----------------------------
    # Password generation
    # -----------------------------
    @staticmethod
    def generate_strong_password(length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    # -----------------------------
    # Secret helpers
    # -----------------------------
    def secret_exists(self, secret_name: str) -> bool:
        try:
            self.secrets_client.describe_secret(SecretId=secret_name)
            return True
        except self.secrets_client.exceptions.ResourceNotFoundException:
            return False

    # -----------------------------
    # Create secret (SAFE)
    # -----------------------------
    def create_secret(
        self,
        secret_name: str,
        db_instance_id: str,
        username: str,
        dbname: str
    ):
        """
        Create secret ONLY IF IT DOES NOT EXIST.
        Password is generated ONCE and stored.
        """

        if self.secret_exists(secret_name):
            print(f"⚠️  Secret already exists: {secret_name}")
            print("❌ Creation aborted to prevent credential drift")
            return

        print(f"🔍 Discovering RDS endpoint for {db_instance_id}...")
        rds = self.rds_client.describe_db_instances(
            DBInstanceIdentifier=db_instance_id
        )["DBInstances"][0]

        password = self.generate_strong_password()

        payload = {
            "username": username,
            "password": password,
            "host": rds["Endpoint"]["Address"],
            "port": rds["Endpoint"]["Port"],
            "dbname": dbname,
            "engine": "postgres",
        }

        print(f"🔐 Creating secret: {secret_name}")
        self.secrets_client.create_secret(
            Name=secret_name,
            Description=f"Kong PostgreSQL credentials ({db_instance_id})",
            SecretString=json.dumps(payload),
            Tags=[
                {"Key": "Application", "Value": "Kong"},
                {"Key": "ManagedBy", "Value": "secrets_admin.py"},
            ],
        )

        print("✅ Secret created successfully")
        print("⚠️  Ensure DB user password matches this secret")

    # -----------------------------
    # Rotate password (DANGEROUS)
    # -----------------------------
    def rotate_password(self, secret_name: str, db_instance_id: str):
        """
        Rotate password in RDS AND Secrets Manager.
        This WILL break Kong until it is restarted.
        """

        confirm = input(
            "⚠️  This will rotate the DB password and restart is required.\n"
            "Type ROTATE to continue: "
        )
        if confirm != "ROTATE":
            print("❌ Rotation aborted")
            return

        secret = self.get_secret(secret_name)
        new_password = self.generate_strong_password()

        print("1/3 Updating RDS password...")
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            MasterUserPassword=new_password,
            ApplyImmediately=True,
        )

        print("⏳ Waiting for RDS to apply password (30s)...")
        time.sleep(30)

        print("2/3 Updating secret...")
        secret["password"] = new_password
        self.secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret),
        )

        print("3/3 Rotation complete")
        print("⚠️  Restart Kong to apply new credentials")

    # -----------------------------
    # Read-only helpers
    # -----------------------------
    def get_secret(self, secret_name: str) -> dict:
        response = self.secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])

    def list_secrets(self, name_filter: str = "kong"):
        response = self.secrets_client.list_secrets(
            Filters=[{"Key": "name", "Values": [name_filter]}]
        )

        if not response["SecretList"]:
            print("No secrets found")
            return

        print(f"\n{'Name':<40} {'Created':<25}")
        print("=" * 70)
        for s in response["SecretList"]:
            print(f"{s['Name']:<40} {s['CreatedDate']}")

    def delete_secret(self, secret_name: str, recovery_days: int = 30):
        confirm = input(
            f"⚠️  Delete secret {secret_name}? Type DELETE to confirm: "
        )
        if confirm != "DELETE":
            print("❌ Deletion aborted")
            return

        self.secrets_client.delete_secret(
            SecretId=secret_name,
            RecoveryWindowInDays=recovery_days,
        )
        print("🗑️ Secret scheduled for deletion")


# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="⚠️ Kong Secrets Admin (Manual Use Only)"
    )

    parser.add_argument("action", choices=["create", "get", "rotate", "delete", "list"])
    parser.add_argument("--secret", required=True)
    parser.add_argument("--db-instance")
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--username", default="kong")
    parser.add_argument("--dbname", default="kong")

    args = parser.parse_args()
    admin = KongSecretsAdmin(region=args.region)

    try:
        if args.action == "create":
            if not args.db_instance:
                sys.exit("❌ --db-instance required")
            admin.create_secret(
                args.secret, args.db_instance, args.username, args.dbname
            )

        elif args.action == "get":
            secret = admin.get_secret(args.secret)
            print(json.dumps(secret, indent=2))

        elif args.action == "rotate":
            if not args.db_instance:
                sys.exit("❌ --db-instance required")
            admin.rotate_password(args.secret, args.db_instance)

        elif args.action == "delete":
            admin.delete_secret(args.secret)

        elif args.action == "list":
            admin.list_secrets()

    except Exception as e:
        print(f"❌ Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

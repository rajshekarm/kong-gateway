#!/usr/bin/env python3
"""
Provision RDS PostgreSQL and Secrets Manager secret for Kong
"""

import json
import time
import boto3
from botocore.exceptions import ClientError
from config import config
from utils import generate_strong_password


rds = boto3.client("rds", region_name=config.aws.region)
secrets = boto3.client("secretsmanager", region_name=config.aws.region)


# def rds_exists(db_instance_id):
#     try:
#         rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
#         return True
#     except rds.exceptions.DBInstanceNotFoundFault:
#         return False


# def wait_for_rds(db_instance_id):
#     print("⏳ Waiting for RDS to become available...")
#     waiter = rds.get_waiter("db_instance_available")
#     waiter.wait(DBInstanceIdentifier=db_instance_id)
#     print(" RDS is available")


# def create_rds(db_instance_id, password):
#     print(f" Creating RDS instance {db_instance_id}...")

#     rds.create_db_instance(
#         DBInstanceIdentifier=db_instance_id,
#         Engine="postgres",
#         DBInstanceClass=config.rds.instance_class,
#         AllocatedStorage=config.rds.storage,
#         MasterUsername=config.rds.username,
#         MasterUserPassword=password,
#         VpcSecurityGroupIds=[config.rds.security_group_id],
#         DBSubnetGroupName=config.rds.subnet_group,
#         BackupRetentionPeriod=0,
#         PubliclyAccessible=False,
#         StorageEncrypted=True,
#         DeletionProtection=True,
#     )


def secret_exists(secret_name):
    try:
        secrets.describe_secret(SecretId=secret_name)
        return True
    except secrets.exceptions.ResourceNotFoundException:
        return False


def create_initial_secret(db_instance_id, password):
    """
    SAFE & IDEMPOTENT:
    - Creates secret ONLY if missing
    - Never regenerates credentials
    """

    if secret_exists(config.aws.secret_name):
        print(f" Secret already exists: {config.aws.secret_name}")
        return

    # rds_info = rds.describe_db_instances(
    #     DBInstanceIdentifier=db_instance_id
    # )["DBInstances"][0]

    secret_payload = {
        "username": "kong",
        "password": "kong",
        "host": "10.0.0.153",
        "port": 5432,
        "dbname": "kong",
        "engine": "postgres",
    }

    secrets.create_secret(
        Name=config.aws.secret_name,
        SecretString=json.dumps(secret_payload),
        Description="Kong PostgreSQL credentials",
    )

    print(f"🔐 Secret created: {config.aws.secret_name}")


def main():
    db_instance_id = config.rds.instance_id

    # if rds_exists(db_instance_id):
    #     print(f" RDS already exists: {db_instance_id}")
    #     wait_for_rds(db_instance_id)
    #     return

    password = generate_strong_password()

    # create_rds(db_instance_id, password)
    # wait_for_rds(db_instance_id)
    create_initial_secret(db_instance_id, password)


if __name__ == "__main__":
    main()

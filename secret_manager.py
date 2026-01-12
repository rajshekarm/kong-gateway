"""
Kong Secrets Manager (READ-ONLY)
Safe for runtime and automation
"""

import boto3
import json
from botocore.exceptions import ClientError


class KongSecretsManager:
    def __init__(self, region):
        self.client = boto3.client("secretsmanager", region_name=region)

    def get_secret(self, secret_name):
        response = self.client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])

    def secret_exists(self, secret_name):
        try:
            self.client.describe_secret(SecretId=secret_name)
            return True
        except self.client.exceptions.ResourceNotFoundException:
            return False

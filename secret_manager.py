"""
Kong Secrets Manager (READ-ONLY)
Safe for runtime and automation
"""

import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError


class KongSecretsManager:
    def __init__(self, region: str):
        self.region = region
        self.client = boto3.client("secretsmanager", region_name=region)

        print(f"🔐 Secrets Manager initialized")
        print(f"   Region: {region}")

    def get_secret(self, secret_name: str):
        print(f"🔍 Fetching secret: {secret_name}")

        try:
            print(f"requesting secrets for ", secret_name)
            response = self.client.get_secret_value(SecretId=secret_name)

            print("✅ Secret retrieved successfully")
            print(f"   Version ID: {response.get('VersionId', 'unknown')}")

            secret = json.loads(response["SecretString"])

            # Print ONLY keys, never values
            print(f"   Fields present: {list(secret.keys())}")

            return secret

        except self.client.exceptions.ResourceNotFoundException:
            print("❌ Secret not found")
            print(f"   Name: {secret_name}")
            print("💡 Check secret name and region")
            raise

        except self.client.exceptions.AccessDeniedException:
            print("❌ Access denied when reading secret")
            print("💡 Check IAM role permissions:")
            print("   secretsmanager:GetSecretValue")
            raise

        except NoCredentialsError:
            print("❌ AWS credentials not found")
            print("💡 Is this running on an EC2 with IAM role attached?")
            raise

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"❌ AWS ClientError: {error_code}")
            print(f"   Message: {e.response['Error'].get('Message')}")
            raise

        except json.JSONDecodeError:
            print("❌ SecretString is not valid JSON")
            raise

        except Exception as e:
            print(f"❌ Unexpected error while fetching secret: {e}")
            raise

    def secret_exists(self, secret_name: str) -> bool:
        print(f"🔍 Checking if secret exists: {secret_name}")

        try:
            self.client.describe_secret(SecretId=secret_name)
            print("✅ Secret exists")
            return True

        except self.client.exceptions.ResourceNotFoundException:
            print("❌ Secret does not exist")
            return False

        except self.client.exceptions.AccessDeniedException:
            print("❌ Access denied when checking secret existence")
            return False

        except ClientError as e:
            print(f"❌ AWS error while checking secret: {e}")
            return False

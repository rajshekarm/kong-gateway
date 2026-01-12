"""
Kong Gateway Configuration
"""

import os
from dataclasses import dataclass, field


# -----------------------------
# AWS / Secrets
# -----------------------------

@dataclass
class AWSConfig:
    region: str = os.getenv("AWS_REGION", "us-east-2")
    secret_name: str = os.getenv("SECRET_NAME", "kong/db-credentials")


# -----------------------------
# RDS (Provisioning phase only)
# -----------------------------

@dataclass
@dataclass
class RDSConfig:
    # TEMPORARY: hardcoded for single-env setup
    instance_id: str = "kong-postgres"
    username: str = "kong"
    instance_class: str = "db.t3.micro"
    storage: int = 20
    subnet_group: str = "kong-db-subnet-group"
    security_group_id: str = "sg-0abc123456789def"



# -----------------------------
# Kong Runtime
# -----------------------------

@dataclass
class KongConfig:
    compose_file: str = "docker-compose.yml"
    kong_image: str = os.getenv("KONG_IMAGE", "kong:3.6")
    working_dir: str = os.getenv("KONG_WORKING_DIR", "/opt/kong")


# -----------------------------
# Global config
# -----------------------------

@dataclass
class Config:
    aws: AWSConfig = field(default_factory=AWSConfig)
    rds: RDSConfig = field(default_factory=RDSConfig)
    kong: KongConfig = field(default_factory=KongConfig)


config = Config()

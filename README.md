# Kong Gateway on AWS EC2

This project provides a **production-ready setup for running Kong Gateway on AWS EC2**, with secure secrets management and fully automated deployments.

The solution uses **Docker**, **AWS Secrets Manager**, and **GitHub Actions with AWS Systems Manager (SSM)** to deploy and operate Kong without SSH access or hard-coded credentials.

---

## Architecture Overview

- Kong Gateway runs inside Docker on an Ubuntu EC2 instance  
- Amazon RDS (PostgreSQL) stores Kong configuration and state  
- AWS Secrets Manager securely stores database credentials  
- GitHub Actions triggers deployments on every push to `main`  
- AWS Systems Manager (SSM) executes deployment commands on EC2  
- Kong Admin API is restricted to localhost for security  

High-level flow:

```
Client → (ALB) → Kong Gateway (EC2 / Docker) → RDS
                   ↑
             GitHub Actions → AWS SSM
```

---

## Repository Structure

```
.
├── setup.py              # One-time EC2 bootstrap (Docker, certs, secrets)
├── deploy.py             # Safe, repeatable Kong deployment script
├── docker-compose.yml    # Kong service definition
├── utils.py              # Shared utilities (Docker, health checks)
├── secrets_manager.py    # AWS Secrets Manager integration
├── config.py             # Centralized configuration
└── .github/workflows/    # GitHub Actions deployment pipeline
```

---

## Deployment Workflow

### Initial Setup (One Time on EC2)

Run once after provisioning the EC2 instance:

```bash
python3 setup.py --db-instance <rds-instance-id>
```

This step installs system dependencies, configures Docker, downloads the RDS TLS certificate, and initializes secrets in AWS Secrets Manager.

> After setup, log out and log back in to apply Docker group permissions.

---

### Automated Deployments

- Push changes to the `main` branch  
- GitHub Actions pipeline is triggered automatically  
- GitHub Actions sends deployment commands via AWS Systems Manager (SSM)  
- The EC2 instance pulls the latest code and runs `deploy.py`  

No SSH access is required for deployments.

---

### Kong Startup Process

During deployment:

- Database migrations run safely and idempotently  
- Kong starts using Docker Compose  
- Health checks verify Kong readiness  
- The deployment fails and rolls back if health checks do not pass  

---

## AWS Systems Manager (SSM)

AWS Systems Manager (SSM) is used as the secure execution channel for deployments.

Instead of using SSH:
- GitHub Actions sends a **Run Command** request to SSM  
- The SSM Agent on the EC2 instance executes deployment commands locally  
- Command output and status are returned to GitHub Actions  

### Benefits of Using SSM

- No open SSH ports on the EC2 instance  
- No SSH key management or rotation  
- IAM-based access control  
- Encrypted communication  
- Full audit trail of executed commands  

---

## Security Highlights

- No secrets stored in GitHub or source code  
- AWS IAM + OIDC authentication for CI/CD  
- No SSH access required to the instance  
- Encrypted database connections (TLS)  
- Kong Admin API not exposed publicly  
- Minimal network and attack surface  

---

## Requirements

- Ubuntu EC2 instance  
- Docker and Docker Compose v2  
- Amazon RDS (PostgreSQL)  
- AWS IAM role with access to:
  - AWS Secrets Manager  
  - AWS Systems Manager (SSM)  
- GitHub repository with Actions enabled  

---

## Status

- Production-ready  
- Fully automated  
- Secure by default  

---

## Notes

This setup is intentionally simple and avoids Kubernetes complexity, making it suitable for small to medium workloads that require a reliable and secure API gateway deployment.

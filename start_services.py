#!/usr/bin/env python3
"""
start_services.py

A comprehensive setup script that automatically handles:
1. Environment setup and secret generation
2. Supabase initialization
3. Service configuration
4. Container management
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import secrets
import string
import jwt
from datetime import datetime, timedelta
from cloudflare_setup import main as setup_cloudflare
import random
from typing import List, Dict
from pathlib import Path

def print_banner():
    banner = r"""
    ██╗      ██████╗  ██████╗ █████╗ ██╗         █████╗ ██╗
    ██║     ██╔═══██╗██╔════╝██╔══██╗██║        ██╔══██╗██║
    ██║     ██║   ██║██║     ███████║██║        ███████║██║
    ██║     ██║   ██║██║     ██╔══██║██║        ██╔══██║██║
    ███████╗╚██████╔╝╚██████╗██║  ██║███████╗   ██║  ██║██║
    ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝  ╚═╝╚═╝
    ============================================================
    [  SYSTEM INITIALIZATION SEQUENCE - v2.0.24.ALPHA  ]
    ============================================================
    """
    print("\033[32m" + banner + "\033[0m")

def print_status(message, status="OK"):
    status_colors = {
        "OK": "\033[32m",     # Green
        "ERROR": "\033[31m",  # Red
        "WARN": "\033[33m",   # Yellow
        "INFO": "\033[36m"    # Cyan
    }
    color = status_colors.get(status, "\033[37m")  # Default to white
    print(f"{color}[{status}]\033[0m {message}")

def print_section(title):
    print(f"\n\033[35m{'=' * 60}\033[0m")
    print(f"\033[35m[  {title}  ]\033[0m")
    print(f"\033[35m{'=' * 60}\033[0m\n")

def print_matrix_line():
    chars = "░▒▓█"
    line = "".join(random.choice(chars) for _ in range(60))
    print(f"\033[32m{line}\033[0m")

def generate_random_string(length, exclude_chars='@<>&\'"'):
    """Generate a cryptographically secure random string of specified length."""
    letters = string.ascii_letters
    digits = string.digits
    symbols = ''.join(c for c in string.punctuation if c not in exclude_chars)
    all_chars = letters + digits + symbols
    
    while True:
        password = ''.join(secrets.choice(all_chars) for _ in range(length))
        if (any(c in letters for c in password) and
            any(c in digits for c in password) and
            any(c in symbols for c in password)):
            return password

def generate_jwt_token(secret_key, role):
    """Generate a JWT token for Supabase authentication."""
    payload = {
        "role": role,
        "iss": "supabase",
        "iat": int(datetime.now().timestamp()),
        "exp": int((datetime.now() + timedelta(days=365 * 10)).timestamp())
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

def generate_secret(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_secure_string(length: int = 32) -> str:
    """Generate a secure random string."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret() -> str:
    """Generate a secure JWT secret."""
    return secrets.token_urlsafe(32)

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

def create_env_file():
    """Create a .env file with secure random values."""
    env_vars = {
        # System Configuration
        'tmp': '/tmp',

        # Postgres Configuration
        'POSTGRES_PASSWORD': generate_secure_string(16),
        'POSTGRES_USER': 'postgres',
        'POSTGRES_DB': 'postgres',
        'POSTGRES_HOST': 'db',
        'POSTGRES_PORT': '5432',

        # Redis Configuration
        'REDIS_HOST': 'redis',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': generate_secure_string(16),

        # Supabase Configuration
        'SUPABASE_DB_HOST': 'db',
        'SUPABASE_DB_PORT': '5432',
        'SUPABASE_DB_NAME': 'postgres',
        'SUPABASE_DB_USER': 'postgres',
        'SUPABASE_DB_PASSWORD': generate_secure_string(16),

        # Supabase Secrets
        'JWT_SECRET': generate_jwt_secret(),
        'ANON_KEY': f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlLWRlbW8iLCJpYXQiOjE2NDE3NjkyMDAsImV4cCI6MTc5OTUzNTYwMH0.{generate_secure_string(32)}",
        'SERVICE_ROLE_KEY': f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UtZGVtbyIsImlhdCI6MTY0MTc2OTIwMCwiZXhwIjoxNzk5NTM1NjAwfQ.{generate_secure_string(32)}",
        'DASHBOARD_USERNAME': 'supabase',
        'DASHBOARD_PASSWORD': generate_secure_string(16),
        'POOLER_TENANT_ID': '1000',

        # Supavisor Configuration
        'POOLER_PROXY_PORT_TRANSACTION': '6543',
        'POOLER_DEFAULT_POOL_SIZE': '20',
        'POOLER_MAX_CLIENT_CONN': '100',
        'SECRET_KEY_BASE': generate_secure_string(64),
        'VAULT_ENC_KEY': generate_secure_string(32),

        # API Proxy Configuration
        'KONG_HTTP_PORT': '8000',
        'KONG_HTTPS_PORT': '8443',

        # API Configuration
        'PGRST_DB_SCHEMAS': 'public,storage,graphql_public',

        # Auth Configuration
        'SITE_URL': 'http://localhost:3000',
        'ADDITIONAL_REDIRECT_URLS': '',
        'JWT_EXPIRY': '3600',
        'DISABLE_SIGNUP': 'false',
        'API_EXTERNAL_URL': 'http://localhost:8000',

        # Mailer Configuration
        'MAILER_URLPATHS_CONFIRMATION': '/auth/v1/verify',
        'MAILER_URLPATHS_INVITE': '/auth/v1/verify',
        'MAILER_URLPATHS_RECOVERY': '/auth/v1/verify',
        'MAILER_URLPATHS_EMAIL_CHANGE': '/auth/v1/verify',

        # Email Configuration
        'ENABLE_EMAIL_SIGNUP': 'true',
        'ENABLE_EMAIL_AUTOCONFIRM': 'false',
        'SMTP_ADMIN_EMAIL': 'admin@example.com',
        'SMTP_HOST': 'supabase-mail',
        'SMTP_PORT': '2500',
        'SMTP_USER': generate_secure_string(16),
        'SMTP_PASS': generate_secure_string(16),
        'SMTP_SENDER_NAME': 'Local AI System',
        'ENABLE_ANONYMOUS_USERS': 'false',

        # Phone Configuration
        'ENABLE_PHONE_SIGNUP': 'true',
        'ENABLE_PHONE_AUTOCONFIRM': 'true',

        # Studio Configuration
        'STUDIO_DEFAULT_ORGANIZATION': 'Default Organization',
        'STUDIO_DEFAULT_PROJECT': 'Default Project',
        'STUDIO_PORT': '3000',
        'SUPABASE_PUBLIC_URL': 'http://localhost:8000',
        'IMGPROXY_ENABLE_WEBP_DETECTION': 'true',

        # Functions Configuration
        'FUNCTIONS_VERIFY_JWT': 'false',

        # Logs Configuration
        'LOGFLARE_LOGGER_BACKEND_API_KEY': generate_secure_string(32),
        'LOGFLARE_API_KEY': generate_secure_string(32),
        'DOCKER_SOCKET_LOCATION': '/var/run/docker.sock',

        # N8N Configuration
        'N8N_BASIC_AUTH_USER': 'admin',
        'N8N_BASIC_AUTH_PASSWORD': generate_secure_string(16),
        'N8N_ENCRYPTION_KEY': generate_secure_string(32),
        'N8N_HOST': 'http://localhost:5678',
        'N8N_PORT': '5678',
        'N8N_PROTOCOL': 'http',
        'N8N_SSL_CERT': '',
        'N8N_SSL_KEY': '',
        'N8N_USER_MANAGEMENT_JWT_SECRET': generate_secure_string(32),

        # Flowise Configuration
        'FLOWISE_USERNAME': 'admin',
        'FLOWISE_PASSWORD': generate_secure_string(16),
        'FLOWISE_PORT': '3001',

        # SearXNG Configuration
        'SEARXNG_SECRET': generate_secure_string(32)
    }

    # Create .env file in root directory
    with open('.env', 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    # Create supabase/docker directory if it doesn't exist
    os.makedirs('supabase/docker', exist_ok=True)

    # Copy .env file to supabase/docker/.env
    shutil.copy2('.env', 'supabase/docker/.env')

    print_status("Created .env file with secure random values", "OK")
    print_status("Copied .env file to supabase/docker/.env", "OK")

def setup_environment():
    """Set up the environment variables and clone Supabase repository."""
    print_status("Setting up environment...", "INFO")
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        create_env_file()
    else:
        # If .env exists, ensure it's copied to supabase/docker/.env
        os.makedirs('supabase/docker', exist_ok=True)
        shutil.copy2('.env', 'supabase/docker/.env')
        print_status("Updated supabase/docker/.env with current values", "OK")
    
    # Clone Supabase repository if it doesn't exist
    if not os.path.exists('supabase'):
        print_status("Cloning Supabase repository...", "INFO")
        subprocess.run(['git', 'clone', 'https://github.com/supabase/supabase.git'], check=True)
        print_status("Supabase repository cloned successfully", "OK")
    else:
        print_status("Supabase repository already exists", "INFO")

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def clone_supabase():
    print("Cloning the Supabase repository...")
    if not os.path.exists("supabase"):
        commands = [
            "git clone --filter=blob:none --no-checkout https://github.com/supabase/supabase.git",
            "cd supabase && git sparse-checkout init --cone",
            "cd supabase && git sparse-checkout set docker",
            "cd supabase && git checkout master"
        ]
        for cmd in commands:
            print(f"Running: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
        
        # Copy .env file to supabase/docker/.env
        print("Copying .env to supabase/docker/.env...")
        shutil.copy2(".env", "supabase/docker/.env")

def prepare_supabase_env():
    """Copy .env to Supabase docker directory."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env to supabase/docker/.env...")
    shutil.copyfile(env_example_path, env_path)

def setup_searxng():
    print("Setting up SearXNG...")
    searxng_dir = "searxng-data"
    if not os.path.exists(searxng_dir):
        os.makedirs(searxng_dir)
        settings_file = os.path.join(searxng_dir, "settings.yml")
        if not os.path.exists(settings_file):
            with open(settings_file, "w") as f:
                f.write(f"server:\n  secret_key: {generate_secret()}\n")
            print("SearXNG settings created.")
    else:
        print("SearXNG settings already exist.")

def setup_cloudflared() -> bool:
    print("\nWould you like to use Cloudflare Tunnels for secure access? (y/N)")
    print("This will allow secure access to your services without managing DNS records.")
    choice = input().lower()
    
    if choice != 'y':
        return False
    
    print("\nPlease provide the following Cloudflare information:\n")
    
    # Get Cloudflare information
    tunnel_token = input("1. Cloudflare Tunnel token (from Zero Trust dashboard):\n")
    api_token = input("\n2. Cloudflare API token (with Tunnel:Edit and DNS:Edit permissions):\n")
    account_id = input("\n3. Cloudflare Account ID (found in the dashboard URL):\n")
    domain = input("\n4. Your domain name (e.g., example.com):\n")
    
    # Update .env file with Cloudflare information
    with open(".env", "a") as f:
        f.write(f"\nCLOUDFLARED_TUNNEL_TOKEN={tunnel_token}\n")
        f.write(f"CLOUDFLARE_API_TOKEN={api_token}\n")
        f.write(f"CLOUDFLARE_ACCOUNT_ID={account_id}\n")
        f.write(f"DOMAIN={domain}\n")
    
    # Copy updated .env to supabase/docker/.env
    shutil.copy2(".env", "supabase/docker/.env")
    
    print("\nCloudflare configuration completed successfully.")
    print("The following hostnames will be configured:")
    print(f"- n8n.{domain}")
    print(f"- webui.{domain}")
    print(f"- flowise.{domain}")
    print(f"- ollama.{domain}")
    print(f"- searxng.{domain}")
    
    return True

def stop_existing_containers():
    """Stop and remove existing containers."""
    print("Stopping existing containers...")
    try:
        run_command([
            "docker", "compose",
            "-p", "localai",
            "-f", "docker-compose.yml",
            "-f", "supabase/docker/docker-compose.yml",
            "down"
        ])
    except subprocess.CalledProcessError:
        print("No existing containers to stop.")

def select_services() -> Dict[str, bool]:
    services = {
        "Supabase (Database & Vector Store)": True,
        "N8N (Workflow Automation)": True,
        "Open WebUI (Chat Interface)": True,
        "Flowise (Visual Programming)": True,
        "Qdrant (Vector Database)": True,
        "Redis (Cache)": True,
        "SearXNG (Search Engine)": True,
        "Ollama (Local LLM)": True,
        "Cloudflared (Secure Access)": False
    }
    
    print_section("SERVICE INITIALIZATION MATRIX")
    print("\033[36mSelect services to activate in the neural matrix:\033[0m")
    print("\033[37m[ENTER] to accept default state | [y/n] to toggle\033[0m\n")
    
    for service, default in services.items():
        default_str = "\033[32m[ACTIVE]\033[0m" if default else "\033[31m[INACTIVE]\033[0m"
        choice = input(f"\033[33m▶\033[0m {service} {default_str}: ").lower()
        print_matrix_line()
        
        if choice == '':
            continue
        elif choice in ['y', 'yes']:
            services[service] = True
        elif choice in ['n', 'no']:
            services[service] = False
    
    return services

def start_services(selected_services: Dict[str, bool], use_cloudflare: bool = False) -> None:
    """Start the selected services with proper environment variables."""
    try:
        # Ensure .env file exists and copy it to supabase/docker/.env
        if os.path.exists('.env'):
            shutil.copy2('.env', 'supabase/docker/.env')
        else:
            print("[ERROR] .env file not found. Please run the script again to generate it.")
            return False

        # Stop existing containers first
        try:
            subprocess.run(['docker', 'compose', '-p', 'localai', 'down'], check=True)
        except subprocess.CalledProcessError:
            pass  # Ignore errors if no containers are running

        # Start Supabase services first if selected
        if 'supabase' in selected_services:
            print("[INFO] Activating quantum database matrix...")
            try:
                # Set environment variables explicitly
                env = os.environ.copy()
                env.update({
                    'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
                    'LOGFLARE_API_KEY': os.getenv('LOGFLARE_API_KEY', ''),
                    'LOGFLARE_SOURCE_ID': os.getenv('LOGFLARE_SOURCE_ID', ''),
                    'tmp': '/tmp'  # Add the missing tmp variable
                })
                
                # Start Supabase services
                result = subprocess.run(
                    ['docker', 'compose', '-p', 'localai', '-f', 'supabase/docker/docker-compose.yml', 'up', '-d', 'db'],
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Database initialization fault: {e.stderr}")
                print("[WARN] Continuing with backup protocols...")

        # Start other services
        print("[INFO] Launching AI core systems...")
        services_to_start = []
        for service in selected_services:
            if service != 'supabase':
                print(f"[INFO] Activating {service.title()}...")
                services_to_start.append(service)

        if services_to_start:
            try:
                # Set environment variables explicitly
                env = os.environ.copy()
                env.update({
                    'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
                    'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD', 'redis'),
                    'tmp': '/tmp'  # Add the missing tmp variable
                })
                
                # Build the docker compose command
                cmd = ['docker', 'compose', '-p', 'localai', '-f', 'docker-compose.yml', 'up', '-d']
                cmd.extend(services_to_start)
                
                result = subprocess.run(
                    cmd,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Critical system failure: {e.stderr}")
                return False

        return True
    except Exception as e:
        print(f"[ERROR] System initialization failed: {str(e)}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import jwt
    except ImportError:
        print("Installing required Python packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyJWT", "cryptography"], check=True)

def main():
    print_banner()
    parser = argparse.ArgumentParser(description='Initialize the local AI neural matrix.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Neural processing unit selection (default: cpu)')
    args = parser.parse_args()

    print_section("SYSTEM DIAGNOSTICS")
    check_dependencies()
    
    if not os.path.exists(".env"):
        print_status("Generating quantum encryption keys...", "INFO")
        setup_environment()
    
    print_status("Establishing neural links...", "INFO")
    clone_supabase()
    prepare_supabase_env()
    
    print_status("Configuring search matrix...", "INFO")
    setup_searxng()
    
    use_cloudflared = setup_cloudflared()
    
    selected_services = select_services()
    start_services(selected_services, use_cloudflared)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[31m[ABORT] Neural matrix shutdown initiated...\033[0m")
        sys.exit(1)
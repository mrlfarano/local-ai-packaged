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

def setup_environment() -> None:
    print("Setting up environment variables...")
    env_file = ".env"
    
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write(f"POSTGRES_PASSWORD={generate_secret()}\n")
            f.write(f"JWT_SECRET={generate_secret()}\n")
            f.write(f"ANON_KEY={generate_secret()}\n")
            f.write(f"SERVICE_ROLE_KEY={generate_secret()}\n")
            f.write(f"DASHBOARD_USERNAME=admin\n")
            f.write(f"DASHBOARD_PASSWORD={generate_secret()}\n")
            f.write(f"REDIS_PASSWORD={generate_secret()}\n")
            f.write(f"N8N_BASIC_AUTH_USER=admin\n")
            f.write(f"N8N_BASIC_AUTH_PASSWORD=admin123\n")
            f.write(f"N8N_ENCRYPTION_KEY={generate_secret()}\n")
            f.write(f"FLOWISE_USERNAME=admin\n")
            f.write(f"FLOWISE_PASSWORD=admin123\n")
    
    print("Environment setup complete with secure secrets.")

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
    print_section("NEURAL NETWORK INITIALIZATION")
    print_status("Terminating existing neural pathways...", "INFO")
    subprocess.run(
        "docker compose -p localai -f docker-compose.yml -f supabase/docker/docker-compose.yml down",
        shell=True
    )

    if selected_services["Supabase (Database & Vector Store)"]:
        print_status("Activating quantum database matrix...", "INFO")
        try:
            subprocess.run(
                "docker compose -p localai -f supabase/docker/docker-compose.yml up -d db",
                shell=True,
                check=True
            )
            print_status("Neural pathways stabilizing...", "INFO")
            time.sleep(5)
        except subprocess.CalledProcessError as e:
            print_status(f"Database initialization fault: {e}", "ERROR")
            print_status("Continuing with backup protocols...", "WARN")

    print_status("Launching AI core systems...", "INFO")
    cmd = ["docker", "compose", "-p", "localai"]
    
    if selected_services["Ollama (Local LLM)"]:
        cmd.extend(["--profile", "cpu"])
        print_status("CPU neural network engaged", "INFO")
    
    if use_cloudflare and selected_services["Cloudflared (Secure Access)"]:
        cmd.extend(["--profile", "cloudflared"])
        print_status("Quantum tunneling protocols activated", "INFO")
    
    cmd.extend(["-f", "docker-compose.yml", "up", "-d"])
    
    selected = []
    service_map = {
        "N8N (Workflow Automation)": "n8n",
        "Open WebUI (Chat Interface)": "open-webui",
        "Flowise (Visual Programming)": "flowise",
        "Qdrant (Vector Database)": "qdrant",
        "Redis (Cache)": "redis",
        "SearXNG (Search Engine)": "searxng"
    }
    
    for service_name, container_name in service_map.items():
        if selected_services[service_name]:
            selected.append(container_name)
            print_status(f"Activating {service_name}", "INFO")
    
    if selected:
        cmd.extend(selected)
    
    try:
        subprocess.run(cmd, check=True)
        print_section("SYSTEM ONLINE")
        print("\033[32mNeural matrix successfully initialized!\033[0m")
        print("\n\033[36mAccess points activated:\033[0m")
        print("\033[37m╔════════════════════════════════════════╗")
        print("║  N8N        ➜  http://localhost:5678   ║")
        print("║  Open WebUI ➜  http://localhost:3000   ║")
        print("║  Flowise   ➜  http://localhost:3001   ║")
        print("║  Qdrant    ➜  http://localhost:6333   ║")
        print("║  SearXNG   ➜  http://localhost:8080   ║")
        print("║  Ollama    ➜  http://localhost:11434  ║")
        print("╚════════════════════════════════════════╝\033[0m")
    except subprocess.CalledProcessError as e:
        print_status(f"Critical system failure: {e}", "ERROR")

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
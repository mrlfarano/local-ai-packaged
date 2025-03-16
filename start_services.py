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

def setup_environment():
    """Set up the environment with secure secrets."""
    print("Setting up environment variables...")
    
    if not os.path.exists(".env.example"):
        print("Error: .env.example file not found!")
        sys.exit(1)

    with open(".env.example", "r") as f:
        template = f.read()
    
    # Generate secrets
    secrets_dict = {
        "N8N_ENCRYPTION_KEY": generate_random_string(32),
        "N8N_USER_MANAGEMENT_JWT_SECRET": generate_random_string(32),
        "POSTGRES_PASSWORD": generate_random_string(48),
        "JWT_SECRET": generate_random_string(64),
        "DASHBOARD_USERNAME": "admin",
        "DASHBOARD_PASSWORD": generate_random_string(32),
        "POOLER_TENANT_ID": str(secrets.randbelow(9000) + 1000),
        "SECRET_KEY_BASE": generate_random_string(64),
        "VAULT_ENC_KEY": generate_random_string(32),
        "LOGFLARE_LOGGER_BACKEND_API_KEY": generate_random_string(48),
        "LOGFLARE_API_KEY": generate_random_string(48)
    }
    
    # Generate Supabase tokens
    jwt_secret = secrets_dict["JWT_SECRET"]
    secrets_dict["ANON_KEY"] = generate_jwt_token(jwt_secret, "anon")
    secrets_dict["SERVICE_ROLE_KEY"] = generate_jwt_token(jwt_secret, "service_role")
    
    # Replace values in template
    output_content = template
    for key, value in secrets_dict.items():
        key_loc = output_content.find(f"{key}=")
        if key_loc != -1:
            line_end = output_content.find("\n", key_loc)
            if line_end == -1:
                line_end = len(output_content)
            line_start = key_loc + len(key) + 1
            output_content = output_content[:line_start] + value + output_content[line_end:]
    
    with open(".env", "w") as f:
        f.write(output_content)
    
    print("Environment setup complete with secure secrets.")

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")

def prepare_supabase_env():
    """Copy .env to Supabase docker directory."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env to supabase/docker/.env...")
    shutil.copyfile(env_example_path, env_path)

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG."""
    print("Setting up SearXNG...")
    try:
        if not os.path.exists("searxng"):
            os.makedirs("searxng")
        
        settings_path = os.path.join("searxng", "settings.yml")
        if not os.path.exists(settings_path):
            secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            with open(settings_path, "w") as f:
                f.write(f"server:\n    secret_key: {secret_key}\n")
            print("Generated SearXNG secret key.")
            return secret_key
        else:
            print("SearXNG settings already exist.")
            return None
    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        return None

def setup_cloudflared():
    """Configure Cloudflare Tunnel if requested."""
    print("\nWould you like to use Cloudflare Tunnels for secure access? (y/N)")
    print("This will allow secure access to your services without managing DNS records.")
    response = input().strip().lower()
    if response == 'y' or response == 'yes':
        print("\nPlease provide the following Cloudflare information:")
        print("\n1. Cloudflare Tunnel token (from Zero Trust dashboard):")
        tunnel_token = input().strip()
        
        print("\n2. Cloudflare API token (with Tunnel:Edit and DNS:Edit permissions):")
        api_token = input().strip()
        
        print("\n3. Cloudflare Account ID (found in the dashboard URL):")
        account_id = input().strip()
        
        print("\n4. Your domain name (e.g., example.com):")
        domain = input().strip()
        
        if all([tunnel_token, api_token, account_id, domain]):
            with open(".env", "r") as f:
                content = f.read()
            
            # Update all Cloudflare-related variables
            replacements = {
                "CLOUDFLARED_TUNNEL_TOKEN=": f"CLOUDFLARED_TUNNEL_TOKEN={tunnel_token}",
                "CLOUDFLARE_API_TOKEN=": f"CLOUDFLARE_API_TOKEN={api_token}",
                "CLOUDFLARE_ACCOUNT_ID=": f"CLOUDFLARE_ACCOUNT_ID={account_id}",
                "CLOUDFLARE_DOMAIN=": f"CLOUDFLARE_DOMAIN={domain}"
            }
            
            for key, value in replacements.items():
                if key in content:
                    content = content.replace(key + content.split(key)[1].split("\n")[0], value)
                else:
                    content += f"\n{value}"
            
            with open(".env", "w") as f:
                f.write(content)
            
            print("\nCloudflare configuration completed successfully.")
            print("The following hostnames will be configured:")
            print(f"- n8n.{domain}")
            print(f"- webui.{domain}")
            print(f"- flowise.{domain}")
            print(f"- ollama.{domain}")
            print(f"- searxng.{domain}")
            return True
        else:
            print("\nError: All Cloudflare information is required. Skipping Cloudflare setup.")
    return False

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

def start_services(profile=None, use_cloudflared=False):
    """Start all services with the specified profile."""
    print("Starting services...")
    
    # Start Supabase services first
    try:
        print("Starting Supabase database...")
        run_command([
            "docker", "compose", "-p", "localai",
            "-f", "supabase/docker/docker-compose.yml",
            "up", "-d", "db"  # Start only db first
        ])
        
        print("Waiting for database to initialize...")
        time.sleep(15)  # Give the database time to initialize
        
        print("Starting remaining Supabase services...")
        run_command([
            "docker", "compose", "-p", "localai",
            "-f", "supabase/docker/docker-compose.yml",
            "up", "-d"  # Now start all remaining services
        ])
        
        print("Waiting for Supabase services to stabilize...")
        time.sleep(10)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Error starting Supabase services: {e}")
        print("Continuing with other services...")
    
    # Start local AI services
    try:
        print("Starting local AI services...")
        cmd = ["docker", "compose", "-p", "localai"]
        if profile and profile != "none":
            cmd.extend(["--profile", profile])
        if use_cloudflared:
            cmd.extend(["--profile", "cloudflared"])
        cmd.extend(["-f", "docker-compose.yml", "up", "-d"])
        run_command(cmd)
        
        print("Waiting for services to initialize...")
        time.sleep(10)
        
        # Check service health
        run_command(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"])
        
    except subprocess.CalledProcessError as e:
        print(f"Error starting local AI services: {e}")
        sys.exit(1)

    # After starting services, set up Cloudflare tunnel hostnames
    if use_cloudflared:
        print("\nSetting up Cloudflare tunnel hostnames...")
        setup_cloudflare()

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import jwt
    except ImportError:
        print("Installing required Python packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyJWT", "cryptography"], check=True)

def main():
    parser = argparse.ArgumentParser(description='Set up and start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)')
    args = parser.parse_args()

    # Check dependencies
    check_dependencies()
    
    # Setup environment and generate secrets
    if not os.path.exists(".env"):
        setup_environment()
    
    # Clone and prepare Supabase
    clone_supabase_repo()
    prepare_supabase_env()
    
    # Generate SearXNG secret key
    generate_searxng_secret_key()
    
    # Setup Cloudflared if requested
    use_cloudflared = setup_cloudflared()
    
    # Stop any existing containers
    stop_existing_containers()
    
    # Start all services
    start_services(args.profile, use_cloudflared)
    
    print("\n🎉 Setup complete! Your services are now starting.")
    
    if use_cloudflared:
        # Get domain from .env file
        with open(".env", "r") as f:
            content = f.read()
            domain = next((line.split("=")[1].strip() for line in content.split("\n") 
                         if line.startswith("CLOUDFLARE_DOMAIN=")), None)
        if domain:
            print("\nYour services will be available at:")
            print(f"- n8n: https://n8n.{domain}")
            print(f"- Open WebUI: https://webui.{domain}")
            print(f"- Flowise: https://flowise.{domain}")
            print(f"- Ollama: https://ollama.{domain}")
            print(f"- SearXNG: https://searxng.{domain}")
            print("\nNote: It may take a few minutes for the Cloudflare Tunnel to become active.")
            print("You can monitor the tunnel status in the Cloudflare Zero Trust dashboard.")
    else:
        print("\nAccess your services at:")
        print("- n8n: http://localhost:5678")
        print("- Open WebUI: http://localhost:3000")
        print("- Flowise: http://localhost:3001")
        print("- SearXNG: http://localhost:8080")

if __name__ == "__main__":
    main()
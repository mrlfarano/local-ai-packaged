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
    
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")
    
    if not os.path.exists(settings_base_path):
        print("Warning: SearXNG base settings file not found.")
        return
    
    if not os.path.exists(settings_path):
        shutil.copyfile(settings_base_path, settings_path)
    
    system = platform.system()
    try:
        if system == "Windows":
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
            ]
            subprocess.run(ps_command, check=True)
        else:
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "" if system == "Darwin" else None, f"s|ultrasecretkey|{random_key}|g", settings_path]
            if system == "Darwin":
                subprocess.run(sed_cmd, check=True)
            else:
                subprocess.run(sed_cmd[:-1], check=True)
    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")

def setup_cloudflared():
    """Configure Cloudflare Tunnel if requested."""
    print("\nWould you like to use Cloudflare Tunnels for secure access? (y/N)")
    print("This will allow secure access to your services without managing DNS records.")
    if input().lower() == 'y':
        print("\nPlease enter your Cloudflare Tunnel token (from Zero Trust dashboard):")
        token = input().strip()
        if token:
            with open(".env", "r") as f:
                content = f.read()
            if "CLOUDFLARED_TUNNEL_TOKEN=" in content:
                content = content.replace("CLOUDFLARED_TUNNEL_TOKEN=", f"CLOUDFLARED_TUNNEL_TOKEN={token}")
            else:
                content += f"\nCLOUDFLARED_TUNNEL_TOKEN={token}\n"
            with open(".env", "w") as f:
                f.write(content)
            print("Cloudflare Tunnel token configured successfully.")
            return True
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
    
    # Start Supabase
    run_command([
        "docker", "compose", "-p", "localai",
        "-f", "supabase/docker/docker-compose.yml",
        "up", "-d"
    ])
    
    print("Waiting for Supabase to initialize...")
    time.sleep(10)
    
    # Start local AI services
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    if use_cloudflared:
        cmd.extend(["--profile", "cloudflared"])
    cmd.extend(["-f", "docker-compose.yml", "up", "-d"])
    run_command(cmd)

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
    print("\nAccess your services at:")
    print("- n8n: http://localhost:5678")
    print("- Open WebUI: http://localhost:3000")
    print("- Flowise: http://localhost:3001")
    print("- SearXNG: http://localhost:8080")
    if use_cloudflared:
        print("\nNote: Configure your Cloudflare Tunnel public hostnames in the Zero Trust dashboard.")

if __name__ == "__main__":
    main()
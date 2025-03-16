import os
import shutil
import subprocess
from pathlib import Path

def run_command(cmd):
    """Run a shell command and print output."""
    print(f"\nExecuting: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error executing command: {e}")
        return False

def cleanup():
    """Clean up all resources created by the project."""
    print("🧹 Starting cleanup process...")
    
    # Get the current directory
    current_dir = Path.cwd()
    
    # 1. Stop and remove all Docker containers
    print("\n1. Stopping and removing Docker containers...")
    run_command("docker compose -f docker-compose.yml down -v")
    run_command("docker compose -f supabase/docker/docker-compose.yml down -v")
    
    # 2. Remove all Docker volumes
    print("\n2. Removing Docker volumes...")
    run_command("docker volume prune -f")
    
    # 3. Remove all Docker networks
    print("\n3. Removing Docker networks...")
    run_command("docker network prune -f")
    
    # 4. Remove specific directories
    print("\n4. Removing project directories...")
    dirs_to_remove = [
        "supabase",
        "n8n-data",
        "ollama-data",
        "flowise-data",
        "webui-data",
        "searxng-data",
        "__pycache__"
    ]
    
    for dir_name in dirs_to_remove:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            print(f"Removing {dir_path}")
            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                print(f"Error removing {dir_path}: {e}")
    
    # 5. Remove specific files
    print("\n5. Removing configuration files...")
    files_to_remove = [
        ".env",
        "cloudflared.exe",
        "cloudflared"
    ]
    
    for file_name in files_to_remove:
        file_path = current_dir / file_name
        if file_path.exists():
            print(f"Removing {file_path}")
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
    
    print("\n🧹 Cleanup complete! You can now start fresh with 'python start_services.py'")

if __name__ == "__main__":
    # Ask for confirmation
    print("⚠️  WARNING: This will destroy all local data, containers, and configurations.")
    print("Are you sure you want to proceed? (y/N)")
    
    if input().lower() == 'y':
        cleanup()
    else:
        print("Cleanup cancelled.") 
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
    
    # 1. Force stop all containers first
    print("\n1. Force stopping all containers...")
    run_command("docker ps -q | xargs -r docker stop -t 0")
    run_command("docker ps -a -q | xargs -r docker rm -f")
    
    # 2. Stop and remove all Docker containers
    print("\n2. Removing Docker compose services...")
    run_command("docker compose -f docker-compose.yml down -v --remove-orphans")
    if os.path.exists("supabase/docker/docker-compose.yml"):
        run_command("docker compose -f supabase/docker/docker-compose.yml down -v --remove-orphans")
    
    # 3. Remove all Docker volumes
    print("\n3. Removing Docker volumes...")
    run_command("docker volume ls -q | xargs -r docker volume rm -f")
    run_command("docker volume prune -f")
    
    # 4. Remove all Docker networks
    print("\n4. Removing Docker networks...")
    run_command("docker network prune -f")
    
    # 5. Remove specific directories
    print("\n5. Removing project directories...")
    dirs_to_remove = [
        "supabase",
        "n8n-data",
        "ollama-data",
        "flowise-data",
        "webui-data",
        "searxng-data",
        "__pycache__",
        "shared",
        "n8n",
        "n8n-tool-workflows"
    ]
    
    for dir_name in dirs_to_remove:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            print(f"Removing {dir_path}")
            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                print(f"Error removing {dir_path}: {e}")
                # Try with force remove if normal remove fails
                run_command(f"rm -rf {dir_path}")
    
    # 6. Remove specific files
    print("\n6. Removing configuration files...")
    files_to_remove = [
        ".env",
        "cloudflared.exe",
        "cloudflared",
        ".env.example",
        "docker-compose.yml",
        "Caddyfile"
    ]
    
    for file_name in files_to_remove:
        file_path = current_dir / file_name
        if file_path.exists():
            print(f"Removing {file_path}")
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing {file_path}: {e}")
                # Try with force remove if normal remove fails
                run_command(f"rm -f {file_path}")
    
    # 7. Final cleanup
    print("\n7. Final cleanup...")
    run_command("docker system prune -f")
    
    print("\n🧹 Cleanup complete! You can now start fresh with:")
    print("1. git pull  # to get the latest files")
    print("2. python start_services.py --profile cpu")

if __name__ == "__main__":
    # Ask for confirmation
    print("⚠️  WARNING: This will destroy all local data, containers, and configurations.")
    print("This includes:")
    print("- All running containers")
    print("- All Docker volumes and networks")
    print("- All local configuration files")
    print("- All service data directories")
    print("\nAre you sure you want to proceed? (y/N)")
    
    if input().lower() == 'y':
        cleanup()
    else:
        print("Cleanup cancelled.") 
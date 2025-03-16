import os
import requests
import json
from typing import List, Dict
from dotenv import load_dotenv

def get_cloudflare_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_tunnel_id_from_token(token: str) -> str:
    """Extract tunnel ID from the token."""
    try:
        token_parts = token.split('.')
        if len(token_parts) != 3:
            raise ValueError("Invalid token format")
        
        payload = json.loads(token_parts[1] + '=' * (-len(token_parts[1]) % 4))
        return payload.get('t', '')
    except Exception as e:
        print(f"Error extracting tunnel ID: {e}")
        return ''

def setup_tunnel_hostnames(account_id: str, tunnel_id: str, api_token: str, domain: str, services: List[Dict[str, str]]):
    """
    Set up Cloudflare Tunnel hostnames for each service.
    
    Args:
        account_id: Cloudflare account ID
        tunnel_id: Tunnel ID
        api_token: Cloudflare API token
        domain: Base domain for the services
        services: List of service configurations [{"name": "n8n", "port": "5678"}, ...]
    """
    base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/tunnels/{tunnel_id}/configurations"
    
    # Prepare the configuration
    config = {
        "config": {
            "ingress": []
        }
    }

    # Add service configurations
    for service in services:
        service_name = service["name"]
        service_port = service["port"]
        hostname = f"{service_name}.{domain}"
        
        ingress_rule = {
            "hostname": hostname,
            "service": f"http://localhost:{service_port}",
            "originRequest": {
                "noTLSVerify": True
            }
        }
        config["config"]["ingress"].append(ingress_rule)
    
    # Add catch-all rule
    config["config"]["ingress"].append({"service": "http_status:404"})

    # Update tunnel configuration
    headers = get_cloudflare_headers(api_token)
    response = requests.put(base_url, headers=headers, json=config)
    
    if response.status_code == 200:
        print("Successfully configured tunnel hostnames:")
        for service in services:
            print(f"- {service['name']}.{domain}")
    else:
        print(f"Error configuring tunnel: {response.status_code}")
        print(response.text)

def main():
    load_dotenv()
    
    # Get configuration from environment
    tunnel_token = os.getenv('CLOUDFLARED_TUNNEL_TOKEN')
    api_token = os.getenv('CLOUDFLARE_API_TOKEN')
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    domain = os.getenv('CLOUDFLARE_DOMAIN')
    
    if not all([tunnel_token, api_token, account_id, domain]):
        print("Missing required environment variables. Please check your .env file.")
        return
    
    # Extract tunnel ID from token
    tunnel_id = get_tunnel_id_from_token(tunnel_token)
    if not tunnel_id:
        print("Could not extract tunnel ID from token.")
        return
    
    # Define services to configure
    services = [
        {"name": "n8n", "port": "5678"},
        {"name": "webui", "port": "3000"},
        {"name": "flowise", "port": "3001"},
        {"name": "ollama", "port": "11434"},
        {"name": "searxng", "port": "8080"}
    ]
    
    # Set up tunnel hostnames
    setup_tunnel_hostnames(account_id, tunnel_id, api_token, domain, services)

if __name__ == "__main__":
    main() 
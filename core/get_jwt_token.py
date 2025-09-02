import requests
import configparser
import os
from getpass import getpass

def get_jwt_token(base_url, username, password):
    """
    Get JWT token from ThingsBoard using username/password
    
    Args:
        base_url: ThingsBoard server URL
        username: Your ThingsBoard username
        password: Your ThingsBoard password
        
    Returns:
        JWT token string or None if failed
    """
    login_url = f"{base_url.rstrip('/')}/api/auth/login"
    
    payload = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(login_url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        token = result.get('token')
        
        if token:
            print(f"✅ Successfully obtained JWT token")
            print(f"Token: {token}")
            return token
        else:
            print("❌ No token in response")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def update_config_with_token(token, config_file="data/config/config.properties"):
    """Update config file with the JWT token"""
    # Fallback to old location if new location doesn't exist
    if not os.path.exists(config_file):
        config_file = "config/config.properties"
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    if 'thingsboard' not in config:
        config.add_section('thingsboard')
    
    config.set('thingsboard', 'jwt_token', token)
    
    with open(config_file, 'w') as f:
        config.write(f)
    
    print(f"✅ Updated {config_file} with JWT token")

if __name__ == "__main__":
    # Load current config
    config = configparser.ConfigParser()
    config.read("config/config.properties")
    
    base_url = config.get('thingsboard', 'url', fallback='https://thingsboard-poc.papayaparking.com')
    username = config.get('thingsboard', 'username', fallback=None)
    password = config.get('thingsboard', 'password', fallback=None)
    
    print(f"Getting JWT token from: {base_url}")
    
    # Use username from config or prompt for it
    if username:
        print(f"Using username from config: {username}")
    else:
        print("Please enter your ThingsBoard credentials:")
        username = input("Username: ")
    
    # Use password from config or prompt for it
    if password and password != 'your_password_here':
        print("Using password from config")
    else:
        password = getpass("Password: ")
    
    token = get_jwt_token(base_url, username, password)
    
    if token:
        update_config_with_token(token)
        print("\n🎉 Ready to use! You can now run your device service.")
    else:
        print("\n❌ Failed to get token. Please check your credentials and try again.")
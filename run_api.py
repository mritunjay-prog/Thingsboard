#!/usr/bin/env python3
"""
Direct API Entry Point

This script provides a clean entry point to start the core API service (core/api.py)
with proper device provisioning and environment setup.

Usage:
    python run_api.py                    # Normal start with provisioning check
    python run_api.py --force-provision  # Force re-provision device
    python run_api.py --skip-provision   # Skip provisioning (use existing device info)
"""

import sys
import os
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_argument_parser():
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Start the IoT Device API Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_api.py                    # Normal start
  python run_api.py --force-provision  # Re-provision device
  python run_api.py --skip-provision   # Skip provisioning
        """
    )
    
    parser.add_argument(
        '--force-provision',
        action='store_true',
        help='Force device re-provisioning even if device exists'
    )
    
    parser.add_argument(
        '--skip-provision',
        action='store_true',
        help='Skip device provisioning (requires existing device info)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='data/config/config.properties',
        help='Path to configuration file (default: data/config/config.properties)'
    )
    
    return parser

def validate_config(config_path):
    """Validate that required configuration exists."""
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please ensure your configuration file exists with ThingsBoard settings.")
        return False
    
    print(f"✅ Configuration file found: {config_path}")
    return True

def provision_device(force_provision=False):
    """Handle device provisioning."""
    try:
        from core.APIProvision import get_device_info, get_device_id_by_name
        
        if not force_provision:
            print("🔍 Checking for existing device...")
            # Try to get device info without full provisioning
            try:
                # This would check if device already exists
                device_id, device_token, country_asset_id, state_asset_id = get_device_info()
                print("✅ Using existing device configuration")
                return device_id, device_token, country_asset_id, state_asset_id
            except Exception:
                print("⚠️ No existing device found, proceeding with provisioning...")
        
        print("🚀 Starting device provisioning...")
        device_id, device_token, country_asset_id, state_asset_id = get_device_info()
        
        print("✅ Device provisioning completed successfully!")
        print(f"   Device ID: {device_id}")
        print(f"   Device Token: {device_token[:20]}...")
        print(f"   Country Asset ID: {country_asset_id}")
        print(f"   State Asset ID: {state_asset_id}")
        
        return device_id, device_token, country_asset_id, state_asset_id
        
    except Exception as e:
        print(f"❌ Device provisioning failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your ThingsBoard credentials in config/config.properties")
        print("2. Ensure ThingsBoard server is accessible")
        print("3. Verify your network connection")
        raise

def set_environment_variables(device_id, device_token, country_asset_id, state_asset_id):
    """Set environment variables for the API service."""
    os.environ['DEVICE_ID'] = device_id
    os.environ['DEVICE_TOKEN'] = device_token
    os.environ['COUNTRY_ASSET_ID'] = country_asset_id
    os.environ['STATE_ASSET_ID'] = state_asset_id
    
    print("✅ Environment variables set for API service")

def start_api_service():
    """Start the core API service."""
    try:
        print("\n🚀 Starting IoT Device API Service...")
        print("=" * 50)
        
        # Import and run the API service
        from core import api
        
        # The api module will start its MQTT client and telemetry service
        # This will block until the application exits
        
    except KeyboardInterrupt:
        print("\n🛑 API service stopped by user")
    except Exception as e:
        print(f"❌ API service error: {e}")
        raise

def main():
    """Main entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    print("🔧 IoT Device API Service Launcher")
    print("=" * 40)
    
    # Validate configuration
    if not validate_config(args.config):
        sys.exit(1)
    
    # Handle device provisioning
    if not args.skip_provision:
        try:
            device_id, device_token, country_asset_id, state_asset_id = provision_device(
                force_provision=args.force_provision
            )
            
            # Set environment variables for the API service
            set_environment_variables(device_id, device_token, country_asset_id, state_asset_id)
            
        except Exception as e:
            print(f"❌ Failed to provision device: {e}")
            sys.exit(1)
    else:
        print("⚠️ Skipping device provisioning - using existing environment variables")
        required_vars = ['DEVICE_ID', 'DEVICE_TOKEN', 'COUNTRY_ASSET_ID', 'STATE_ASSET_ID']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {missing_vars}")
            print("Either run without --skip-provision or set these variables manually")
            sys.exit(1)
        
        print("✅ Using existing environment variables")
    
    # Start the API service
    try:
        start_api_service()
    except Exception as e:
        print(f"❌ Failed to start API service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
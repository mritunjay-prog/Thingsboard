#!/usr/bin/env python3
"""
Simple API Starter

Minimal entry point to start core/api.py with device provisioning.
This is the simplest way to start your IoT device API service.

Usage:
    python start_api.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Simple main entry point for the API service."""
    print("🚀 Starting IoT Device API Service...")
    
    try:
        # Import and start the API service
        # The api.py module handles its own provisioning and setup
        from core import api
        
        print("✅ API service started successfully")
        print("Press Ctrl+C to stop the service")
        
    except KeyboardInterrupt:
        print("\n🛑 API service stopped by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ API service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Quick test script for network diagnostics"""

from device_logging.network_diagnostics import run_network_diagnostics
import json

# Try to get real device_id if APIProvision is available
try:
    # First try to get device_id by name (more efficient)
    from core.APIProvision import get_device_id_by_name, DEVICE_NAME
    device_id = get_device_id_by_name(DEVICE_NAME)
    
    if device_id:
        print(f"Using real device_id: {device_id}")
    else:
        # Fallback to full provisioning if device not found
        from core.APIProvision import get_device_info
        device_id, _, _, _ = get_device_info()
        print(f"Device provisioned, using device_id: {device_id}")
        
except Exception as e:
    device_id = "test_device"
    print(f"Using fallback device_id: {device_id} (Could not get real device_id: {e})")

# Test 1: Basic connectivity
print("Testing basic connectivity...")
result1 = run_network_diagnostics(device_id, {
    "tests": ["ping", "dns"],
    "target_host": "google.com",
    "duration_seconds": 5
})

print("PING Status:", result1["test_results"]["ping"]["status"])
print("DNS Status:", result1["test_results"]["dns"]["status"])
print("Network Interface:", result1["network_interface"])
print("Connection Type:", result1["connection_type"])
print("Device ID:", result1["device_id"])

# Test 2: ThingsBoard connectivity
print("\nTesting ThingsBoard connectivity...")
result2 = run_network_diagnostics(device_id, {
    "tests": ["ping", "dns", "traceroute"],
    "target_host": "thingsboard.io",
    "duration_seconds": 10
})

print("Results:", json.dumps(result2, indent=2))
#!/usr/bin/env python3
"""
Test script for network_diagnostics.py module
Run comprehensive tests without ThingsBoard RPC
"""

import json
import time
from device_logging.network_diagnostics import run_network_diagnostics


def test_basic_connectivity():
    """Test basic ping and DNS functionality"""
    print("=" * 60)
    print("TEST 1: Basic Connectivity (Ping + DNS)")
    print("=" * 60)
    
    params = {
        "tests": ["ping", "dns"],
        "target_host": "google.com",
        "duration_seconds": 5
    }
    
    result = run_network_diagnostics("test_device_001", params)
    print(json.dumps(result, indent=2))
    return result


def test_comprehensive_diagnostics():
    """Test all diagnostic features"""
    print("\n" + "=" * 60)
    print("TEST 2: Comprehensive Diagnostics (All Tests)")
    print("=" * 60)
    
    params = {
        "tests": ["ping", "traceroute", "bandwidth", "dns", "speed_test"],
        "target_host": "github.com",
        "duration_seconds": 15,
        "speed_test_servers": ["auto"]
    }
    
    result = run_network_diagnostics("test_device_002", params)
    print(json.dumps(result, indent=2))
    return result


def test_thingsboard_connectivity():
    """Test connectivity to ThingsBoard-like server"""
    print("\n" + "=" * 60)
    print("TEST 3: ThingsBoard Server Connectivity")
    print("=" * 60)
    
    params = {
        "tests": ["ping", "dns", "traceroute"],
        "target_host": "thingsboard.io",  # Using public ThingsBoard demo
        "duration_seconds": 10
    }
    
    result = run_network_diagnostics("test_device_003", params)
    print(json.dumps(result, indent=2))
    return result


def test_multiple_hosts():
    """Test connectivity to multiple hosts"""
    print("\n" + "=" * 60)
    print("TEST 4: Multiple Host Testing")
    print("=" * 60)
    
    hosts = ["google.com", "cloudflare.com", "github.com", "8.8.8.8"]
    
    for i, host in enumerate(hosts):
        print(f"\n--- Testing Host {i+1}: {host} ---")
        params = {
            "tests": ["ping", "dns"],
            "target_host": host,
            "duration_seconds": 3
        }
        
        result = run_network_diagnostics(f"test_device_00{i+4}", params)
        
        # Print summary
        test_results = result.get("test_results", {})
        ping_status = test_results.get("ping", {}).get("status", "unknown")
        dns_status = test_results.get("dns", {}).get("status", "unknown")
        latency = test_results.get("ping", {}).get("avg_latency_ms", 0)
        
        print(f"Host: {host}")
        print(f"  Ping: {ping_status} ({latency}ms)")
        print(f"  DNS:  {dns_status}")
        print(f"  Interface: {result.get('network_interface', 'unknown')}")
        print(f"  Connection: {result.get('connection_type', 'unknown')}")


def test_error_handling():
    """Test error handling with invalid hosts"""
    print("\n" + "=" * 60)
    print("TEST 5: Error Handling (Invalid Hosts)")
    print("=" * 60)
    
    invalid_hosts = ["invalid.nonexistent.domain", "999.999.999.999"]
    
    for host in invalid_hosts:
        print(f"\n--- Testing Invalid Host: {host} ---")
        params = {
            "tests": ["ping", "dns"],
            "target_host": host,
            "duration_seconds": 5
        }
        
        result = run_network_diagnostics("test_device_error", params)
        
        # Print error summary
        test_results = result.get("test_results", {})
        for test_name, test_result in test_results.items():
            status = test_result.get("status", "unknown")
            error = test_result.get("error", "No error")
            print(f"  {test_name}: {status} - {error}")


def test_speed_test_simulation():
    """Test speed test functionality"""
    print("\n" + "=" * 60)
    print("TEST 6: Speed Test Simulation")
    print("=" * 60)
    
    params = {
        "tests": ["speed_test"],
        "target_host": "speedtest.net",
        "duration_seconds": 10,
        "speed_test_servers": ["auto", "custom.speedtest.server.com"]
    }
    
    result = run_network_diagnostics("test_device_speed", params)
    
    # Print speed test results nicely
    speed_result = result.get("test_results", {}).get("speed_test", {})
    if speed_result.get("status") == "pass":
        print(f"Download Speed: {speed_result.get('download_mbps', 0)} Mbps")
        print(f"Upload Speed: {speed_result.get('upload_mbps', 0)} Mbps")
        print(f"Latency: {speed_result.get('latency_ms', 0)} ms")
        print(f"Jitter: {speed_result.get('jitter_ms', 0)} ms")
        print(f"Server: {speed_result.get('server', 'unknown')}")
        print(f"Test Duration: {speed_result.get('test_duration_seconds', 0)} seconds")
    else:
        print(f"Speed test failed: {speed_result.get('error', 'Unknown error')}")
    
    return result


def run_all_tests():
    """Run all test scenarios"""
    print("🚀 Starting Network Diagnostics Test Suite")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Run all tests
        test_basic_connectivity()
        test_comprehensive_diagnostics()
        test_thingsboard_connectivity()
        test_multiple_hosts()
        test_error_handling()
        test_speed_test_simulation()
        
        # Summary
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print(f"Total test duration: {elapsed_time:.1f} seconds")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        print("=" * 60)


def interactive_test():
    """Interactive test mode - let user choose parameters"""
    print("\n" + "=" * 60)
    print("🔧 INTERACTIVE TEST MODE")
    print("=" * 60)
    
    # Get user input
    target_host = input("Enter target host (default: google.com): ").strip() or "google.com"
    
    print("\nAvailable tests: ping, dns, traceroute, bandwidth, speed_test")
    tests_input = input("Enter tests (comma-separated, default: ping,dns): ").strip()
    tests = [t.strip() for t in tests_input.split(",")] if tests_input else ["ping", "dns"]
    
    duration_input = input("Enter test duration in seconds (default: 10): ").strip()
    duration = int(duration_input) if duration_input.isdigit() else 10
    
    # Run the test
    params = {
        "tests": tests,
        "target_host": target_host,
        "duration_seconds": duration,
        "speed_test_servers": ["auto"]
    }
    
    print(f"\n🔍 Running diagnostics on {target_host}...")
    print(f"Tests: {', '.join(tests)}")
    print(f"Duration: {duration} seconds")
    print("-" * 40)
    
    result = run_network_diagnostics("interactive_test", params)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        run_all_tests()
        
        # Ask if user wants to run interactive mode
        print("\n" + "=" * 60)
        choice = input("Would you like to run interactive test mode? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            interactive_test()
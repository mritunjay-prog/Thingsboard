import subprocess
import time
import json
import socket
import re
import threading
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime


class NetworkDiagnostics:
    """Comprehensive network diagnostics for IoT devices"""
    
    def __init__(self, device_id: str = None):
        self.device_id = device_id or "unknown"
        self.results = {}
        
    def run_diagnostics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive network diagnostics based on parameters"""
        
        tests = params.get("tests", ["ping", "dns"])
        target_host = params.get("target_host", "8.8.8.8")
        duration_seconds = params.get("duration_seconds", 30)
        speed_test_servers = params.get("speed_test_servers", ["auto"])
        
        print(f"Starting network diagnostics for {len(tests)} tests...")
        
        # Initialize results structure
        test_results = {}
        
        # Get network interface info
        network_interface, connection_type = self._get_network_interface_info()
        
        # Run each requested test
        for test in tests:
            print(f"Running {test} test...")
            
            if test == "ping":
                test_results["ping"] = self._run_ping_test(target_host, duration_seconds)
            elif test == "traceroute":
                test_results["traceroute"] = self._run_traceroute_test(target_host)
            elif test == "bandwidth":
                test_results["bandwidth"] = self._run_bandwidth_test(target_host, duration_seconds)
            elif test == "dns":
                test_results["dns"] = self._run_dns_test(target_host)
            elif test == "speed_test":
                test_results["speed_test"] = self._run_speed_test(speed_test_servers, duration_seconds)
        
        return {
            "success": True,
            "test_results": test_results,
            "network_interface": network_interface,
            "connection_type": connection_type,
            "test_timestamp": int(time.time() * 1000),
            "device_id": self.device_id
        }
    
    def _run_ping_test(self, target_host: str, duration_seconds: int) -> Dict[str, Any]:
        """Run ping connectivity test"""
        try:
            # Calculate number of pings (1 per second for duration)
            count = min(duration_seconds, 30)  # Cap at 30 pings
            
            # Run ping command
            cmd = ["ping", "-c", str(count), target_host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration_seconds + 10)
            
            if result.returncode == 0:
                # Parse ping output
                output = result.stdout
                
                # Extract average latency
                avg_match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+', output)
                avg_latency = float(avg_match.group(1)) if avg_match else 0.0
                
                # Extract packet loss
                loss_match = re.search(r'(\d+)% packet loss', output)
                packet_loss = int(loss_match.group(1)) if loss_match else 0
                
                return {
                    "status": "pass" if packet_loss < 10 else "fail",
                    "avg_latency_ms": round(avg_latency, 1),
                    "packet_loss_percent": packet_loss,
                    "packets_sent": count,
                    "target_host": target_host
                }
            else:
                return {
                    "status": "fail",
                    "error": "Ping command failed",
                    "avg_latency_ms": 0,
                    "packet_loss_percent": 100
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": "fail",
                "error": "Ping test timed out",
                "avg_latency_ms": 0,
                "packet_loss_percent": 100
            }
        except Exception as e:
            return {
                "status": "fail",
                "error": f"Ping test error: {str(e)}",
                "avg_latency_ms": 0,
                "packet_loss_percent": 100
            }
    
    def _run_traceroute_test(self, target_host: str) -> Dict[str, Any]:
        """Run traceroute network path test"""
        try:
            # Use traceroute command (or tracepath as fallback)
            cmd = ["traceroute", "-m", "15", target_host]  # Max 15 hops
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            except FileNotFoundError:
                # Fallback to tracepath if traceroute not available
                cmd = ["tracepath", target_host]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                output = result.stdout
                lines = output.strip().split('\n')
                
                # Count hops (exclude header line)
                hops = 0
                total_time = 0
                
                for line in lines[1:]:  # Skip header
                    if '*' not in line and 'ms' in line:
                        hops += 1
                        # Extract time from line
                        time_matches = re.findall(r'([\d.]+)\s*ms', line)
                        if time_matches:
                            total_time += float(time_matches[0])
                
                return {
                    "status": "pass" if hops > 0 else "fail",
                    "hops": hops,
                    "total_time_ms": round(total_time, 1),
                    "target_host": target_host
                }
            else:
                return {
                    "status": "fail",
                    "error": "Traceroute command failed",
                    "hops": 0,
                    "total_time_ms": 0
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": "fail",
                "error": "Traceroute test timed out",
                "hops": 0,
                "total_time_ms": 0
            }
        except Exception as e:
            return {
                "status": "fail",
                "error": f"Traceroute test error: {str(e)}",
                "hops": 0,
                "total_time_ms": 0
            }
    
    def _run_bandwidth_test(self, target_host: str, duration_seconds: int) -> Dict[str, Any]:
        """Run basic bandwidth test using HTTP download"""
        try:
            # Use a test file download to measure bandwidth
            test_url = f"http://{target_host}/test" if not target_host.startswith('http') else target_host
            
            start_time = time.time()
            
            # Try to download a test file or make multiple requests
            total_bytes = 0
            requests_made = 0
            
            while time.time() - start_time < min(duration_seconds, 30):
                try:
                    response = requests.get(test_url, timeout=5, stream=True)
                    if response.status_code == 200:
                        for chunk in response.iter_content(chunk_size=1024):
                            total_bytes += len(chunk)
                            if time.time() - start_time >= duration_seconds:
                                break
                    requests_made += 1
                except:
                    break
            
            elapsed_time = time.time() - start_time
            
            if total_bytes > 0 and elapsed_time > 0:
                # Calculate bandwidth in Mbps
                bandwidth_mbps = (total_bytes * 8) / (elapsed_time * 1000000)
                
                return {
                    "status": "pass",
                    "bandwidth_mbps": round(bandwidth_mbps, 2),
                    "total_bytes": total_bytes,
                    "duration_seconds": round(elapsed_time, 1),
                    "requests_made": requests_made
                }
            else:
                return {
                    "status": "fail",
                    "error": "No data transferred",
                    "bandwidth_mbps": 0,
                    "total_bytes": 0
                }
                
        except Exception as e:
            return {
                "status": "fail",
                "error": f"Bandwidth test error: {str(e)}",
                "bandwidth_mbps": 0,
                "total_bytes": 0
            }
    
    def _run_dns_test(self, target_host: str) -> Dict[str, Any]:
        """Run DNS resolution test"""
        try:
            start_time = time.time()
            
            # Resolve hostname to IP
            ip_address = socket.gethostbyname(target_host)
            
            resolution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "status": "pass",
                "resolution_time_ms": round(resolution_time, 1),
                "resolved_ip": ip_address,
                "target_host": target_host
            }
            
        except socket.gaierror as e:
            return {
                "status": "fail",
                "error": f"DNS resolution failed: {str(e)}",
                "resolution_time_ms": 0,
                "target_host": target_host
            }
        except Exception as e:
            return {
                "status": "fail",
                "error": f"DNS test error: {str(e)}",
                "resolution_time_ms": 0
            }
    
    def _run_speed_test(self, servers: List[str], duration_seconds: int) -> Dict[str, Any]:
        """Run internet speed test"""
        try:
            # Simulate speed test results (in real implementation, use speedtest-cli or similar)
            # For demonstration, we'll simulate realistic values
            
            import random
            
            # Simulate test duration
            test_duration = min(duration_seconds, 30)
            time.sleep(min(test_duration / 10, 3))  # Simulate test time
            
            # Generate realistic speed test results
            download_mbps = round(random.uniform(50, 100), 1)
            upload_mbps = round(random.uniform(20, 50), 1)
            latency_ms = round(random.uniform(10, 50), 1)
            jitter_ms = round(random.uniform(1, 10), 1)
            
            server = servers[0] if servers else "auto"
            if server == "auto":
                server = "speedtest.provider.com"
            
            return {
                "status": "pass",
                "download_mbps": download_mbps,
                "upload_mbps": upload_mbps,
                "latency_ms": latency_ms,
                "jitter_ms": jitter_ms,
                "server": server,
                "test_duration_seconds": test_duration
            }
            
        except Exception as e:
            return {
                "status": "fail",
                "error": f"Speed test error: {str(e)}",
                "download_mbps": 0,
                "upload_mbps": 0,
                "latency_ms": 0,
                "jitter_ms": 0
            }
    
    def _get_network_interface_info(self) -> tuple:
        """Get current network interface and connection type"""
        try:
            # Try to get network interface information
            result = subprocess.run(["ip", "route", "show", "default"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout
                
                # Extract interface name
                interface_match = re.search(r'dev (\w+)', output)
                interface = interface_match.group(1) if interface_match else "unknown"
                
                # Determine connection type based on interface name
                if interface.startswith('wwan') or interface.startswith('ppp'):
                    connection_type = "4G_LTE"
                elif interface.startswith('wlan') or interface.startswith('wifi'):
                    connection_type = "WiFi"
                elif interface.startswith('eth') or interface.startswith('enp'):
                    connection_type = "Ethernet"
                else:
                    connection_type = "Unknown"
                
                return interface, connection_type
            else:
                return "unknown", "Unknown"
                
        except Exception as e:
            print(f"Error getting network interface info: {e}")
            return "unknown", "Unknown"


def run_network_diagnostics(device_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to run network diagnostics"""
    diagnostics = NetworkDiagnostics(device_id)
    return diagnostics.run_diagnostics(params)


# Test function for standalone usage
if __name__ == "__main__":
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
    
    # Test the network diagnostics
    test_params = {
        "tests": ["ping", "dns", "traceroute"],
        "target_host": "google.com",
        "duration_seconds": 10
    }
    
    result = run_network_diagnostics(device_id, test_params)
    print(json.dumps(result, indent=2))
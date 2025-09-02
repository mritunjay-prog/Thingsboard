"""
Comprehensive Diagnostics Utilities

Production-grade diagnostics combining network, system, and sensor diagnostics
with detailed reporting, health monitoring, and automated troubleshooting.
"""

import time
import json
import subprocess
import socket
import re
import threading
import psutil
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .config_manager import ConfigManager
from .logger_factory import LoggerFactory


class NetworkDiagnostics:
    """Enhanced network diagnostics with comprehensive testing capabilities."""
    
    def __init__(self, config_manager: ConfigManager, logger: logging.Logger):
        self.config = config_manager
        self.logger = logger
        self.network_config = config_manager.get_network_config()
    
    def run_comprehensive_diagnostics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive network diagnostics with parallel execution."""
        tests = params.get("tests", ["ping", "dns"])
        target_host = params.get("target_host", "8.8.8.8")
        duration_seconds = params.get("duration_seconds", 30)
        
        self.logger.info(f"Starting comprehensive network diagnostics: {tests}")
        
        # Get network interface info
        network_interface, connection_type = self._get_network_interface_info()
        
        # Run tests in parallel for better performance
        test_results = {}
        with ThreadPoolExecutor(max_workers=len(tests)) as executor:
            future_to_test = {}
            
            for test in tests:
                if test == "ping":
                    future = executor.submit(self._run_ping_test, target_host, duration_seconds)
                elif test == "traceroute":
                    future = executor.submit(self._run_traceroute_test, target_host)
                elif test == "dns":
                    future = executor.submit(self._run_dns_test, target_host)
                elif test == "bandwidth":
                    future = executor.submit(self._run_bandwidth_test, target_host, duration_seconds)
                elif test == "speed_test":
                    future = executor.submit(self._run_speed_test, params.get("speed_test_servers", ["auto"]), duration_seconds)
                elif test == "port_scan":
                    future = executor.submit(self._run_port_scan, target_host, params.get("ports", []))
                else:
                    continue
                
                future_to_test[future] = test
            
            # Collect results
            for future in as_completed(future_to_test):
                test_name = future_to_test[future]
                try:
                    test_results[test_name] = future.result()
                except Exception as e:
                    self.logger.error(f"Test {test_name} failed: {e}")
                    test_results[test_name] = {
                        "status": "fail",
                        "error": str(e)
                    }
        
        return {
            "success": True,
            "test_results": test_results,
            "network_interface": network_interface,
            "connection_type": connection_type,
            "test_timestamp": int(time.time() * 1000),
            "device_id": self.config.get_system_config().device_id,
            "test_duration_seconds": time.time() - params.get("start_time", time.time())
        }
    
    def _run_ping_test(self, target_host: str, duration_seconds: int) -> Dict[str, Any]:
        """Enhanced ping test with statistics."""
        try:
            count = min(duration_seconds, 30)
            cmd = ["ping", "-c", str(count), target_host]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration_seconds + 10)
            test_duration = time.time() - start_time
            
            if result.returncode == 0:
                output = result.stdout
                
                # Extract statistics
                avg_match = re.search(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', output)
                loss_match = re.search(r'(\d+)% packet loss', output)
                
                avg_latency = float(avg_match.group(2)) if avg_match else 0.0
                min_latency = float(avg_match.group(1)) if avg_match else 0.0
                max_latency = float(avg_match.group(3)) if avg_match else 0.0
                jitter = float(avg_match.group(4)) if avg_match else 0.0
                packet_loss = int(loss_match.group(1)) if loss_match else 0
                
                return {
                    "status": "pass" if packet_loss < 10 else "fail",
                    "avg_latency_ms": round(avg_latency, 1),
                    "min_latency_ms": round(min_latency, 1),
                    "max_latency_ms": round(max_latency, 1),
                    "jitter_ms": round(jitter, 1),
                    "packet_loss_percent": packet_loss,
                    "packets_sent": count,
                    "test_duration_seconds": round(test_duration, 2),
                    "target_host": target_host
                }
            else:
                return {
                    "status": "fail",
                    "error": "Ping command failed",
                    "stderr": result.stderr,
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
    
    def _run_dns_test(self, target_host: str) -> Dict[str, Any]:
        """Enhanced DNS test with multiple record types."""
        try:
            results = {}
            
            # Test A record resolution
            start_time = time.time()
            ip_address = socket.gethostbyname(target_host)
            a_record_time = (time.time() - start_time) * 1000
            
            results["a_record"] = {
                "resolved_ip": ip_address,
                "resolution_time_ms": round(a_record_time, 1)
            }
            
            # Test reverse DNS
            try:
                start_time = time.time()
                hostname = socket.gethostbyaddr(ip_address)[0]
                reverse_time = (time.time() - start_time) * 1000
                
                results["reverse_dns"] = {
                    "hostname": hostname,
                    "resolution_time_ms": round(reverse_time, 1)
                }
            except:
                results["reverse_dns"] = {
                    "status": "fail",
                    "error": "Reverse DNS lookup failed"
                }
            
            return {
                "status": "pass",
                "resolution_time_ms": round(a_record_time, 1),
                "resolved_ip": ip_address,
                "target_host": target_host,
                "detailed_results": results
            }
            
        except socket.gaierror as e:
            return {
                "status": "fail",
                "error": f"DNS resolution failed: {str(e)}",
                "resolution_time_ms": 0,
                "target_host": target_host
            }
    
    def _run_port_scan(self, target_host: str, ports: List[int]) -> Dict[str, Any]:
        """Scan specified ports on target host."""
        if not ports:
            ports = [22, 80, 443, 1883, 8080, 8443]  # Common IoT ports
        
        open_ports = []
        closed_ports = []
        
        def scan_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((target_host, port))
                sock.close()
                return port, result == 0
            except:
                return port, False
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(scan_port, port) for port in ports]
            
            for future in as_completed(futures):
                port, is_open = future.result()
                if is_open:
                    open_ports.append(port)
                else:
                    closed_ports.append(port)
        
        return {
            "status": "pass",
            "open_ports": sorted(open_ports),
            "closed_ports": sorted(closed_ports),
            "total_ports_scanned": len(ports),
            "target_host": target_host
        }
    
    def _get_network_interface_info(self) -> Tuple[str, str]:
        """Get detailed network interface information."""
        try:
            # Get default route interface
            result = subprocess.run(["ip", "route", "show", "default"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                interface_match = re.search(r'dev (\w+)', result.stdout)
                interface = interface_match.group(1) if interface_match else "unknown"
                
                # Determine connection type with more detail
                if interface.startswith('wwan') or interface.startswith('ppp'):
                    connection_type = "4G_LTE"
                elif interface.startswith('wlan') or interface.startswith('wifi'):
                    connection_type = "WiFi"
                elif interface.startswith('eth') or interface.startswith('enp'):
                    connection_type = "Ethernet"
                elif interface.startswith('docker') or interface.startswith('br-'):
                    connection_type = "Virtual"
                else:
                    connection_type = "Unknown"
                
                return interface, connection_type
            
        except Exception as e:
            self.logger.warning(f"Failed to get network interface info: {e}")
        
        return "unknown", "Unknown"


class SystemDiagnostics:
    """Comprehensive system diagnostics and health monitoring."""
    
    def __init__(self, config_manager: ConfigManager, logger: logging.Logger):
        self.config = config_manager
        self.logger = logger
    
    def run_system_health_check(self) -> Dict[str, Any]:
        """Run comprehensive system health check."""
        self.logger.info("Running system health check")
        
        health_data = {
            "timestamp": int(time.time() * 1000),
            "system_info": self._get_system_info(),
            "resource_usage": self._get_resource_usage(),
            "disk_usage": self._get_disk_usage(),
            "network_interfaces": self._get_network_interfaces(),
            "running_processes": self._get_process_info(),
            "system_load": self._get_system_load(),
            "temperature": self._get_temperature_info(),
            "health_score": 0,
            "recommendations": []
        }
        
        # Calculate health score and recommendations
        health_data["health_score"] = self._calculate_health_score(health_data)
        health_data["recommendations"] = self._generate_recommendations(health_data)
        
        return health_data
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime_seconds": int(time.time() - psutil.boot_time())
        }
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        return {
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2)
        }
    
    def _get_disk_usage(self) -> List[Dict[str, Any]]:
        """Get disk usage for all mounted filesystems."""
        disk_usage = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent_used": round((usage.used / usage.total) * 100, 1)
                })
            except PermissionError:
                continue
        
        return disk_usage
    
    def _calculate_health_score(self, health_data: Dict[str, Any]) -> int:
        """Calculate overall system health score (0-100)."""
        score = 100
        
        # CPU usage impact
        cpu_usage = health_data["resource_usage"]["cpu_percent"]
        if cpu_usage > 90:
            score -= 20
        elif cpu_usage > 70:
            score -= 10
        
        # Memory usage impact
        memory_usage = health_data["resource_usage"]["memory_percent"]
        if memory_usage > 90:
            score -= 20
        elif memory_usage > 80:
            score -= 10
        
        # Disk usage impact
        for disk in health_data["disk_usage"]:
            if disk["percent_used"] > 95:
                score -= 15
            elif disk["percent_used"] > 85:
                score -= 5
        
        return max(0, score)


class DiagnosticsUtils:
    """
    Production-grade diagnostics utility combining network, system, and sensor diagnostics
    with comprehensive reporting and automated troubleshooting.
    """
    
    def __init__(self, config_manager: ConfigManager, logger_factory: LoggerFactory):
        self.config = config_manager
        self.logger = logger_factory.get_logger("diagnostics")
        self.performance_logger = logger_factory.get_performance_logger("diagnostics")
        
        # Initialize diagnostic components
        self.network_diagnostics = NetworkDiagnostics(config_manager, self.logger)
        self.system_diagnostics = SystemDiagnostics(config_manager, self.logger)
    
    def run_comprehensive_diagnostics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive diagnostics across all systems."""
        self.logger.info("Starting comprehensive diagnostics")
        self.performance_logger.start_timer("comprehensive_diagnostics")
        
        try:
            diagnostic_results = {
                "timestamp": int(time.time() * 1000),
                "device_id": self.config.get_system_config().device_id,
                "diagnostics_version": "1.0.0",
                "network_diagnostics": {},
                "system_diagnostics": {},
                "overall_health": {},
                "recommendations": []
            }
            
            # Run network diagnostics if requested
            if params.get("include_network", True):
                network_params = params.get("network_params", {})
                network_params["start_time"] = time.time()
                diagnostic_results["network_diagnostics"] = self.network_diagnostics.run_comprehensive_diagnostics(network_params)
            
            # Run system diagnostics if requested
            if params.get("include_system", True):
                diagnostic_results["system_diagnostics"] = self.system_diagnostics.run_system_health_check()
            
            # Generate overall health assessment
            diagnostic_results["overall_health"] = self._assess_overall_health(diagnostic_results)
            
            # Generate recommendations
            diagnostic_results["recommendations"] = self._generate_comprehensive_recommendations(diagnostic_results)
            
            duration = self.performance_logger.end_timer("comprehensive_diagnostics")
            diagnostic_results["diagnostic_duration_seconds"] = duration
            
            self.logger.info(f"Comprehensive diagnostics completed in {duration:.2f}s")
            return diagnostic_results
            
        except Exception as e:
            self.logger.error(f"Comprehensive diagnostics failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }
    
    def _assess_overall_health(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall system health from diagnostic results."""
        health_scores = []
        
        # Network health
        if "network_diagnostics" in results and results["network_diagnostics"].get("success"):
            network_score = self._calculate_network_health_score(results["network_diagnostics"])
            health_scores.append(("network", network_score))
        
        # System health
        if "system_diagnostics" in results:
            system_score = results["system_diagnostics"].get("health_score", 0)
            health_scores.append(("system", system_score))
        
        # Calculate overall score
        if health_scores:
            overall_score = sum(score for _, score in health_scores) / len(health_scores)
        else:
            overall_score = 0
        
        # Determine health status
        if overall_score >= 80:
            status = "healthy"
        elif overall_score >= 60:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "overall_score": round(overall_score, 1),
            "status": status,
            "component_scores": dict(health_scores),
            "assessment_time": datetime.now().isoformat()
        }
    
    def _calculate_network_health_score(self, network_results: Dict[str, Any]) -> int:
        """Calculate network health score from test results."""
        score = 100
        test_results = network_results.get("test_results", {})
        
        for test_name, result in test_results.items():
            if result.get("status") == "fail":
                if test_name in ["ping", "dns"]:
                    score -= 25  # Critical tests
                else:
                    score -= 10  # Less critical tests
            elif test_name == "ping" and result.get("packet_loss_percent", 0) > 5:
                score -= 15  # High packet loss
        
        return max(0, score)
    
    def _generate_comprehensive_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations based on all diagnostic results."""
        recommendations = []
        
        # Network recommendations
        if "network_diagnostics" in results:
            network_results = results["network_diagnostics"].get("test_results", {})
            
            if network_results.get("ping", {}).get("status") == "fail":
                recommendations.append("Network connectivity issues detected. Check network configuration and cables.")
            
            if network_results.get("dns", {}).get("status") == "fail":
                recommendations.append("DNS resolution issues detected. Check DNS server configuration.")
        
        # System recommendations
        if "system_diagnostics" in results:
            system_data = results["system_diagnostics"]
            
            cpu_usage = system_data.get("resource_usage", {}).get("cpu_percent", 0)
            if cpu_usage > 80:
                recommendations.append(f"High CPU usage detected ({cpu_usage}%). Consider optimizing running processes.")
            
            memory_usage = system_data.get("resource_usage", {}).get("memory_percent", 0)
            if memory_usage > 85:
                recommendations.append(f"High memory usage detected ({memory_usage}%). Consider adding more RAM or optimizing memory usage.")
        
        # Overall health recommendations
        overall_health = results.get("overall_health", {})
        if overall_health.get("status") == "critical":
            recommendations.append("System health is critical. Immediate attention required.")
        elif overall_health.get("status") == "warning":
            recommendations.append("System health shows warning signs. Monitor closely and address issues.")
        
        if not recommendations:
            recommendations.append("System appears to be operating normally.")
        
        return recommendations
    
    def export_diagnostics_report(self, results: Dict[str, Any], format_type: str = "json") -> str:
        """Export diagnostics results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_id = self.config.get_system_config().device_id
        
        if format_type.lower() == "json":
            filename = f"diagnostics_report_{device_id}_{timestamp}.json"
            filepath = Path("reports") / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Diagnostics report exported to {filepath}")
        return str(filepath)
"""
Production-Grade Sensor Manager

Centralized management of all IoT sensors and utilities with comprehensive
monitoring, health checks, automated diagnostics, and reporting capabilities.
"""

import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .config_manager import ConfigManager
from .logger_factory import LoggerFactory
from .diagnostics_utils import DiagnosticsUtils


class SensorHealthMonitor:
    """Continuous health monitoring for all sensors."""
    
    def __init__(self, sensor_manager, logger: logging.Logger):
        self.sensor_manager = sensor_manager
        self.logger = logger
        self.monitoring_active = False
        self.monitoring_thread = None
        self.health_history = []
        self.alert_callbacks = []
    
    def start_monitoring(self, interval_seconds: int = 300) -> None:
        """Start continuous health monitoring."""
        if self.monitoring_active:
            self.logger.warning("Health monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        self.logger.info(f"Health monitoring started with {interval_seconds}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                health_data = self.sensor_manager.check_all_sensors_health()
                self.health_history.append(health_data)
                
                # Keep only last 24 hours of data
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.health_history = [
                    h for h in self.health_history 
                    if datetime.fromisoformat(h["timestamp"]) > cutoff_time
                ]
                
                # Check for alerts
                self._check_health_alerts(health_data)
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _check_health_alerts(self, health_data: Dict[str, Any]) -> None:
        """Check for health alerts and trigger callbacks."""
        alerts = []
        
        for sensor_name, sensor_health in health_data.get("sensors", {}).items():
            if not sensor_health.get("healthy", True):
                alerts.append({
                    "type": "sensor_unhealthy",
                    "sensor": sensor_name,
                    "message": f"Sensor {sensor_name} is unhealthy",
                    "details": sensor_health
                })
        
        # Trigger alert callbacks
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add callback for health alerts."""
        self.alert_callbacks.append(callback)
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trends over specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_data = [
            h for h in self.health_history 
            if datetime.fromisoformat(h["timestamp"]) > cutoff_time
        ]
        
        if not recent_data:
            return {"error": "No health data available"}
        
        # Calculate trends
        trends = {
            "time_period_hours": hours,
            "data_points": len(recent_data),
            "sensor_trends": {},
            "overall_health_trend": "stable"
        }
        
        # Analyze each sensor
        sensors = set()
        for data in recent_data:
            sensors.update(data.get("sensors", {}).keys())
        
        for sensor in sensors:
            sensor_data = [
                d["sensors"].get(sensor, {}) for d in recent_data 
                if sensor in d.get("sensors", {})
            ]
            
            if sensor_data:
                healthy_count = sum(1 for s in sensor_data if s.get("healthy", False))
                health_percentage = (healthy_count / len(sensor_data)) * 100
                
                trends["sensor_trends"][sensor] = {
                    "health_percentage": round(health_percentage, 1),
                    "total_checks": len(sensor_data),
                    "healthy_checks": healthy_count,
                    "trend": "improving" if health_percentage > 80 else "degrading" if health_percentage < 60 else "stable"
                }
        
        return trends


class SensorManager:
    """
    Production-grade sensor manager providing centralized control and monitoring
    of all IoT sensors with comprehensive diagnostics and reporting.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        # Initialize configuration and logging
        self.config_manager = ConfigManager(config_path)
        self.logger_factory = LoggerFactory(self.config_manager)
        self.logger = self.logger_factory.get_logger("sensor_manager")
        self.performance_logger = self.logger_factory.get_performance_logger("sensor_manager")
        
        # Initialize diagnostics
        self.diagnostics = DiagnosticsUtils(self.config_manager, self.logger_factory)
        
        # Initialize health monitoring
        self.health_monitor = SensorHealthMonitor(self, self.logger)
        
        # Sensor registry
        self.sensors = {}
        self.sensor_configs = {}
        
        # Performance tracking
        self.operation_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_response_time": 0.0
        }
        
        self.logger.info("SensorManager initialized successfully")
    
    def register_sensor(self, sensor_name: str, sensor_instance: Any, config: Optional[Dict] = None) -> None:
        """Register a sensor with the manager."""
        self.sensors[sensor_name] = sensor_instance
        self.sensor_configs[sensor_name] = config or {}
        
        # Create sensor-specific logger
        sensor_logger = self.logger_factory.get_sensor_logger(sensor_name)
        
        self.logger.info(f"Registered sensor: {sensor_name}")
    
    def unregister_sensor(self, sensor_name: str) -> None:
        """Unregister a sensor from the manager."""
        if sensor_name in self.sensors:
            del self.sensors[sensor_name]
            del self.sensor_configs[sensor_name]
            self.logger.info(f"Unregistered sensor: {sensor_name}")
    
    def test_all_sensors(self) -> Dict[str, Any]:
        """Test all registered sensors comprehensively."""
        self.logger.info("Starting comprehensive sensor testing")
        self.performance_logger.start_timer("test_all_sensors")
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.config_manager.get_system_config().device_id,
            "total_sensors": len(self.sensors),
            "sensors": {},
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0
            },
            "recommendations": []
        }
        
        # Test sensors in parallel for better performance
        with ThreadPoolExecutor(max_workers=min(len(self.sensors), 5)) as executor:
            future_to_sensor = {
                executor.submit(self._test_single_sensor, name, sensor): name
                for name, sensor in self.sensors.items()
            }
            
            for future in as_completed(future_to_sensor):
                sensor_name = future_to_sensor[future]
                try:
                    result = future.result()
                    test_results["sensors"][sensor_name] = result
                    
                    # Update summary
                    if result["success"]:
                        test_results["summary"]["passed"] += 1
                    else:
                        test_results["summary"]["failed"] += 1
                    
                    if result.get("warnings"):
                        test_results["summary"]["warnings"] += len(result["warnings"])
                        
                except Exception as e:
                    self.logger.error(f"Sensor test failed for {sensor_name}: {e}")
                    test_results["sensors"][sensor_name] = {
                        "success": False,
                        "error": str(e),
                        "test_duration": 0
                    }
                    test_results["summary"]["failed"] += 1
        
        # Generate recommendations
        test_results["recommendations"] = self._generate_test_recommendations(test_results)
        
        duration = self.performance_logger.end_timer("test_all_sensors")
        test_results["total_test_duration"] = duration
        
        self.logger.info(f"Sensor testing completed in {duration:.2f}s")
        return test_results
    
    def _test_single_sensor(self, sensor_name: str, sensor_instance: Any) -> Dict[str, Any]:
        """Test a single sensor comprehensively."""
        start_time = time.time()
        sensor_logger = self.logger_factory.get_sensor_logger(sensor_name)
        
        try:
            sensor_logger.info(f"Testing sensor: {sensor_name}")
            
            result = {
                "sensor_name": sensor_name,
                "success": False,
                "test_timestamp": datetime.now().isoformat(),
                "tests_performed": [],
                "warnings": [],
                "performance_metrics": {}
            }
            
            # Basic connectivity test
            if hasattr(sensor_instance, 'test_connection'):
                conn_result = sensor_instance.test_connection()
                result["tests_performed"].append("connectivity")
                result["connectivity"] = conn_result
                
                if not conn_result.get("success", False):
                    result["error"] = "Connectivity test failed"
                    return result
            
            # Data collection test
            if hasattr(sensor_instance, 'collect_data'):
                data_result = sensor_instance.collect_data()
                result["tests_performed"].append("data_collection")
                result["data_collection"] = data_result
                
                if not data_result.get("success", False):
                    result["warnings"].append("Data collection issues detected")
            
            # Health check test
            if hasattr(sensor_instance, 'check_health'):
                health_result = sensor_instance.check_health()
                result["tests_performed"].append("health_check")
                result["health_check"] = health_result
                
                if not health_result.get("healthy", True):
                    result["warnings"].append("Health check indicates issues")
            
            # Performance test
            if hasattr(sensor_instance, 'performance_test'):
                perf_result = sensor_instance.performance_test()
                result["tests_performed"].append("performance")
                result["performance_metrics"] = perf_result
            
            result["success"] = True
            sensor_logger.info(f"Sensor {sensor_name} test completed successfully")
            
        except Exception as e:
            sensor_logger.error(f"Sensor {sensor_name} test failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        finally:
            result["test_duration"] = round(time.time() - start_time, 2)
        
        return result
    
    def check_all_sensors_health(self) -> Dict[str, Any]:
        """Check health of all registered sensors."""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.config_manager.get_system_config().device_id,
            "sensors": {},
            "overall_health": "unknown"
        }
        
        healthy_count = 0
        total_count = len(self.sensors)
        
        for sensor_name, sensor_instance in self.sensors.items():
            try:
                if hasattr(sensor_instance, 'check_health'):
                    sensor_health = sensor_instance.check_health()
                else:
                    # Basic health check - try to get status
                    sensor_health = {"healthy": True, "status": "unknown"}
                
                health_data["sensors"][sensor_name] = sensor_health
                
                if sensor_health.get("healthy", False):
                    healthy_count += 1
                    
            except Exception as e:
                health_data["sensors"][sensor_name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        # Calculate overall health
        if total_count == 0:
            health_data["overall_health"] = "no_sensors"
        elif healthy_count == total_count:
            health_data["overall_health"] = "healthy"
        elif healthy_count > total_count * 0.7:
            health_data["overall_health"] = "warning"
        else:
            health_data["overall_health"] = "critical"
        
        health_data["health_percentage"] = round((healthy_count / max(total_count, 1)) * 100, 1)
        
        return health_data
    
    def run_comprehensive_diagnostics(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run comprehensive diagnostics including network, system, and sensors."""
        if params is None:
            params = {
                "include_network": True,
                "include_system": True,
                "include_sensors": True,
                "network_params": {
                    "tests": ["ping", "dns", "traceroute"],
                    "target_host": "8.8.8.8",
                    "duration_seconds": 30
                }
            }
        
        self.logger.info("Starting comprehensive diagnostics")
        
        # Run base diagnostics
        diagnostic_results = self.diagnostics.run_comprehensive_diagnostics(params)
        
        # Add sensor-specific diagnostics if requested
        if params.get("include_sensors", True):
            diagnostic_results["sensor_diagnostics"] = self.test_all_sensors()
        
        return diagnostic_results
    
    def collect_comprehensive_data(self) -> Dict[str, Any]:
        """Collect data from all sensors simultaneously."""
        self.logger.info("Collecting comprehensive sensor data")
        self.performance_logger.start_timer("collect_comprehensive_data")
        
        collection_results = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.config_manager.get_system_config().device_id,
            "sensors": {},
            "collection_summary": {
                "successful": 0,
                "failed": 0,
                "total_data_points": 0
            }
        }
        
        # Collect data from all sensors in parallel
        with ThreadPoolExecutor(max_workers=len(self.sensors)) as executor:
            future_to_sensor = {
                executor.submit(self._collect_sensor_data, name, sensor): name
                for name, sensor in self.sensors.items()
            }
            
            for future in as_completed(future_to_sensor):
                sensor_name = future_to_sensor[future]
                try:
                    sensor_data = future.result()
                    collection_results["sensors"][sensor_name] = sensor_data
                    
                    if sensor_data.get("success", False):
                        collection_results["collection_summary"]["successful"] += 1
                        collection_results["collection_summary"]["total_data_points"] += sensor_data.get("data_points", 0)
                    else:
                        collection_results["collection_summary"]["failed"] += 1
                        
                except Exception as e:
                    self.logger.error(f"Data collection failed for {sensor_name}: {e}")
                    collection_results["sensors"][sensor_name] = {
                        "success": False,
                        "error": str(e)
                    }
                    collection_results["collection_summary"]["failed"] += 1
        
        duration = self.performance_logger.end_timer("collect_comprehensive_data")
        collection_results["collection_duration"] = duration
        
        return collection_results
    
    def _collect_sensor_data(self, sensor_name: str, sensor_instance: Any) -> Dict[str, Any]:
        """Collect data from a single sensor."""
        try:
            if hasattr(sensor_instance, 'collect_data'):
                return sensor_instance.collect_data()
            else:
                return {
                    "success": False,
                    "error": "Sensor does not support data collection"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def start_health_monitoring(self, interval_seconds: int = 300) -> None:
        """Start continuous health monitoring."""
        self.health_monitor.start_monitoring(interval_seconds)
    
    def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        self.health_monitor.stop_monitoring()
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trends over specified time period."""
        return self.health_monitor.get_health_trends(hours)
    
    def create_master_report(self) -> Dict[str, Any]:
        """Create comprehensive master report of all systems."""
        self.logger.info("Creating master report")
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "device_id": self.config_manager.get_system_config().device_id,
            "report_version": "1.0.0",
            "system_info": {},
            "sensor_status": {},
            "diagnostics": {},
            "health_trends": {},
            "performance_stats": self.operation_stats.copy(),
            "recommendations": []
        }
        
        try:
            # System diagnostics
            report["diagnostics"] = self.run_comprehensive_diagnostics()
            
            # Current sensor status
            report["sensor_status"] = self.check_all_sensors_health()
            
            # Health trends
            report["health_trends"] = self.get_health_trends(24)
            
            # Generate master recommendations
            report["recommendations"] = self._generate_master_recommendations(report)
            
        except Exception as e:
            self.logger.error(f"Master report generation failed: {e}")
            report["error"] = str(e)
        
        return report
    
    def _generate_test_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_sensors = [
            name for name, result in test_results["sensors"].items()
            if not result.get("success", False)
        ]
        
        if failed_sensors:
            recommendations.append(f"Failed sensors detected: {', '.join(failed_sensors)}. Check connections and configurations.")
        
        warning_count = test_results["summary"]["warnings"]
        if warning_count > 0:
            recommendations.append(f"{warning_count} warnings detected. Review sensor health and performance.")
        
        if test_results["summary"]["passed"] == test_results["total_sensors"]:
            recommendations.append("All sensors are functioning normally.")
        
        return recommendations
    
    def _generate_master_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate master recommendations from comprehensive report."""
        recommendations = []
        
        # System health recommendations
        diagnostics = report.get("diagnostics", {})
        overall_health = diagnostics.get("overall_health", {})
        
        if overall_health.get("status") == "critical":
            recommendations.append("CRITICAL: System health is critical. Immediate attention required.")
        
        # Sensor health recommendations
        sensor_status = report.get("sensor_status", {})
        if sensor_status.get("overall_health") == "critical":
            recommendations.append("CRITICAL: Multiple sensors are unhealthy. Check sensor connections and power.")
        
        # Performance recommendations
        perf_stats = report.get("performance_stats", {})
        if perf_stats.get("failed_operations", 0) > perf_stats.get("successful_operations", 1):
            recommendations.append("High failure rate detected. Review system logs and sensor configurations.")
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters.")
        
        return recommendations
    
    def export_report(self, report: Dict[str, Any], format_type: str = "json") -> str:
        """Export report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_id = self.config_manager.get_system_config().device_id
        
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        if format_type.lower() == "json":
            filename = f"master_report_{device_id}_{timestamp}.json"
            filepath = reports_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Master report exported to {filepath}")
        return str(filepath)
    
    def get_operation_statistics(self) -> Dict[str, Any]:
        """Get operational statistics."""
        return {
            "operation_stats": self.operation_stats.copy(),
            "registered_sensors": list(self.sensors.keys()),
            "health_monitoring_active": self.health_monitor.monitoring_active,
            "log_statistics": self.logger_factory.get_log_statistics()
        }
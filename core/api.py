import json, time, random, threading, subprocess, sys, os
import requests
import paho.mqtt.client as mqtt
from pathlib import Path
from datetime import datetime    
from .APIProvision import get_device_info
from services.telemetry_manager import get_telemetry_manager, save_telemetry_data
from .database_service import initialize_database_service
from sensors.lidar import get_lidar_streaming_service, get_lidar_control_service
from sensors.lidar import get_lidar_telemetry_data, get_lidar_summary
from sensors.lidar import get_occupancy_detector, save_lidar_telemetry_to_file, get_lidar_telemetry_file_status
from sensors.ultrasonic import get_ultrasonic_telemetry_data, get_ultrasonic_summary
from sensors.ultrasonic import ultrasonic_control_service, get_ultrasonic_streaming_service
from sensors.ultrasonic import save_ultrasonic_telemetry_to_file, get_ultrasonic_telemetry_file_status
from sensors.ultrasonic import get_ultrasonic_proximity_detector
from sensors import (
    get_camera_capture_service, 
    get_camera_streaming_service,
    get_environment_conditions_service,
    get_air_quality_monitor_service,
    get_light_level_monitor_service
)
from sensors.camera import timed_camera_capture, estimate_camera_capture_session
from sensors.lidar import timed_lidar_capture, estimate_lidar_capture_session
from sensors.ultrasonic import timed_ultrasonic_capture, estimate_ultrasonic_capture_session
from sensors.environmental_sensor.environmental_manager import timed_environmental_capture, estimate_environmental_capture_session
from services import SimpleS3Uploader

# Import centralized telemetry publisher service
from services.telemetry_publisher import (
    get_telemetry_publisher,
    publish_lidar_telemetry,
    publish_occupancy_telemetry,
    publish_proximity_alert_telemetry,
    publish_environmental_telemetry,
    publish_telemetry
)

import configparser

def trigger_system_reboot(delay_seconds=0):
    """Trigger actual system reboot with optional delay"""
    
    def reboot_system():
        if delay_seconds > 0:
            print(f"System reboot scheduled in {delay_seconds} seconds...")
            time.sleep(delay_seconds)
        
        print("Initiating system reboot...")
        try:
            # For Linux systems
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to reboot system: {e}")
        except FileNotFoundError:
            print("'sudo' command not found. Trying alternative reboot methods...")
            try:
                # Alternative method without sudo (may require different permissions)
                subprocess.run(["reboot"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Unable to reboot system. Insufficient permissions or command not available.")
    
    # Run reboot in a separate thread to allow response to be sent first
    threading.Thread(target=reboot_system, daemon=True).start()

# Global variable to store the MQTT client
mqtt_client = None

# Initialize streaming service with publish callback (will be set up after MQTT client is created)
lidar_streaming_service = None

# Load configuration
config = configparser.ConfigParser()
config_file = 'data/config/config.properties'
# Fallback to old location if new location doesn't exist
if not os.path.exists(config_file):
    config_file = 'config/config.properties'
config.read(config_file)

# Get device info from environment variables (set by main.py) or fallback to provisioning
device_id = os.environ.get('DEVICE_ID')
token = os.environ.get('DEVICE_TOKEN')
country_asset = os.environ.get('COUNTRY_ASSET_ID')
state_asset = os.environ.get('STATE_ASSET_ID')

if not all([device_id, token, country_asset, state_asset]):
    print("⚠️ Device info not found in environment - running direct provisioning...")
    try:
        device_id, token, country_asset, state_asset = get_device_info()
        print("Device provisioned successfully!")
        print(f"Device ID: {device_id}")
        print(f"Device Token: {token[:20]}...")
        print(f"Country Asset ID: {country_asset}")
        print(f"State Asset ID: {state_asset}")
    except Exception as e:
        print(f"Failed to provision device: {e}")
        sys.exit(1)
else:
    print("✅ Using pre-provisioned device information")
    print(f"Device ID: {device_id}")
    print(f"Device Token: {token[:20]}...")
    print(f"Country Asset ID: {country_asset}")
    print(f"State Asset ID: {state_asset}")

# Store device info globally for use throughout the application
DEVICE_INFO = {
    'device_id': device_id,
    'device_token': token,
    'country_asset_id': country_asset,
    'state_asset_id': state_asset
}

def get_device_id():
    """Helper function to get device ID from global DEVICE_INFO"""
    return DEVICE_INFO['device_id']

def get_device_token():
    """Helper function to get device token from global DEVICE_INFO"""
    return DEVICE_INFO['device_token']

def get_country_asset_id():
    """Helper function to get country asset ID from global DEVICE_INFO"""
    return DEVICE_INFO['country_asset_id']

def get_state_asset_id():
    """Helper function to get state asset ID from global DEVICE_INFO"""
    return DEVICE_INFO['state_asset_id']



# Get ThingsBoard host from config
THINGSBOARD_HOST = config.get('thingsboard', 'url')
MQTT_HOST = THINGSBOARD_HOST.replace('https://', '').replace('http://', '')

# Create log directories (for telemetry data only, not logging)
log_base_dir = Path("data/logs")
log_base_dir.mkdir(parents=True, exist_ok=True)

print(f"✅ API initialized for device: {get_device_id()}")

# Initialize database service (runs only once)
print("🗄️ Initializing database service...")
try:
    db_init_success = initialize_database_service()
    if db_init_success:
        print("✅ Database service initialized successfully")
    else:
        print("⚠️ Database service initialization failed - continuing without database")
except Exception as e:
    print(f"❌ Database service initialization error: {e}")
    print("⚠️ Continuing without database service")

# Global data collection control state
collection_control = {
    "active": True,
    "sensors": {
        "lidar": {"active": True, "mode": "normal", "sampling_rate_hz": 0.1},
        "camera": {"active": True, "mode": "normal", "sampling_rate_hz": 0.1},
        "ultrasonic": {"active": True, "mode": "normal", "sampling_rate_hz": 0.1},
        "environmental": {"active": True, "mode": "normal", "sampling_rate_hz": 0.1}
    },
    "global_sampling_rate_hz": 0.1,  # Default: every 10 seconds
    "mode": "normal"
}
collection_control_lock = threading.Lock()
print(f"✅ Data collection control initialized")

# === MQTT Client Setup ===
client = mqtt.Client()
client.username_pw_set(get_device_token())

# Initialize telemetry publisher service with MQTT client
telemetry_publisher = get_telemetry_publisher(client)
print("✅ Telemetry publisher service initialized with MQTT client")

# Initialize the global MQTT client reference and streaming services
mqtt_client = client
lidar_control_service = get_lidar_control_service()
lidar_streaming_service = get_lidar_streaming_service(telemetry_callback=publish_lidar_telemetry)
lidar_control_service.set_telemetry_streaming_service(lidar_streaming_service)
ultrasonic_streaming_service = get_ultrasonic_streaming_service(telemetry_callback=publish_telemetry)

# Initialize the occupancy detector with telemetry callback
occupancy_detector = get_occupancy_detector(telemetry_callback=publish_occupancy_telemetry)

# Initialize the proximity detector with telemetry callback
proximity_detector = get_ultrasonic_proximity_detector(telemetry_callback=publish_proximity_alert_telemetry)

# Initialize the camera capture service
camera_capture_service = get_camera_capture_service()

# Initialize the camera streaming service
camera_streaming_service = get_camera_streaming_service()

# Initialize the environmental sensor services
environment_conditions_service = get_environment_conditions_service()
air_quality_monitor_service = get_air_quality_monitor_service()
light_level_monitor_service = get_light_level_monitor_service()

# Auto-start LiDAR system with default configuration for live data
auto_start_lidar = config.getboolean('DEFAULT', 'lidar.auto_start', fallback=True)  # Default to True
if auto_start_lidar:
    print("🚀 Auto-starting LiDAR system...")
    try:
        # Get configuration from config file with fallbacks
        default_lidar_config = {
            "scan_rate_hz": config.getfloat('DEFAULT', 'lidar.scan_rate_hz', fallback=10.0),
            "resolution": config.get('DEFAULT', 'lidar.resolution', fallback='medium'),
            "range_filter": {
                "min_range_m": config.getfloat('DEFAULT', 'lidar.min_range_m', fallback=0.5),
                "max_range_m": config.getfloat('DEFAULT', 'lidar.max_range_m', fallback=30.0)
            }
        }
        
        # Start LiDAR with configuration
        lidar_start_result = lidar_control_service.start(default_lidar_config)
        if lidar_start_result.get("active", False):
            print("✅ LiDAR system auto-started successfully!")
            print(f"   - Scan rate: {default_lidar_config['scan_rate_hz']} Hz")
            print(f"   - Resolution: {default_lidar_config['resolution']}")
            print(f"   - Range: {default_lidar_config['range_filter']['min_range_m']}m to {default_lidar_config['range_filter']['max_range_m']}m")
            
            # Auto-start occupancy detection if enabled
            auto_start_occupancy = config.getboolean('DEFAULT', 'lidar.auto_start_occupancy', fallback=True)
            if auto_start_occupancy:
                occupancy_start_result = occupancy_detector.start_detection()
                if occupancy_start_result.get("success", False):
                    print("✅ Occupancy detection auto-started successfully!")
                else:
                    print("⚠️ Failed to auto-start occupancy detection")
            else:
                print("ℹ️ Occupancy detection auto-start disabled in configuration")
        else:
            print("⚠️ Failed to auto-start LiDAR system")
            
    except Exception as e:
        print(f"❌ Error auto-starting LiDAR system: {e}")
    
    print("📡 System ready - LiDAR telemetry should be live!")
else:
    print("ℹ️ LiDAR auto-start disabled in configuration")
    print("📡 System ready - Use 'lidar.control' RPC to start LiDAR manually")

# Auto-start Ultrasonic system
auto_start_ultrasonic = config.getboolean('DEFAULT', 'ultrasonic.auto_start', fallback=True)  # Default to True
if auto_start_ultrasonic:
    print("🔊 Auto-starting Ultrasonic system...")
    try:
        # Start ultrasonic streaming with default interval
        ultrasonic_interval = config.getfloat('DEFAULT', 'ultrasonic.streaming_interval', fallback=2.0)
        ultrasonic_start_result = ultrasonic_streaming_service.start_streaming(ultrasonic_interval)
        
        if ultrasonic_start_result.get("success", False):
            print("✅ Ultrasonic system auto-started successfully!")
            print(f"   - Streaming interval: {ultrasonic_interval}s")
            print(f"   - 4 sensors active with distance and confidence data")
            
            # Auto-start proximity detection if enabled
            auto_start_proximity = config.getboolean('DEFAULT', 'ultrasonic.auto_start_proximity', fallback=True)
            if auto_start_proximity:
                proximity_start_result = proximity_detector.start_detection()
                if proximity_start_result.get("success", False):
                    print("✅ Proximity detection auto-started successfully!")
                    print(f"   - Sensor thresholds: {proximity_start_result.get('sensor_thresholds', {})}")
                else:
                    print("⚠️ Failed to auto-start proximity detection")
            else:
                print("ℹ️ Proximity detection auto-start disabled in configuration")
        else:
            print("⚠️ Failed to auto-start Ultrasonic system")
            
    except Exception as e:
        print(f"❌ Error auto-starting Ultrasonic system: {e}")
    
    print("📡 Ultrasonic telemetry should be live!")
else:
    print("ℹ️ Ultrasonic auto-start disabled in configuration")

# Auto-start Environmental sensors
auto_start_environmental = config.getboolean('DEFAULT', 'environmental.auto_start', fallback=True)  # Default to True
if auto_start_environmental:
    print("🌍 Auto-starting Environmental sensors...")
    try:
        # Start environment conditions monitoring
        env_interval = config.getint('DEFAULT', 'environmental.environment_interval_seconds', fallback=30)
        env_result = environment_conditions_service.start_monitoring(env_interval)
        if env_result.get("success", False):
            print(f"✅ Environment conditions monitoring started (interval: {env_interval}s)")
        else:
            print("⚠️ Failed to start environment conditions monitoring")
        
        # Start air quality monitoring
        air_interval = config.getint('DEFAULT', 'environmental.air_quality_interval_seconds', fallback=60)
        air_result = air_quality_monitor_service.start_monitoring(air_interval)
        if air_result.get("success", False):
            print(f"✅ Air quality monitoring started (interval: {air_interval}s)")
        else:
            print("⚠️ Failed to start air quality monitoring")
        
        # Start light level monitoring
        light_interval = config.getint('DEFAULT', 'environmental.light_level_interval_seconds', fallback=30)
        light_result = light_level_monitor_service.start_monitoring(light_interval)
        if light_result.get("success", False):
            print(f"✅ Light level monitoring started (interval: {light_interval}s)")
        else:
            print("⚠️ Failed to start light level monitoring")
            
        print("📡 Environmental sensors ready - telemetry should be live!")
        
    except Exception as e:
        print(f"❌ Error auto-starting Environmental sensors: {e}")
else:
    print("ℹ️ Environmental sensors auto-start disabled in configuration")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to ThingsBoard MQTT!")
        client.subscribe("v1/devices/me/rpc/request/+")  ## Thingsboard dashboard sent RPC e.g reboot 
    else:
        print(f"MQTT connection failed with code: {rc}")
client.on_connect = on_connect

def on_message(client, userdata, msg):
    print(f"RPC Received: {msg.topic}")
    
    try:
        req = json.loads(msg.payload.decode())
    except json.JSONDecodeError as e:
        print(f"Failed to parse RPC message: {e}")
        return

    method = req.get("method")
    params = req.get("params", {})
    topic_parts = msg.topic.split("/")
    rpc_id = msg.topic.split("/")[-1]

    if not isinstance(params, dict):
        params = {}

    print(f"RPC Call: {method}, Params: {params}")

    response = {"success": False, "error": f"Unknown method: {method}"}

    if method == "system.restart":
        delay_seconds = params.get("delay_seconds", 0)
        print(f"Triggering actual system restart (delay: {delay_seconds}s)...")
        
        # Send response first before triggering reboot
        response = {
            "success": True,
            "restart_scheduled_at": int(time.time() * 1000 + delay_seconds * 1000),
            "message": f"System reboot initiated with {delay_seconds}s delay"
        }
        
        # Trigger actual system reboot
        trigger_system_reboot(delay_seconds)



    elif method == "lidar.control":
        print("Processing LiDAR control request...")
        action = params.get("action", "status")
        config_payload = params.get("config", {})
        enable_streaming = params.get("enable_streaming", True)
        message = ""
        
        print(f"🔍 LiDAR control action: {action}")
        print(f"🔍 Config payload: {config_payload}")
        print(f"🔍 Enable streaming: {enable_streaming}")
        print(f"🔍 Current thread: {threading.current_thread().name}")
        print(f"🔍 Active thread count: {threading.active_count()}")
        
        try:
            # Apply configuration first (if provided)
            if config_payload:
                print(f"🔧 Applying LiDAR configuration: {config_payload}")
                try:
                    applied_config = lidar_control_service.apply_config(
                        scan_rate_hz=config_payload.get("scan_rate_hz"),
                        resolution=config_payload.get("resolution"),
                        range_filter=config_payload.get("range_filter")
                    )
                    print(f"✅ LiDAR configuration updated: {applied_config}")
                except Exception as cfg_err:
                    print(f"❌ Config apply error: {cfg_err}")
                    response = {
                        "success": False,
                        "data": {
                            "status": "error",
                            "message": f"Invalid configuration: {cfg_err}"
                        },
                        "timestamp": int(time.time() * 1000)
                    }
                    if rpc_id is not None:
                        client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                    return
            
            # Perform action with streaming integration
            streaming_result = None
            
            if action == "start":
                print(f"▶️ Starting LiDAR scanning...")
                try:
                    state = lidar_control_service.start()
                    print(f"✅ LiDAR control service started: {state}")
                    message = "LiDAR scanning started"
                except Exception as start_err:
                    print(f"❌ Error starting LiDAR control service: {start_err}")
                    import traceback
                    traceback.print_exc()
                    state = {"active": False, "error": str(start_err)}
                    message = f"LiDAR scanning start failed: {start_err}"
                
                # Start telemetry streaming if enabled
                if enable_streaming and state.get("active", False) and lidar_streaming_service:
                    streaming_result = lidar_streaming_service.start_streaming()
                    if streaming_result.get("success", False):
                        message += " with telemetry streaming"
                    else:
                        message += f" (streaming failed: {streaming_result.get('message', 'unknown error')})"
                
                # Occupancy detection starts automatically with LiDAR scanning
                message += " and occupancy detection enabled"
                        
            elif action == "stop":
                print(f"🛑 Stopping LiDAR scanning...")
                
                # Send immediate response to prevent client timeout
                immediate_response = {
                    "success": True,
                    "data": {
                        "status": "stopping",
                        "message": "LiDAR stop command received, processing..."
                    },
                    "timestamp": int(time.time() * 1000)
                }
                
                print(f"📤 Sending immediate stop response: {immediate_response}")
                if rpc_id is not None:
                    client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(immediate_response))
                    print(f"✅ Immediate stop response sent")
                
                # Now use normal stop method since service is lock-free
                try:
                    print(f"🛑 Attempting to stop LiDAR control service...")
                    state = lidar_control_service.stop()
                    print(f"✅ LiDAR control service stopped successfully: {state}")
                    message = "LiDAR scanning stopped"
                    print(f"✅ LiDAR stop operation completed successfully")
                    
                except Exception as stop_err:
                    print(f"❌ Error stopping LiDAR control service: {stop_err}")
                    import traceback
                    traceback.print_exc()
                    state = {"active": False, "error": str(stop_err)}
                    message = f"LiDAR scanning stopped with error: {stop_err}"
                    print(f"❌ LiDAR stop operation failed")
                
                # Stop telemetry streaming
                try:
                    if lidar_streaming_service:
                        print(f"📡 About to call lidar_streaming_service.stop_streaming()...")
                        streaming_result = lidar_streaming_service.stop_streaming()
                        print(f"📡 Streaming service stop result: {streaming_result}")
                    else:
                        print("⚠️ No streaming service available to stop")
                except Exception as stream_err:
                    print(f"❌ Error stopping streaming service: {stream_err}")
                    import traceback
                    traceback.print_exc()
                
                print(f"🔄 LiDAR stop process completed, continuing with normal telemetry...")
                
                # Since we already sent the response, skip the normal response mechanism
                return
                    
            elif action == "reset":
                # Stop streaming first
                if lidar_streaming_service:
                    streaming_result = lidar_streaming_service.stop_streaming()
                
                state = lidar_control_service.reset()
                message = "LiDAR control reset"
                
            elif action in ("status", "config"):
                state = lidar_control_service.current_state()
                if lidar_streaming_service:
                    streaming_status = lidar_streaming_service.get_status()
                    state["streaming"] = streaming_status
                else:
                    state["streaming"] = {"streaming": False, "message": "Streaming service not available"}
                
                # Add occupancy detection status
                if occupancy_detector:
                    occupancy_status = occupancy_detector.get_status()
                    state["occupancy_detection"] = occupancy_status
                else:
                    state["occupancy_detection"] = {"detecting": False, "message": "Occupancy detector not available"}
                
                message = "LiDAR status reported"
                
            else:
                response = {
                    "success": False,
                    "data": {
                        "status": "error",
                        "message": f"Unsupported action '{action}'"
                    },
                    "timestamp": int(time.time() * 1000)
                }
                if rpc_id is not None:
                    client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                return
            
            print(f"LiDAR control action '{action}' executed successfully")
            
            # Determine status based on action and state
            if action == "start":
                status = "active" if state.get("active", False) else "inactive"
            elif action == "stop":
                status = "inactive" if not state.get("active", False) else "active"
            elif action == "reset":
                status = "reset"
            elif action in ("status", "config"):
                status = "active" if state.get("active", False) else "inactive"
            else:
                status = "unknown"
            
            response = {
                "success": True,
                "data": {
                    "status": status,
                    "message": message
                },
                "timestamp": int(time.time() * 1000)
            }
        
        except Exception as e:
            print(f"❌ LiDAR control failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "data": {
                    "status": "error",
                    "message": f"LiDAR control failed: {e}"
                },
                "timestamp": int(time.time() * 1000)
            }

    elif method == "proximity.control":
        print("Processing Proximity detection control request...")
        action = params.get("action", "status")
        sensor_id = params.get("sensor_id")
        threshold_cm = params.get("threshold_cm")
        confidence_threshold = params.get("confidence_threshold")
        message = ""
        
        print(f"🔍 Proximity control action: {action}")
        
        try:
            if action == "start":
                print(f"▶️ Starting Proximity detection...")
                result = proximity_detector.start_detection()
                
                if result.get("success", False):
                    print(f"✅ Proximity detection started successfully")
                    message = "Proximity detection started"
                    status = "active"
                else:
                    print(f"❌ Failed to start Proximity detection: {result.get('message', 'Unknown error')}")
                    message = f"Failed to start: {result.get('message', 'Unknown error')}"
                    status = "error"
                    
            elif action == "stop":
                print(f"🛑 Stopping Proximity detection...")
                result = proximity_detector.stop_detection()
                
                if result.get("success", False):
                    print(f"✅ Proximity detection stopped successfully")
                    message = f"Proximity detection stopped"
                    status = "inactive"
                else:
                    print(f"❌ Failed to stop Proximity detection: {result.get('message', 'Unknown error')}")
                    message = f"Failed to stop: {result.get('message', 'Unknown error')}"
                    status = "error"
                    
            elif action == "update_threshold":
                if sensor_id and threshold_cm:
                    success = proximity_detector.update_sensor_threshold(sensor_id, threshold_cm)
                    if success:
                        message = f"Sensor {sensor_id} threshold updated to {threshold_cm}cm"
                        status = "updated"
                    else:
                        message = f"Failed to update threshold for sensor {sensor_id}"
                        status = "error"
                else:
                    message = "Missing sensor_id or threshold_cm parameters"
                    status = "error"
                    
            elif action == "update_confidence":
                if confidence_threshold is not None:
                    success = proximity_detector.update_confidence_threshold(confidence_threshold)
                    if success:
                        message = f"Confidence threshold updated to {confidence_threshold}"
                        status = "updated"
                    else:
                        message = f"Invalid confidence threshold: {confidence_threshold}"
                        status = "error"
                else:
                    message = "Missing confidence_threshold parameter"
                    status = "error"
                    
            elif action == "status":
                proximity_status = proximity_detector.get_status()
                status = "active" if proximity_status.get("detecting", False) else "inactive"
                message = "Proximity detection status reported"
                
                response = {
                    "success": True,
                    "data": {
                        "status": status,
                        "message": message,
                        "proximity_detection": proximity_status
                    },
                    "timestamp": int(time.time() * 1000)
                }
                
                if rpc_id is not None:
                    client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                return
                
            else:
                response = {
                    "success": False,
                    "data": {
                        "status": "error",
                        "message": f"Unsupported action '{action}'"
                    },
                    "timestamp": int(time.time() * 1000)
                }
                if rpc_id is not None:
                    client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                return
            
            print(f"Proximity control action '{action}' executed successfully")
            
            response = {
                "success": True,
                "data": {
                    "status": status,
                    "message": message
                },
                "timestamp": int(time.time() * 1000)
            }
        
        except Exception as e:
            print(f"❌ Proximity control failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "data": {
                    "status": "error",
                    "message": f"Proximity control failed: {e}"
                },
                "timestamp": int(time.time() * 1000)
            }

    elif method == "ultrasonic.control":
        print("Processing Ultrasonic control request...")
        action = params.get("action", "status")
        streaming_interval = params.get("streaming_interval", 2.0)
        message = ""
        
        print(f"🔍 Ultrasonic control action: {action}")
        print(f"🔍 Streaming interval: {streaming_interval}")
        
        try:
            if action == "start":
                print(f"▶️ Starting Ultrasonic streaming...")
                result = ultrasonic_streaming_service.start_streaming(streaming_interval)
                
                if result.get("success", False):
                    print(f"✅ Ultrasonic streaming started successfully")
                    message = f"Ultrasonic streaming started with {streaming_interval}s interval"
                    status = "active"
                else:
                    print(f"❌ Failed to start Ultrasonic streaming: {result.get('message', 'Unknown error')}")
                    message = f"Failed to start: {result.get('message', 'Unknown error')}"
                    status = "error"
                    
            elif action == "stop":
                print(f"🛑 Stopping Ultrasonic streaming...")
                result = ultrasonic_streaming_service.stop_streaming()
                
                if result.get("success", False):
                    print(f"✅ Ultrasonic streaming stopped successfully")
                    message = f"Ultrasonic streaming stopped"
                    status = "inactive"
                else:
                    print(f"❌ Failed to stop Ultrasonic streaming: {result.get('message', 'Unknown error')}")
                    message = f"Failed to stop: {result.get('message', 'Unknown error')}"
                    status = "error"
                    
            elif action == "status":
                # Get current ultrasonic telemetry data
                telemetry = get_ultrasonic_telemetry_data()
                status = "active" if telemetry else "inactive"
                message = "Ultrasonic status reported"
                
                # Add proximity detection status
                if proximity_detector:
                    proximity_status = proximity_detector.get_status()
                    result = {
                        "success": True,
                        "data": {
                            "status": status,
                            "message": message,
                            "streaming_interval": streaming_interval,
                            "proximity_detection": proximity_status
                        },
                        "timestamp": int(time.time() * 1000)
                    }
                    
                    if rpc_id is not None:
                        client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(result))
                    return
                
            else:
                response = {
                    "success": False,
                    "data": {
                        "status": "error",
                        "message": f"Unsupported action '{action}'"
                    },
                    "timestamp": int(time.time() * 1000)
                }
                if rpc_id is not None:
                    client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                return
            
            print(f"Ultrasonic control action '{action}' executed successfully")
            
            response = {
                "success": True,
                "data": {
                    "status": status,
                    "message": message,
                    "streaming_interval": streaming_interval
                },
                "timestamp": int(time.time() * 1000)
            }
        
        except Exception as e:
            print(f"❌ Ultrasonic control failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "data": {
                    "status": "error",
                    "message": f"Ultrasonic control failed: {e}"
                },
                "timestamp": int(time.time() * 1000)
            }

    elif method == "camera.capture":
        print("Processing Camera image capture request...")
        print(f"🔍 Received params: {params}")
        
        try:
            # Get device ID for file naming and S3 paths
            device_id = get_device_id()
            
            # Execute image capture
            capture_result = camera_capture_service.capture_image(params, device_id)
            print(f"🔍 Capture result: {capture_result}")
            
            if capture_result.get("success", True):
                local_image_path = capture_result.get('local_path')
                print(f"✅ Image captured successfully: {local_image_path}")
                
                # Initialize response with basic success data
                response = {
                    "success": True,
                    "image_size_bytes": capture_result.get("image_size_bytes", 0),
                    "capture_timestamp": capture_result.get("capture_timestamp", int(time.time() * 1000))
                }
                
                # Add image URL or base64 if available
                if "image_url" in capture_result:
                    response["image_url"] = capture_result["image_url"]
                if "image_base64" in capture_result:
                    response["image_base64"] = capture_result["image_base64"]

                # --- S3 Upload Logic Integration ---
                print("🔍 Starting S3 upload logic check...")
                # Check for S3 upload configuration (both nested and flat formats)
                s3_config = params.get("s3_upload")
                if not s3_config:
                    # Check for flat S3 parameters
                    if any(key in params for key in ["bucket", "prefix", "s3_bucket", "s3_prefix"]):
                        s3_config = {
                            "bucket": params.get("bucket") or params.get("s3_bucket"),
                            "prefix": params.get("prefix") or params.get("s3_prefix", ""),
                            "generate_presigned_url": params.get("generate_presigned_url", False),
                            "url_expiry_seconds": params.get("url_expiry_seconds", 3600)
                        }
                        print(f"🔍 Found flat S3 parameters, created config: {s3_config}")
                    else:
                        print("🔍 No S3 upload parameters found")
                else:
                    print(f"🔍 Found nested S3 config: {s3_config}")
                
                if s3_config and local_image_path:
                    print("🚚 S3 upload requested. Starting upload process...")
                    print(f"🔧 S3 config: {s3_config}")
                    print(f"📁 Local image path: {local_image_path}")
                    
                    # 1. Instantiate and configure the uploader
                    uploader = SimpleS3Uploader(device_id=device_id)
                    try:
                        uploader.setup_s3_credentials() # Uses environment variables
                        print("✅ S3 credentials configured successfully")
                    except Exception as cred_error:
                        print(f"❌ S3 credentials setup failed: {cred_error}")
                        print("💡 Please set AWS credentials via environment variables:")
                        print("   export AWS_ACCESS_KEY_ID=your_access_key")
                        print("   export AWS_SECRET_ACCESS_KEY=your_secret_key")
                        print("   export AWS_DEFAULT_REGION=us-east-1")
                        response["s3_upload_status"] = "failed"
                        response["s3_error"] = f"Credentials setup failed: {cred_error}"
                        # Continue with the response but mark S3 upload as failed
                        if rpc_id is not None:
                            client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                        return
                    
                    # 2. Prepare the S3 path with structure: bucket_name/{device_id}/prefix/timestamp/
                    bucket_name = s3_config.get("bucket")
                    raw_prefix = s3_config.get("prefix", "")
                    
                    timestamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
                    
                    # Build folder path: {device_id}/prefix/timestamp/
                    s3_folder_path = f"{device_id}/{raw_prefix}/{timestamp_str}"
                    
                    print(f"🪣 Bucket: {bucket_name}")
                    print(f"📁 Raw prefix: {raw_prefix}")
                    print(f"📁 Device ID: {device_id}")
                    print(f"📅 Timestamp: {timestamp_str}")
                    print(f"📁 Final S3 folder path: {s3_folder_path}")

                    # 3. Upload the file
                    print(f"📤 Uploading to S3: bucket={bucket_name}, folder={s3_folder_path}")
                    try:
                        upload_success = uploader.upload_file(
                            file_path=local_image_path,
                            bucket_name=bucket_name,
                            folder_path=s3_folder_path
                        )
                        
                        print(f"📊 Upload result: {upload_success}")
                        
                    except Exception as upload_error:
                        print(f"❌ S3 upload failed with error: {upload_error}")
                        upload_success = False
                        response["s3_upload_status"] = "failed"
                        response["s3_error"] = f"Upload failed: {upload_error}"
                    
                    # 4. If upload is successful, add the S3 location to the response
                    if upload_success:
                        filename = os.path.basename(local_image_path)
                        s3_key = f"{s3_folder_path.strip('/')}/{filename}"
                        s3_location = f"s3://{bucket_name}/{s3_key}"
                        response["s3_location"] = s3_location
                        print(f"🌍 S3 upload complete: {s3_location}")
                    else:
                        print("⚠️ S3 upload failed. Check uploader logs for details.")
                        # Optionally add an error note to the response
                        response["s3_upload_status"] = "failed"
                        response["s3_error"] = "Upload returned False"

                # --- End of S3 Upload Logic ---
                print("🔍 S3 upload logic completed")
                # Build the response (ensure all required fields are set)
                if "success" not in response:
                    response["success"] = True
                if "image_size_bytes" not in response:
                    response["image_size_bytes"] = capture_result.get("image_size_bytes", 0)
                if "capture_timestamp" not in response:
                    response["capture_timestamp"] = capture_result.get("capture_timestamp", int(time.time() * 1000))

            else:
                print(f"❌ Image capture failed: {capture_result.get('error', 'Unknown error')}")
                response = {
                    "success": False,
                    "error": capture_result.get("error", "Image capture failed"),
                    "timestamp": capture_result.get("timestamp", int(time.time() * 1000))
                }
        
        except Exception as e:
            print(f"❌ Camera capture failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "error": f"Camera capture failed: {e}",
                "timestamp": int(time.time() * 1000)
            }

    elif method == "camera.video.capture":
        print("Processing Camera video capture request...")
        print(f"🔍 Received params: {params}")
        
        try:
            # Get device ID for file naming and S3 paths
            device_id = get_device_id()
            
            # Execute video capture
            capture_result = camera_capture_service.capture_video(params, device_id)
            print(f"🔍 Capture result: {capture_result}")
            
            if capture_result.get("success", False):
                local_video_path = capture_result.get('local_path')
                print(f"✅ Video captured successfully: {local_video_path}")
                
                # Initialize response with basic success data
                response = {
                    "success": True,
                    "video_size_bytes": capture_result.get("video_size_bytes", 0),
                    "capture_timestamp": capture_result.get("capture_timestamp", int(time.time() * 1000)),
                    "duration_seconds": capture_result.get("duration_seconds", 0)
                }
                
                # Add video URL
                if "video_url" in capture_result:
                    response["video_url"] = capture_result["video_url"]

                # --- S3 Upload Logic Integration ---
                print("🔍 Starting S3 upload logic check...")
                # Check for S3 upload configuration (both nested and flat formats)
                s3_config = params.get("s3_upload")
                if not s3_config:
                    # Check for flat S3 parameters
                    if any(key in params for key in ["bucket", "prefix", "s3_bucket", "s3_prefix"]):
                        s3_config = {
                            "bucket": params.get("bucket") or params.get("s3_bucket"),
                            "prefix": params.get("prefix") or params.get("s3_prefix", ""),
                            "generate_presigned_url": params.get("generate_presigned_url", False),
                            "url_expiry_seconds": params.get("url_expiry_seconds", 3600)
                        }
                        print(f"🔍 Found flat S3 parameters, created config: {s3_config}")
                    else:
                        print("🔍 No S3 upload parameters found")
                else:
                    print(f"🔍 Found nested S3 config: {s3_config}")
                
                if s3_config and local_video_path:
                    print("🚚 S3 upload requested. Starting upload process...")
                    print(f"🔧 S3 config: {s3_config}")
                    print(f"📁 Local video path: {local_video_path}")
                    
                    # 1. Instantiate and configure the uploader
                    uploader = SimpleS3Uploader(device_id=device_id)
                    try:
                        uploader.setup_s3_credentials() # Uses environment variables
                        print("✅ S3 credentials configured successfully")
                    except Exception as cred_error:
                        print(f"❌ S3 credentials setup failed: {cred_error}")
                        print("💡 Please set AWS credentials via environment variables:")
                        print("   export AWS_ACCESS_KEY_ID=your_access_key")
                        print("   export AWS_SECRET_ACCESS_KEY=your_secret_key")
                        print("   export AWS_DEFAULT_REGION=us-east-1")
                        response["s3_upload_status"] = "failed"
                        response["s3_error"] = f"Credentials setup failed: {cred_error}"
                        # Continue with the response but mark S3 upload as failed
                        if rpc_id is not None:
                            client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
                        return
                    
                    # 2. Prepare the S3 path with structure: bucket_name/{device_id}/prefix/timestamp/
                    bucket_name = s3_config.get("bucket")
                    raw_prefix = s3_config.get("prefix", "")
                    
                    timestamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
                    
                    # Build folder path: {device_id}/prefix/timestamp/
                    s3_folder_path = f"{device_id}/{raw_prefix}/{timestamp_str}"
                    
                    print(f"🪣 Bucket: {bucket_name}")
                    print(f"📁 Raw prefix: {raw_prefix}")
                    print(f"📁 Device ID: {device_id}")
                    print(f"📅 Timestamp: {timestamp_str}")
                    print(f"📁 Final S3 folder path: {s3_folder_path}")

                    # 3. Upload the file
                    print(f"📤 Uploading to S3: bucket={bucket_name}, folder={s3_folder_path}")
                    try:
                        upload_success = uploader.upload_file(
                            file_path=local_video_path,
                            bucket_name=bucket_name,
                            folder_path=s3_folder_path
                        )
                        
                        print(f"📊 Upload result: {upload_success}")
                        
                    except Exception as upload_error:
                        print(f"❌ S3 upload failed with error: {upload_error}")
                        upload_success = False
                        response["s3_upload_status"] = "failed"
                        response["s3_error"] = f"Upload failed: {upload_error}"
                    
                    # 4. If upload is successful, add the S3 location to the response
                    if upload_success:
                        filename = os.path.basename(local_video_path)
                        s3_key = f"{s3_folder_path.strip('/')}/{filename}"
                        s3_location = f"s3://{bucket_name}/{s3_key}"
                        response["s3_location"] = s3_location
                        print(f"🌍 S3 upload complete: {s3_location}")
                    else:
                        print("⚠️ S3 upload failed. Check uploader logs for details.")
                        # Optionally add an error note to the response
                        response["s3_upload_status"] = "failed"
                        response["s3_error"] = "Upload returned False"

                # --- End of S3 Upload Logic ---
                print("🔍 S3 upload logic completed")
                # Build the response (ensure all required fields are set)
                if "success" not in response:
                    response["success"] = True
                if "video_size_bytes" not in response:
                    response["video_size_bytes"] = capture_result.get("video_size_bytes", 0)
                if "capture_timestamp" not in response:
                    response["capture_timestamp"] = capture_result.get("capture_timestamp", int(time.time() * 1000))
                if "duration_seconds" not in response:
                    response["duration_seconds"] = capture_result.get("duration_seconds", 0)
                
            else:
                print(f"❌ Video capture failed: {capture_result.get('error', 'Unknown error')}")
                response = {
                    "success": False,
                    "error": capture_result.get("error", "Video capture failed"),
                    "timestamp": capture_result.get("timestamp", int(time.time() * 1000))
                }
        
        except Exception as e:
            print(f"❌ Camera video capture failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "error": f"Camera video capture failed: {e}",
                "timestamp": int(time.time() * 1000)
            }

    elif method == "camera.stream.start":
        print("Processing Camera stream start request...")
        
        try:
            # Get device ID for stream naming and endpoints
            device_id = get_device_id()
            
            # Execute stream start
            stream_result = camera_streaming_service.start_stream(params, device_id)
            
            if stream_result.get("success", False):
                print(f"✅ Stream started successfully: {stream_result.get('stream_info', {}).get('stream_id', 'unknown')}")
                response = stream_result
            else:
                print(f"❌ Stream start failed: {stream_result.get('error', 'Unknown error')}")
                response = stream_result
        
        except Exception as e:
            print(f"❌ Camera stream start failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "error": f"Camera stream start failed: {e}",
                "timestamp": int(time.time() * 1000)
            }

    elif method == "camera.stream.stop":
        print("Processing Camera stream stop request...")
        
        try:
            # Get device ID for S3 paths
            device_id = get_device_id()
            
            # Execute stream stop
            stream_result = camera_streaming_service.stop_stream(params, device_id)
            
            if stream_result.get("success", False):
                print(f"✅ Stream stopped successfully: {params.get('stream_id', 'unknown')}")
                response = stream_result
            else:
                print(f"❌ Stream stop failed: {stream_result.get('error', 'Unknown error')}")
                response = stream_result
        
        except Exception as e:
            print(f"❌ Camera stream stop failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "error": f"Camera stream stop failed: {e}",
                "timestamp": int(time.time() * 1000)
            }

    elif method == "sensor.calibrate":
        print("Processing Sensor calibration request...")
        sensor_type = params.get("sensor_type", "unknown")
        calibration_type = params.get("calibration_type", "unknown")
        reference_values = params.get("reference_values", {})
        
        print(f"🔧 Sensor calibration: {sensor_type}, type: {calibration_type}")
        print(f"🔧 Reference values: {reference_values}")
        
        try:
            if sensor_type == "ultrasonic":
                if calibration_type in ["zero", "span", "full"]:
                    # Extract threshold value from reference_values
                    threshold_cm = reference_values.get("threshold_cm")
                    
                    if threshold_cm is not None:
                        # Validate threshold range
                        if not (5 <= threshold_cm <= 200):
                            response = {
                                "success": False,
                                "data": {
                                    "status": "error",
                                    "message": f"Invalid threshold_cm: {threshold_cm}. Must be between 5 and 200 cm"
                                },
                                "timestamp": int(time.time() * 1000)
                            }
                        else:
                            # Apply calibration to all ultrasonic sensors
                            calibration_results = {}
                            all_success = True
                            
                            for sensor_id in range(1, 5):
                                success = proximity_detector.update_sensor_threshold(sensor_id, threshold_cm)
                                calibration_results[f"sensor_{sensor_id}"] = {
                                    "threshold_cm": threshold_cm,
                                    "calibrated": success
                                }
                                if not success:
                                    all_success = False
                            
                            if all_success:
                                print(f"✅ Ultrasonic calibration completed: All sensors set to {threshold_cm}cm threshold")
                                
                                # Get current proximity detector status for response
                                proximity_status = proximity_detector.get_status()
                                
                                response = {
                                    "success": True,
                                    "data": {
                                        "status": "calibrated",
                                        "message": f"Ultrasonic {calibration_type} calibration completed",
                                        "sensor_type": sensor_type,
                                        "calibration_type": calibration_type,
                                        "threshold_cm": threshold_cm,
                                        "sensors_calibrated": calibration_results,
                                        "proximity_detection_status": {
                                            "detecting": proximity_status.get("detecting", False),
                                            "sensor_thresholds": proximity_status.get("sensor_thresholds", {}),
                                            "confidence_threshold": proximity_status.get("confidence_threshold", 0.8)
                                        }
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                            else:
                                print(f"⚠️ Ultrasonic calibration partially failed")
                                response = {
                                    "success": False,
                                    "data": {
                                        "status": "partial_failure", 
                                        "message": f"Ultrasonic {calibration_type} calibration partially failed",
                                        "sensor_type": sensor_type,
                                        "calibration_type": calibration_type,
                                        "threshold_cm": threshold_cm,
                                        "sensors_calibrated": calibration_results
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                    else:
                        response = {
                            "success": False,
                            "data": {
                                "status": "error",
                                "message": "Missing threshold_cm in reference_values"
                            },
                            "timestamp": int(time.time() * 1000)
                        }
                else:
                    response = {
                        "success": False,
                        "data": {
                            "status": "error",
                            "message": f"Unsupported calibration_type '{calibration_type}' for ultrasonic sensors. Supported: zero, span, full"
                        },
                        "timestamp": int(time.time() * 1000)
                    }
            else:
                response = {
                    "success": False,
                    "data": {
                        "status": "error",
                        "message": f"Unsupported sensor_type '{sensor_type}'. Currently supported: ultrasonic"
                    },
                    "timestamp": int(time.time() * 1000)
                }
        
        except Exception as e:
            print(f"❌ Sensor calibration failed: {e}")
            import traceback
            traceback.print_exc()
            response = {
                "success": False,
                "data": {
                    "status": "error",
                    "message": f"Sensor calibration failed: {e}"
                },
                "timestamp": int(time.time() * 1000)
            }

    elif method == "openPort":
        port = params.get("port", "unknown")
        print(f"Opening port {port}...")
        
        try:
            # Validate port number
            if port == "unknown" or not isinstance(port, (int, str)):
                response = {
                    "success": False,
                    "error": "Invalid port number provided"
                }
            else:
                port_num = int(port)
                if not (1 <= port_num <= 65535):
                    response = {
                        "success": False,
                        "error": f"Port number {port_num} is out of valid range (1-65535)"
                    }
                else:
                    # Initialize open_ports dictionary if it doesn't exist
                    if 'open_ports' not in globals():
                        global open_ports
                        open_ports = {}
                    
                    # Check if port is already open
                    if port_num in open_ports:
                        response = {
                            "success": False,
                            "error": f"Port {port_num} is already open"
                        }
                    else:
                        # Try to open the port
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        
                        try:
                            sock.bind(('0.0.0.0', port_num))
                            sock.listen(5)
                            
                            open_ports[port_num] = sock
                            
                            print(f"✅ Port {port_num} opened and listening")
                            
                            response = {
                                "success": True,
                                "message": f"Port {port_num} opened successfully",
                                "port_details": {
                                    "port_number": port_num,
                                    "status": "listening",
                                    "bind_address": "0.0.0.0",
                                    "max_connections": 5,
                                    "opened_at": int(time.time() * 1000)
                                }
                            }
                            
                        except OSError as e:
                            if e.errno == 98:  # Address already in use
                                response = {
                                    "success": False,
                                    "error": f"Port {port_num} is already in use"
                                }
                            elif e.errno == 13:  # Permission denied
                                response = {
                                    "success": False,
                                    "error": f"Permission denied to bind to port {port_num} (try ports > 1024 for non-root users)"
                                }
                            else:
                                response = {
                                    "success": False,
                                    "error": f"Failed to open port {port_num}: {str(e)}"
                                }
                            sock.close()
                    
        except ValueError:
            response = {
                "success": False,
                "error": f"Invalid port number format: {port}"
            }
        except Exception as e:
            response = {
                "success": False,
                "error": f"Unexpected error opening port {port}: {str(e)}"
            }

    elif method == "rebootDevice":
        print("Simulating device reboot...")
        response = {
            "success": True,
            "message": "Device reboot scheduled",
            "reboot_time": int(time.time() * 1000)
        }

    elif method == "setChargingRate":
        rate = params.get("rate_kw", 0)
        print(f"Simulating charging rate update to {rate} kW...")
        response = {
            "success": True,
            "message": f"Charging rate set to {rate} kW"
        }

    elif method == "lockPort":
        port = params.get("port", "unknown")
        print(f"Locking port {port}...")
        
        try:
            # Validate port number
            if port == "unknown" or not isinstance(port, (int, str)):
                response = {
                    "success": False,
                    "error": "Invalid port number provided"
                }
            else:
                port_num = int(port)
                if not (1 <= port_num <= 65535):
                    response = {
                        "success": False,
                        "error": f"Port number {port_num} is out of valid range (1-65535)"
                    }
                else:
                    # Initialize locked_ports dictionary if it doesn't exist
                    if 'locked_ports' not in globals():
                        global locked_ports
                        locked_ports = {}
                    
                    # Check if port is already locked
                    if port_num in locked_ports:
                        response = {
                            "success": False,
                            "error": f"Port {port_num} is already locked"
                        }
                    else:
                        # Check if port is currently open and close it first
                        if 'open_ports' in globals() and port_num in open_ports:
                            try:
                                # Close the socket before locking
                                sock = open_ports[port_num]
                                sock.close()
                                del open_ports[port_num]
                                print(f"Closed port {port_num} before locking")
                            except Exception as e:
                                print(f"Warning: Error closing port {port_num} before locking: {e}")
                        
                        # Lock the port by marking it as locked
                        locked_ports[port_num] = {
                            "locked_at": int(time.time() * 1000),
                            "status": "locked"
                        }
                        
                        print(f"🔒 Port {port_num} locked successfully")
                        
                        response = {
                            "success": True,
                            "message": f"Port {port_num} locked successfully",
                            "port_details": {
                                "port_number": port_num,
                                "status": "locked",
                                "locked_at": int(time.time() * 1000),
                                "access_blocked": True
                            }
                        }
                    
        except ValueError:
            response = {
                "success": False,
                "error": f"Invalid port number format: {port}"
            }
        except Exception as e:
            response = {
                "success": False,
                "error": f"Unexpected error locking port {port}: {str(e)}"
            }

    elif method == "database.status":
        print("Processing Database status request...")
        try:
            from .database_service import get_database_service
            service = get_database_service()
            status = service.get_status()
            
            response = {
                "success": True,
                "data": status,
                "timestamp": int(time.time() * 1000)
            }
            
        except Exception as e:
            print(f"❌ Database status failed: {e}")
            response = {
                "success": False,
                "data": {
                    "status": "error",
                    "message": f"Database status failed: {e}"
                },
                "timestamp": int(time.time() * 1000)
            }

    elif method == "unlockPort":
        port = params.get("port", "unknown")
        print(f"Unlocking port {port}...")
        
        try:
            # Validate port number
            if port == "unknown" or not isinstance(port, (int, str)):
                response = {
                    "success": False,
                    "error": "Invalid port number provided"
                }
            else:
                port_num = int(port)
                if not (1 <= port_num <= 65535):
                    response = {
                        "success": False,
                        "error": f"Port number {port_num} is out of valid range (1-65535)"
                    }
                else:
                    # Check if we have the port in our locked_ports dictionary
                    if 'locked_ports' in globals() and port_num in locked_ports:
                        try:
                            # Remove the port from locked ports
                            locked_info = locked_ports[port_num]
                            del locked_ports[port_num]
                            
                            print(f"🔓 Port {port_num} unlocked successfully")
                            
                            response = {
                                "success": True,
                                "message": f"Port {port_num} unlocked successfully",
                                "port_details": {
                                    "port_number": port_num,
                                    "status": "unlocked",
                                    "unlocked_at": int(time.time() * 1000),
                                    "was_locked_at": locked_info.get("locked_at"),
                                    "access_restored": True
                                }
                            }
                            
                        except Exception as e:
                            response = {
                                "success": False,
                                "error": f"Error unlocking port {port_num}: {str(e)}"
                            }
                    else:
                        response = {
                            "success": False,
                            "error": f"Port {port_num} is not currently locked or was not locked by this application"
                        }
                    
        except ValueError:
            response = {
                "success": False,
                "error": f"Invalid port number format: {port}"
            }
        except Exception as e:
            response = {
                "success": False,
                "error": f"Unexpected error unlocking port {port}: {str(e)}"
            }

    elif method == "closePort":
        port = params.get("port", "unknown")
        print(f"Closing port {port}...")
        
        try:
            # Validate port number
            if port == "unknown" or not isinstance(port, (int, str)):
                response = {
                    "success": False,
                    "error": "Invalid port number provided"
                }
            else:
                port_num = int(port)
                if not (1 <= port_num <= 65535):
                    response = {
                        "success": False,
                        "error": f"Port number {port_num} is out of valid range (1-65535)"
                    }
                else:
                    # Check if we have the port in our open_ports dictionary
                    if 'open_ports' in globals() and port_num in open_ports:
                        try:
                            # Close the socket
                            sock = open_ports[port_num]
                            sock.close()
                            
                            # Remove from our tracking dictionary
                            del open_ports[port_num]
                            
                            print(f"✅ Port {port_num} closed successfully")
                            
                            response = {
                                "success": True,
                                "message": f"Port {port_num} closed successfully",
                                "port_details": {
                                    "port_number": port_num,
                                    "status": "closed",
                                    "closed_at": int(time.time() * 1000)
                                }
                            }
                            
                        except Exception as e:
                            response = {
                                "success": False,
                                "error": f"Error closing port {port_num}: {str(e)}"
                            }
                    else:
                        response = {
                            "success": False,
                            "error": f"Port {port_num} is not currently open or was not opened by this application"
                        }
                    
        except ValueError:
            response = {
                "success": False,
                "error": f"Invalid port number format: {port}"
            }
        except Exception as e:
            response = {
                "success": False,
                "error": f"Unexpected error closing port {port}: {str(e)}"
            }



    if rpc_id is not None:
        client.publish(f"v1/devices/me/rpc/response/{rpc_id}", json.dumps(response))
        print(f"RPC response sent: {response}")
    else:
        print("Missing RPC ID. Cannot send response.")

client.on_message = on_message
client.connect(MQTT_HOST, 1883, 60)

# def simulate_telemetry():
#     print("Starting controlled telemetry service...")
    
#     # Initialize telemetry manager and start session
#     telemetry_manager = get_telemetry_manager()
#     telemetry_manager.start_session()
    
#     while True:
#         try:
#             with collection_control_lock:
#                 is_active = collection_control["active"]
#                 current_sampling_rate = collection_control["global_sampling_rate_hz"]
#                 sensors_state = collection_control["sensors"].copy()
#                 current_mode = collection_control["mode"]
            
#             if not is_active:
#                 # Collection is paused/stopped
#                 time.sleep(1)  # Short sleep when inactive
#                 continue
            
#             # Calculate sleep interval based on sampling rate
#             sleep_interval = 1.0 / current_sampling_rate if current_sampling_rate > 0 else 10.0
            
#             # Build payload based on active sensors
#             payload = {}
            
#             # Add LiDAR data if active - check both collection control AND LiDAR control service
#             if sensors_state.get("lidar", {}).get("active", False):
#                 try:
#                     # Check if LiDAR control service is actually active
#                     lidar_service_params = lidar_control_service.get_effective_generation_params()
#                     lidar_service_active = lidar_service_params.get("active", False)
                    
#                     if lidar_service_active:
#                         # Get LiDAR telemetry data in ThingsBoard format
#                         lidar_telemetry = get_lidar_telemetry_data()
                        
#                         if lidar_telemetry and "values" in lidar_telemetry:
#                             # Add LiDAR values to payload
#                             payload.update(lidar_telemetry["values"])
                            
#                             print(f"LiDAR telemetry: {len(lidar_telemetry['values'])} metrics, point_count: {lidar_telemetry['values'].get('lidar.point_count', 0)}")
                            
#                             # Save LiDAR telemetry data to file
#                             save_lidar_telemetry_to_file(lidar_telemetry)
#                     else:
#                         print(f"🛑 LiDAR service is stopped - skipping telemetry generation")
                    
#                     # High frequency mode for LiDAR (only if service is active)
#                     if lidar_service_active and sensors_state["lidar"]["mode"] == "high_frequency":
#                         # Add additional LiDAR summary data
#                         lidar_summary = get_lidar_summary()
#                         payload.update(lidar_summary)
                        
#                         print(f"High frequency LiDAR: Added {len(lidar_summary)} additional metrics")
                        
#                 except Exception as e:
#                     print(f"LiDAR data collection error: {e}")
            
#             # Add environmental data if active (now using actual environmental services)
#             if sensors_state.get("environmental", {}).get("active", False):
#                 try:
#                     # Get actual environmental telemetry data
#                     env_telemetry = environment_conditions_service.get_telemetry_data()
#                     air_telemetry = air_quality_monitor_service.get_telemetry_data()
#                     light_telemetry = light_level_monitor_service.get_telemetry_data()
                    
#                     # Publish each environmental sensor type separately to MQTT
#                     if env_telemetry and "values" in env_telemetry:
#                         publish_environmental_telemetry(env_telemetry, "environment")
#                         # Also save to file
#                         environment_conditions_service.save_telemetry_to_file(env_telemetry)
                    
#                     if air_telemetry and "values" in air_telemetry:
#                         publish_environmental_telemetry(air_telemetry, "air_quality")
#                         # Also save to file
#                         air_quality_monitor_service.save_telemetry_to_file(air_telemetry)
                    
#                     if light_telemetry and "values" in light_telemetry:
#                         publish_environmental_telemetry(light_telemetry, "light_level")
#                         # Also save to file
#                         light_level_monitor_service.save_telemetry_to_file(light_telemetry)
                    
#                     # Add environmental data to main payload for combined telemetry
#                     if env_telemetry and "values" in env_telemetry:
#                         payload.update(env_telemetry["values"])
#                     if air_telemetry and "values" in air_telemetry:
#                         payload.update(air_telemetry["values"])
#                     if light_telemetry and "values" in light_telemetry:
#                         payload.update(light_telemetry["values"])
                        
#                 except Exception as e:
#                     print(f"Environmental data collection error: {e}")
#                     # Fallback to basic simulation
#                     env_data = {
#                         "environment.temperature_c": round(random.uniform(20, 40), 2),
#                         "environment.humidity_percent": round(random.uniform(30, 70), 2),
#                     }
#                     payload.update(env_data)
            
#             # Ultrasonic data is now handled by dedicated streaming service via ultrasonic.control
#             # No need to generate ultrasonic telemetry here anymore
            
#             # Add camera data if active
#             if sensors_state.get("camera", {}).get("active", False):
#                 camera_data = {
#                     "camera.occupancy.detected": random.choice([True, False]),
#                 }
                
#                 # High frequency mode for camera
#                 if sensors_state["camera"]["mode"] == "high_frequency":
#                     camera_data.update({
#                         "camera.motion_detected": random.choice([True, False]),
#                         "camera.light_level": random.randint(0, 255),
#                         "camera.focus_quality": round(random.uniform(0.5, 1.0), 2)
#                     })
                
#                 payload.update(camera_data)
                
#                 print(f"Camera telemetry: occupancy={camera_data.get('camera.occupancy.detected', False)}, motion={camera_data.get('camera.motion_detected', False)}")
            
#             # Add system data (always included)
#             payload.update({
#                 "power.grid_power_w": round(random.uniform(80, 150), 2),
#                 "power.energy_kwh": round(random.uniform(0.1, 20.0), 2),
#                 "system.cpu_usage_percent": round(random.uniform(10, 90), 2),
#                 "system.memory_usage_mb": random.randint(100, 512),
#                 "system.uptime_sec": int(time.time()),
#                 "status.occupied": random.choice([True, False]),
#                 "status.port1.connected": random.choice([True, False]),
#                 "status.port2.connected": random.choice([True, False]),
#                 "data_collection.mode": current_mode,
#                 "data_collection.sampling_rate_hz": current_sampling_rate
#             })
            
#             # Publish telemetry if we have data
#             if payload:
#                 client.publish("v1/devices/me/telemetry", json.dumps(payload))
#                 print(f"Telemetry sent: {len(payload)} metrics (mode: {current_mode}, rate: {current_sampling_rate}Hz)")
                
#                 # Save telemetry data to local storage
#                 try:
#                     save_telemetry_data(payload)
#                 except Exception as e:
#                     print(f"⚠️ Failed to save telemetry data: {e}")
            
#             time.sleep(sleep_interval)
            
#         except Exception as e:
#             print(f"Telemetry error: {e}")
#             time.sleep(5)  # Short sleep on error

# threading.Thread(target=simulate_telemetry, daemon=True).start()
client.loop_forever()
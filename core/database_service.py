import os
import json
import time
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
import threading

class DatabaseService:
    """Service to deploy SQLite Docker container and initialize database tables"""
    
    def __init__(self):
        self.lock_file_path = Path("data/database/.db_service_lock")
        self.db_file_path = Path("data/database/papaya-parking-data.db")
        self.container_name = "sqlite-papaya-parking-data"
        self.port = 8081  # SQLite web interface port (changed from 8080 to avoid conflicts)
        
    def is_service_already_run(self):
        """Check if the database service has already been run"""
        if not self.lock_file_path.exists():
            return False
            
        try:
            with open(self.lock_file_path, 'r') as f:
                lock_data = json.load(f)
                
            # Check if container is still running
            if self._is_container_running(lock_data.get("container_name")):
                return True
            else:
                # Container not running, remove stale lock file
                self.lock_file_path.unlink()
                return False
                
        except (json.JSONDecodeError, FileNotFoundError):
            # Corrupted lock file, remove it
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()
            return False
            
        return False
    
    def _is_container_running(self, container_name):
        """Check if Docker container is running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=False
            )
            return container_name in result.stdout
        except Exception:
            return False
    
    def _is_port_in_use(self, port):
        """Check if a port is already in use"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return False
        except OSError:
            return True
    
    def _create_database_directory(self):
        """Ensure database directory exists"""
        self.db_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _deploy_sqlite_docker(self):
        """Deploy SQLite Docker container"""
        try:
            print("🐳 Deploying SQLite Docker container...")
            
            # Check if port is available
            if self._is_port_in_use(self.port):
                print(f"⚠️ Port {self.port} is already in use, trying alternative port...")
                # Try alternative ports
                for alt_port in [8082, 8083, 8084, 8085]:
                    if not self._is_port_in_use(alt_port):
                        self.port = alt_port
                        print(f"✅ Using alternative port: {self.port}")
                        break
                else:
                    print("❌ No available ports found in range 8081-8085")
                    return False
            
            # Stop and remove existing container if it exists
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True, check=False
            )
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True, check=False
            )
            
            # Create database directory
            self._create_database_directory()
            
            # Deploy SQLite container with volume mount
            cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-p", f"{self.port}:8080",
                "-v", f"{self.db_file_path.parent.absolute()}:/data",
                "-e", "SQLITE_DATABASE=/data/papaya-parking-data.db",
                "coleifer/sqlite-web:latest"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()
            
            print(f"✅ SQLite Docker container deployed successfully!")
            print(f"   Container ID: {container_id}")
            print(f"   Web Interface: http://localhost:{self.port}")
            print(f"   Database Path: {self.db_file_path}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to deploy SQLite Docker container: {e}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error deploying SQLite Docker: {e}")
            return False
    
    def _create_database_tables(self):
        """Create the required database tables"""
        try:
            print("🗄️ Creating database tables...")
            
            # Fix permissions if database file exists but is owned by root
            if self.db_file_path.exists():
                try:
                    import pwd
                    current_user = pwd.getpwuid(os.getuid()).pw_name
                    subprocess.run(["sudo", "chown", f"{current_user}:{current_user}", str(self.db_file_path)], 
                                 capture_output=True, check=False)
                    print(f"✅ Fixed database file permissions for user: {current_user}")
                except Exception as perm_error:
                    print(f"⚠️ Could not fix permissions: {perm_error}")
            
            # Connect to database (will create if doesn't exist)
            conn = sqlite3.connect(str(self.db_file_path))
            cursor = conn.cursor()
            
            # Create telemetry table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp BIGINT NOT NULL,
                    sensor_type VARCHAR(50) NOT NULL,
                    data_json TEXT NOT NULL,
                    sync_status INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for telemetry
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON telemetry(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON telemetry(sync_status)")
            
            # Create event log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(100) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    message TEXT,
                    details_json TEXT,
                    timestamp BIGINT NOT NULL,
                    acknowledged INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for event log
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON event_log(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON event_log(timestamp)")
            
            # Commit changes
            conn.commit()
            conn.close()
            
            print("✅ Database tables created successfully!")
            print("   - telemetry table with indexes")
            print("   - event_log table with indexes")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create database tables: {e}")
            return False
    
    def _create_lock_file(self):
        """Create lock file to prevent multiple runs"""
        try:
            lock_data = {
                "pid": os.getpid(),
                "started_at": time.time(),
                "container_name": self.container_name,
                "db_file": str(self.db_file_path),
                "port": self.port,
                "web_interface": f"http://localhost:{self.port}"
            }
            
            with open(self.lock_file_path, 'w') as f:
                json.dump(lock_data, f, indent=2)
                
            print("🔒 Service lock file created")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create lock file: {e}")
            return False
    
    def _wait_for_container_ready(self, timeout_seconds=30):
        """Wait for container to be ready"""
        print("⏳ Waiting for container to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            if self._is_container_running(self.container_name):
                # Additional check: try to connect to web interface
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.port}", timeout=5)
                    if response.status_code == 200:
                        print("✅ Container is ready and responding!")
                        return True
                except:
                    pass
            time.sleep(2)
        
        print("⚠️ Container ready timeout - continuing anyway")
        return False
    
    def run_once(self):
        """Run the database service once"""
        if self.is_service_already_run():
            print("ℹ️ Database service already running - skipping initialization")
            return True
        
        print("🚀 Starting database service initialization...")
        
        # Deploy SQLite Docker container
        if not self._deploy_sqlite_docker():
            return False
        
        # Wait for container to be ready
        self._wait_for_container_ready()
        
        # Create database tables
        if not self._create_database_tables():
            return False
        
        # Create lock file
        if not self._create_lock_file():
            return False
        
        print("🎉 Database service initialization completed successfully!")
        print(f"📊 Database: {self.db_file_path}")
        print(f"🌐 Web Interface: http://localhost:{self.port}")
        print(f"🔒 Lock File: {self.lock_file_path}")
        
        return True
    
    def get_status(self):
        """Get current service status"""
        try:
            if not self.lock_file_path.exists():
                return {
                    "status": "not_initialized",
                    "message": "Database service has not been initialized"
                }
            
            with open(self.lock_file_path, 'r') as f:
                lock_data = json.load(f)
            
            container_running = self._is_container_running(lock_data.get("container_name"))
            
            return {
                "status": "running" if container_running else "stopped",
                "container_name": lock_data.get("container_name"),
                "db_file": lock_data.get("db_file"),
                "port": lock_data.get("port"),
                "web_interface": lock_data.get("web_interface"),
                "started_at": lock_data.get("started_at"),
                "container_running": container_running
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get status: {e}"
            }
    
    def cleanup(self):
        """Cleanup resources (for testing/debugging)"""
        try:
            # Remove lock file
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()
                print("🔓 Lock file removed")
            
            # Stop and remove container
            subprocess.run(["docker", "stop", self.container_name], capture_output=True, check=False)
            subprocess.run(["docker", "rm", self.container_name], capture_output=True, check=False)
            print("🐳 Container stopped and removed")
            
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return False

# Global instance
_database_service = None

def get_database_service():
    """Get the global database service instance"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service

def initialize_database_service():
    """Initialize the database service (runs once)"""
    service = get_database_service()
    return service.run_once()

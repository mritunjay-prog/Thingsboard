# Database Service

This service automatically deploys a SQLite Docker container and initializes the database with required tables when `api.py` starts. It runs only once per session to prevent duplicate initialization.

## Features

- **One-time initialization**: Service runs only once when `api.py` starts
- **Docker deployment**: Automatically deploys SQLite container with web interface
- **Table creation**: Creates required database tables with proper indexes
- **Lock mechanism**: Prevents multiple runs using a lock file
- **Health monitoring**: Checks container status and web interface availability

## Database Tables

### Telemetry Table
```sql
CREATE TABLE telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp BIGINT NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    data_json TEXT NOT NULL,
    sync_status INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_timestamp ON telemetry(timestamp);
CREATE INDEX idx_sync_status ON telemetry(sync_status);
```

### Event Log Table
```sql
CREATE TABLE event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    details_json TEXT,
    timestamp BIGINT NOT NULL,
    acknowledged INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_event_type ON event_log(event_type);
CREATE INDEX idx_timestamp ON event_log(timestamp);
```

## How It Works

1. **Startup Check**: When `api.py` starts, it checks if the database service has already run
2. **Lock File**: Uses `data/database/.db_service_lock` to track service state
3. **Container Deployment**: Deploys SQLite Docker container if not already running
4. **Table Creation**: Creates database tables with proper schema and indexes
5. **Web Interface**: Provides SQLite web interface at `http://localhost:8080`

## Docker Container

- **Image**: `coleifer/sqlite-web:latest`
- **Port**: 8080
- **Volume Mount**: `./data/database:/data`
- **Database File**: `papaya-parking-data.db`

## RPC Commands

### Check Database Status
```json
{
    "method": "database.status",
    "params": {}
}
```

Response:
```json
{
    "success": true,
    "data": {
        "status": "running",
        "container_name": "sqlite-papaya-parking-data",
        "db_file": "data/database/papaya-parking-data.db",
        "port": 8080,
        "web_interface": "http://localhost:8080",
        "started_at": 1756658264.448968,
        "container_running": true
    },
    "timestamp": 1756658264000
}
```

## Manual Management

### Start with Docker Compose
```bash
docker-compose -f docker-compose.sqlite.yml up -d
```

### Stop Container
```bash
docker stop sqlite-papaya-parking-data
docker rm sqlite-papaya-parking-data
```

### Access Web Interface
Open `http://localhost:8080` in your browser to access the SQLite web interface.

### View Database File
The database file is located at `data/database/papaya-parking-data.db`

## Troubleshooting

### Container Not Starting
- Check if Docker is running: `docker ps`
- Check Docker logs: `docker logs sqlite-papaya-parking-data`
- Ensure port 8080 is available

### Lock File Issues
- Remove lock file: `rm data/database/.db_service_lock`
- Restart `api.py`

### Database Connection Issues
- Verify container is running: `docker ps | grep sqlite`
- Check web interface: `curl http://localhost:8080`
- Verify database file exists and has proper permissions

## Configuration

The service uses default configuration but can be customized by modifying:
- Port number in `DatabaseService.__init__()`
- Container name in `DatabaseService.__init__()`
- Database file path in `DatabaseService.__init__()`
- Docker image in `_deploy_sqlite_docker()`

## Dependencies

- Docker installed and running
- Python `sqlite3` module (built-in)
- Python `requests` module (for health checks)
- Port 8080 available



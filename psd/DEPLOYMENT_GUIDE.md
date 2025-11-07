# VM Deployment Requirements & Procedure

## 1. VM Requirements

### Hardware Specifications
- **CPU**: 4 cores minimum (8 cores recommended)
- **RAM**: 16 GB minimum (32 GB recommended)
- **Storage**: 100 GB SSD minimum (200 GB recommended)
- **Network**: 1 Gbps network interface

### Operating System
- **OS**: Ubuntu 22.04 LTS (Server)
- **Architecture**: x86_64 (AMD64)
- **Kernel**: 5.15 or later

### Network Configuration
- **Static IP**: Assign a static IP address
- **DNS**: Configure DNS resolution
- **Firewall Ports**:
  - 80 (HTTP)
  - 443 (HTTPS)
  - 8000 (API - internal only)
  - 5432 (PostgreSQL - internal only)
  - 5000 (OSRM - internal only)
  - 22 (SSH - restricted to admin IPs)

---

## 2. Pre-Installation Setup

### 2.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 2.2 Create Application User
```bash
sudo adduser --system --group --home /opt/zone-generator zoneapp
sudo usermod -aG sudo zoneapp  # If admin access needed
```

### 2.3 Install Base Dependencies
```bash
# Essential tools
sudo apt install -y git curl wget vim htop net-tools

# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Build tools (for Python packages)
sudo apt install -y build-essential libssl-dev libffi-dev

# PostgreSQL client libraries
sudo apt install -y libpq-dev
```

---

## 3. Database Installation

### 3.1 Install PostgreSQL + PostGIS
```bash
# Install PostgreSQL 15
sudo apt install -y postgresql-15 postgresql-contrib-15

# Install PostGIS
sudo apt install -y postgresql-15-postgis-3

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3.2 Configure PostgreSQL
```bash
# Switch to postgres user
sudo -u postgres psql

# Run in psql:
CREATE DATABASE zone_generator;
CREATE USER zoneapp WITH ENCRYPTED PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE zone_generator TO zoneapp;
\c zone_generator
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
\q
```

### 3.3 Configure PostgreSQL Authentication
```bash
sudo vim /etc/postgresql/15/main/pg_hba.conf

# Add line (before the "peer" lines):
local   zone_generator    zoneapp                                 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3.4 Test Database Connection
```bash
psql -U zoneapp -d zone_generator -h localhost
# Enter password when prompted
# Should connect successfully
\q
```

---

## 4. OSRM Installation (Docker)

### 4.1 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install -y docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 4.2 Download OSM Data
```bash
# Create OSRM directory
sudo mkdir -p /opt/osrm/data
cd /opt/osrm/data

# Download Saudi Arabia OSM data
wget https://download.geofabrik.de/asia/saudi-arabia-latest.osm.pbf

# Verify download
ls -lh saudi-arabia-latest.osm.pbf
```

### 4.3 Process OSM Data with OSRM
```bash
# Extract (10-20 minutes)
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:latest \
  osrm-extract -p /opt/car.lua /data/saudi-arabia-latest.osm.pbf

# Contract (5-10 minutes)
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:latest \
  osrm-contract /data/saudi-arabia-latest.osrm

# Partition (optional, for MLD)
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:latest \
  osrm-partition /data/saudi-arabia-latest.osrm

# Customize (optional, for MLD)
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:latest \
  osrm-customize /data/saudi-arabia-latest.osrm
```

### 4.4 Create OSRM Service
```bash
# Create docker-compose.yml
sudo vim /opt/osrm/docker-compose.yml
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  osrm:
    image: ghcr.io/project-osrm/osrm-backend:latest
    container_name: osrm-backend
    command: osrm-routed --algorithm mld /data/saudi-arabia-latest.osrm
    volumes:
      - ./data:/data
    ports:
      - "5000:5000"
    restart: unless-stopped
    mem_limit: 8g
```

### 4.5 Start OSRM Service
```bash
cd /opt/osrm
docker-compose up -d

# Check logs
docker-compose logs -f

# Test OSRM
curl "http://localhost:5000/route/v1/driving/46.6753,24.7136;46.7,24.72?overview=false"
# Should return JSON with route data
```

---

## 5. Application Installation

### 5.1 Clone Repository
```bash
sudo mkdir -p /opt/zone-generator
sudo chown zoneapp:zoneapp /opt/zone-generator
cd /opt/zone-generator

# Clone code (replace with actual repository)
git clone https://github.com/your-org/zone-generator.git .

# Or upload files manually
```

### 5.2 Create Python Virtual Environment
```bash
cd /opt/zone-generator
python3.11 -m venv venv
source venv/bin/activate
```

### 5.3 Install Python Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installations
python -c "import fastapi; print('FastAPI OK')"
python -c "import ortools; print('OR-Tools OK')"
python -c "import sklearn; print('scikit-learn OK')"
```

**requirements.txt**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
pandas==2.1.3
numpy==1.26.2
geopandas==0.14.1
shapely==2.0.2
scikit-learn==1.3.2
ortools==9.7.2996
openpyxl==3.1.2
python-multipart==0.0.6
requests==2.31.0
```

### 5.4 Create Environment Configuration
```bash
vim /opt/zone-generator/.env
```

**.env**:
```bash
# Database
DATABASE_URL=postgresql://zoneapp:CHANGE_THIS_PASSWORD@localhost:5432/zone_generator

# OSRM
OSRM_HOST=http://localhost:5000

# Application
APP_NAME=Intelligent Zone Generator
DEBUG=false
LOG_LEVEL=INFO

# CORS (frontend domain)
CORS_ORIGINS=http://your-domain.com,https://your-domain.com

# File Upload
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=/opt/zone-generator/uploads

# Session
SECRET_KEY=GENERATE_RANDOM_SECRET_KEY_HERE
```

### 5.5 Initialize Database Schema
```bash
source venv/bin/activate
python -m app.init_db
```

**init_db.py**:
```python
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            customercode VARCHAR(50) PRIMARY KEY,
            cus_latitude DOUBLE PRECISION NOT NULL,
            cus_longitude DOUBLE PRECISION NOT NULL,
            geom GEOMETRY(Point, 4326),
            isactive INTEGER DEFAULT 1,
            area VARCHAR(100),
            zone VARCHAR(50),
            route_id VARCHAR(50),
            route_day VARCHAR(10),
            visit_sequence INTEGER,
            dc VARCHAR(100),
            salesagentcode VARCHAR(50),
            cusname VARCHAR(255),
            totalamount DECIMAL(15,2),
            totaldeliveredorders INTEGER,
            averageorderamount DECIMAL(15,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_customers_coords 
          ON customers (cus_latitude, cus_longitude);
        CREATE INDEX IF NOT EXISTS idx_customers_zone ON customers (zone);
        CREATE INDEX IF NOT EXISTS idx_customers_geom ON customers USING GIST (geom);
        
        CREATE TABLE IF NOT EXISTS zones (
            zone_id VARCHAR(50) PRIMARY KEY,
            area VARCHAR(100),
            dc VARCHAR(100),
            zone_type VARCHAR(50),
            geom GEOMETRY(Polygon, 4326),
            customer_count INTEGER,
            total_revenue DECIMAL(15,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            agent_assigned VARCHAR(50)
        );
        
        CREATE INDEX IF NOT EXISTS idx_zones_geom ON zones USING GIST (geom);
        
        CREATE TABLE IF NOT EXISTS routes (
            route_id VARCHAR(50) PRIMARY KEY,
            zone_id VARCHAR(50) REFERENCES zones(zone_id),
            route_day VARCHAR(10),
            customer_count INTEGER,
            total_distance_km DOUBLE PRECISION,
            total_time_min DOUBLE PRECISION,
            route_sequence JSONB,
            constraint_violations JSONB,
            feasibility_status VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS config (
            config_key VARCHAR(100) PRIMARY KEY,
            config_value JSONB,
            area_override VARCHAR(100),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    conn.commit()
    
print("✅ Database initialized successfully")
```

---

## 6. Systemd Service Configuration

### 6.1 Create FastAPI Service
```bash
sudo vim /etc/systemd/system/zone-generator-api.service
```

**zone-generator-api.service**:
```ini
[Unit]
Description=Zone Generator API Service
After=network.target postgresql.service

[Service]
Type=notify
User=zoneapp
Group=zoneapp
WorkingDirectory=/opt/zone-generator
Environment="PATH=/opt/zone-generator/venv/bin"
ExecStart=/opt/zone-generator/venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6.2 Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable zone-generator-api
sudo systemctl start zone-generator-api

# Check status
sudo systemctl status zone-generator-api

# View logs
sudo journalctl -u zone-generator-api -f
```

---

## 7. Nginx Installation & Configuration

### 7.1 Install Nginx
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 7.2 Configure Nginx
```bash
sudo vim /etc/nginx/sites-available/zone-generator
```

**zone-generator nginx config**:
```nginx
# API upstream
upstream api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;  # Change this
    
    client_max_body_size 50M;
    
    # Frontend (static files)
    location / {
        root /var/www/zone-generator;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long operations
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    
    # Static assets
    location /assets/ {
        root /var/www/zone-generator;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 7.3 Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/zone-generator /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### 7.4 Deploy Frontend Files
```bash
sudo mkdir -p /var/www/zone-generator
sudo chown -R www-data:www-data /var/www/zone-generator

# Copy frontend files
sudo cp -r /opt/zone-generator/frontend/* /var/www/zone-generator/
```

---

## 8. SSL Certificate (Optional but Recommended)

### 8.1 Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 8.2 Obtain Certificate
```bash
sudo certbot --nginx -d your-domain.com
```

### 8.3 Auto-renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot installs auto-renewal cron job automatically
```

---

## 9. Firewall Configuration

### 9.1 Install UFW
```bash
sudo apt install -y ufw
```

### 9.2 Configure Firewall Rules
```bash
# Allow SSH (important: do this first!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

---

## 10. Backup Configuration

### 10.1 Create Backup Script
```bash
sudo vim /opt/scripts/backup-db.sh
```

**backup-db.sh**:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="zone_generator"

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U zoneapp -h localhost $DB_NAME | gzip > \
  $BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${DB_NAME}_${TIMESTAMP}.sql.gz"
```

### 10.2 Schedule Backups
```bash
sudo chmod +x /opt/scripts/backup-db.sh

# Add to crontab
sudo crontab -e

# Add line (daily backup at 2 AM):
0 2 * * * /opt/scripts/backup-db.sh >> /var/log/db-backup.log 2>&1
```

---

## 11. Monitoring & Logging

### 11.1 Application Logs
```bash
# API logs
sudo journalctl -u zone-generator-api -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### 11.2 System Monitoring
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Check resource usage
htop

# Check disk usage
df -h

# Check memory
free -h
```

### 11.3 Log Rotation
```bash
# Configure logrotate for application logs
sudo vim /etc/logrotate.d/zone-generator
```

**/etc/logrotate.d/zone-generator**:
```
/var/log/zone-generator/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 zoneapp zoneapp
    sharedscripts
    postrotate
        systemctl reload zone-generator-api > /dev/null 2>&1 || true
    endscript
}
```

---

## 12. Health Checks

### 12.1 API Health Endpoint
```python
# In app/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": check_db_connection(),
            "osrm": check_osrm_connection()
        }
    }
```

### 12.2 Monitor Script
```bash
vim /opt/scripts/health-check.sh
```

**health-check.sh**:
```bash
#!/bin/bash

# Check API
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$API_STATUS" != "200" ]; then
    echo "API DOWN" | mail -s "Alert: Zone Generator API Down" admin@example.com
fi

# Check OSRM
OSRM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
if [ "$OSRM_STATUS" != "200" ]; then
    echo "OSRM DOWN" | mail -s "Alert: OSRM Service Down" admin@example.com
fi

# Check PostgreSQL
pg_isready -h localhost -U zoneapp > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "PostgreSQL DOWN" | mail -s "Alert: PostgreSQL Down" admin@example.com
fi
```

---

## 13. Deployment Checklist

- [ ] VM provisioned with correct specifications
- [ ] Ubuntu 22.04 installed and updated
- [ ] Static IP configured
- [ ] Firewall rules applied
- [ ] PostgreSQL installed and configured
- [ ] PostGIS extension enabled
- [ ] Database created with correct schema
- [ ] Docker installed
- [ ] OSRM data downloaded and processed
- [ ] OSRM service running (test with curl)
- [ ] Application code deployed
- [ ] Python virtual environment created
- [ ] All dependencies installed
- [ ] .env file configured with correct values
- [ ] Database initialized (tables created)
- [ ] Systemd service created and started
- [ ] Nginx installed and configured
- [ ] Frontend files deployed
- [ ] SSL certificate obtained (if needed)
- [ ] Backup script configured
- [ ] Monitoring set up
- [ ] Health checks working
- [ ] Test complete workflow (upload → zone → route → export)

---

## 14. Post-Deployment Testing

### 14.1 Test Database Connection
```bash
psql -U zoneapp -d zone_generator -h localhost -c "SELECT postgis_version();"
```

### 14.2 Test OSRM
```bash
curl "http://localhost:5000/table/v1/driving/46.6753,24.7136;46.7,24.72"
```

### 14.3 Test API
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/config
```

### 14.4 Test Frontend
```bash
curl http://localhost/
# Should return HTML content
```

### 14.5 End-to-End Test
1. Open browser to http://your-domain.com
2. Upload sample customer data
3. Create polar zones
4. Optimize routes
5. Export results
6. Verify all outputs

---

## 15. Troubleshooting

### API Won't Start
```bash
# Check logs
sudo journalctl -u zone-generator-api -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8000

# Check Python errors
source /opt/zone-generator/venv/bin/activate
cd /opt/zone-generator
python -m app.main
```

### OSRM Not Responding
```bash
# Check Docker container
docker ps
docker logs osrm-backend

# Restart OSRM
cd /opt/osrm
docker-compose restart

# Check logs
docker-compose logs -f
```

### Database Connection Errors
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Test connection
psql -U zoneapp -d zone_generator -h localhost
```

### High Memory Usage
```bash
# Check memory
free -h

# Check processes
ps aux --sort=-%mem | head -10

# Reduce OSRM memory (edit docker-compose.yml)
mem_limit: 4g

# Reduce API workers (edit systemd service)
--workers 2
```

---

## 16. Maintenance Procedures

### Update Application Code
```bash
cd /opt/zone-generator
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart zone-generator-api
```

### Update OSRM Data
```bash
cd /opt/osrm/data
wget https://download.geofabrik.de/asia/saudi-arabia-latest.osm.pbf -O saudi-arabia-latest.osm.pbf
# Re-process data (see step 4.3)
cd /opt/osrm
docker-compose restart
```

### Vacuum Database
```bash
psql -U zoneapp -d zone_generator -h localhost -c "VACUUM ANALYZE;"
```

---

## 17. Security Hardening

### Disable Root SSH
```bash
sudo vim /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd
```

### Automatic Security Updates
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Fail2Ban (SSH Protection)
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 18. Production Optimization

### PostgreSQL Tuning
```bash
sudo vim /etc/postgresql/15/main/postgresql.conf

# Adjust based on RAM (example for 16GB):
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 64MB
max_connections = 100

sudo systemctl restart postgresql
```

### Nginx Optimization
```bash
sudo vim /etc/nginx/nginx.conf

# Add to http block:
gzip on;
gzip_types text/css application/javascript application/json;
keepalive_timeout 65;
client_max_body_size 50M;

sudo systemctl restart nginx
```

---

## Complete Deployment Commands (Summary)

```bash
# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql-15 postgresql-15-postgis-3 python3.11 python3.11-venv nginx docker.io docker-compose

# 2. Database
sudo -u postgres psql -c "CREATE DATABASE zone_generator;"
sudo -u postgres psql -c "CREATE USER zoneapp WITH PASSWORD 'CHANGE_THIS';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE zone_generator TO zoneapp;"
sudo -u postgres psql -d zone_generator -c "CREATE EXTENSION postgis;"

# 3. OSRM
cd /opt/osrm/data
wget https://download.geofabrik.de/asia/saudi-arabia-latest.osm.pbf
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/saudi-arabia-latest.osm.pbf
docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend osrm-contract /data/saudi-arabia-latest.osrm
cd /opt/osrm && docker-compose up -d

# 4. Application
cd /opt/zone-generator
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.init_db

# 5. Services
sudo cp zone-generator-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zone-generator-api

# 6. Nginx
sudo cp zone-generator.nginx /etc/nginx/sites-available/zone-generator
sudo ln -s /etc/nginx/sites-available/zone-generator /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# 7. Verify
curl http://localhost:8000/health
```

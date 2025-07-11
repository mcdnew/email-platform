# Email Platform Deployment Guide

This guide walks you through two deployment methods for your Email Platform + Streamlit frontend:

- **A. Bare-metal** on an Ubuntu Lightsail instance (no Docker)  
- **B. Docker-Compose** on an Ubuntu Lightsail instance  

Each section is broken into clear, copy-&-paste steps so even beginners can follow.

---

## A. Bare-Metal Deployment on Ubuntu Lightsail

### 1. Launch & Configure an Ubuntu Lightsail Instance

1. In the AWS Lightsail console, click **Create instance**.  
2. Choose **Linux/Unix → Ubuntu 22.04 LTS**.  
3. Pick an instance plan (e.g. $5/mo).  
4. Under **SSH key**, use the default or upload your own.  
5. Name it (e.g. `email-platform`) and click **Create**.  

Once it's up, note its **public IP**. Under **Networking**, add firewall rules to open:

- TCP **22** (SSH)  
- TCP **8000** (Backend API)  
- TCP **8501** (Streamlit frontend)

### 2. SSH into the Server

```bash
ssh ubuntu@YOUR_LIGHTSAIL_IP
```

*Replace YOUR_LIGHTSAIL_IP with the public IP.*

### 3. System Update & Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-pip python3-venv postgresql postgresql-contrib build-essential libpq-dev
```

### 4. Configure PostgreSQL

Switch to the postgres superuser:

```bash
sudo -u postgres psql
```

In the psql prompt, run:

```sql
CREATE ROLE email_user WITH LOGIN PASSWORD 'strongpassword';
CREATE DATABASE email_platform OWNER email_user;
\q
```

**Tip:** You can choose any username/password—just keep them consistent in your .env.

### 5. Clone & Configure the Backend

```bash
cd ~
git clone https://github.com/yourusername/email-platform.git
cd email-platform
cp .env.example .env
```

Edit .env (`nano .env`) and set:

```ini
DATABASE_URL=postgresql://email_user:strongpassword@localhost:5432/email_platform
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_BCC=
MAX_EMAILS_PER_DAY=100
SCHEDULER_SECRET=
```

### 6. Install & Migrate the Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run Alembic migrations
alembic upgrade head
```

If you get errors about alembic not found, install it in the venv:
```bash
pip install alembic
```

### 7. Run the Backend (Development)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Test in your browser:
`http://YOUR_LIGHTSAIL_IP:8000/docs` should load the OpenAPI UI.

#### Optional—systemd service

To run on startup, create `/etc/systemd/system/email-backend.service`:

```ini
[Unit]
Description=Email Platform API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/email-platform
ExecStart=/home/ubuntu/email-platform/venv/bin/uvicorn app.main:app \
          --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable email-backend
sudo systemctl start email-backend
```

### 8. Clone & Configure the Frontend

In a separate folder (or the same):

```bash
cd ~
git clone https://github.com/yourusername/email-platform.git frontend
cd frontend
cp frontend/.env.example frontend/.env
```

Edit `frontend/.env` and set:

```ini
API_URL=http://YOUR_LIGHTSAIL_IP:8000
```

### 9. Install & Run the Frontend

```bash
cd ~/frontend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # should include streamlit and st-aggrid etc.

streamlit run frontend/main.py --server.port 8501 --server.address 0.0.0.0
```

Visit `http://YOUR_LIGHTSAIL_IP:8501` in your browser.

#### Optional—systemd service

Create `/etc/systemd/system/email-frontend.service`:

```ini
[Unit]
Description=Email Platform Frontend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/frontend
ExecStart=/home/ubuntu/frontend/venv/bin/streamlit run frontend/main.py \
          --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable email-frontend
sudo systemctl start email-frontend
```

---

## B. Docker-Compose Deployment on Ubuntu Lightsail

### 1. Launch & Configure the Lightsail Instance

Follow **A.1** and **A.2** above (open ports 22, 8000, 8501).

### 2. Install Docker & Docker-Compose

```bash
ssh ubuntu@YOUR_LIGHTSAIL_IP

# Install Docker
sudo apt update
sudo apt install -y \
    ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) \
    signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Allow ubuntu user to run docker
sudo usermod -aG docker ubuntu
newgrp docker

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Clone & Configure the Repository

```bash
cd ~
git clone https://github.com/yourusername/email-platform.git
cd email-platform
```

Copy env files:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit `.env`:

```ini
# .env
DATABASE_URL=postgresql://email_user:strongpassword@db:5432/email_platform
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_BCC=
MAX_EMAILS_PER_DAY=100
SCHEDULER_SECRET=
```

Edit `frontend/.env`:

```ini
API_URL=http://backend:8000
```

### 4. Launch with Docker-Compose

```bash
docker-compose up -d
```

This starts three services:

- **db** (Postgres)
- **backend** (FastAPI + Uvicorn)
- **frontend** (Streamlit)

Check status:

```bash
docker-compose ps
```

Logs:

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. Verify & Access

- **Backend OpenAPI:** `http://YOUR_LIGHTSAIL_IP:8000/docs`
- **Frontend:** `http://YOUR_LIGHTSAIL_IP:8501`

### 6. Auto-Start on Reboot

Create `/etc/systemd/system/docker-compose-app.service`:

```ini
[Unit]
Description=Docker Compose: Email Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/home/ubuntu/email-platform
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable docker-compose-app
sudo systemctl start docker-compose-app
```

---

## Final Tips

- **DNS:** Point your domain (e.g. app.example.com) via an A-record to your Lightsail IP.
- **SSL:** Once your domain is live, install Certbot and configure Nginx as reverse-proxy with Let's Encrypt certificates.
- **Monitoring:** Use `journalctl -u email-backend -f` (or Docker logs) to debug.
- **Backups:** Regularly dump your Postgres data with `pg_dump`.

Deploy your app on AWS Lightsail—either directly ("bare-metal") or via Docker. Good luck!

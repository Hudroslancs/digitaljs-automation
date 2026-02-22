# Jobsheet System — Phase 1: Docker + AWS EC2 + Cloudflare Tunnel

## Architecture Overview

```
Internet → Cloudflare Tunnel → cloudflared container → Flask app container
                                                      → Prometheus + Grafana (localhost only)
```

No ports are exposed to the internet. Cloudflare Tunnel punches outward — zero open inbound ports on EC2.

---

## File Structure

```
jobsheet-system/
├── app.py                          # Flask app
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example                    # copy to .env, fill in secrets
├── .gitignore                      # .env is ignored
├── monitoring/
│   └── prometheus.yml
├── templates/
│   └── create_jobsheet.html
├── static/
│   ├── style.css
│   ├── script.js
│   └── jobsheet_bg.png
└── .github/
    └── workflows/
        └── deploy.yml              # GitHub Actions CI/CD
```

---

## Phase 1 Deployment — Step by Step

### Step 1: AWS EC2 Setup (Free Tier)

1. Go to AWS Console → EC2 → Launch Instance
2. Choose **Amazon Linux 2023** (free tier eligible)
3. Instance type: **t2.micro** (free tier — 750 hrs/month)
4. Key pair: create a new one, download the `.pem` file
5. Security Group — **only allow these inbound rules:**
   - SSH (port 22) from your IP only (not 0.0.0.0/0)
   - No HTTP/HTTPS rules needed — Cloudflare Tunnel handles it
6. Storage: 8 GB gp2 (free tier gives 30 GB, but keep it lean)

**Set up billing alert immediately:**
- AWS Console → Billing → Budgets → Create Budget
- Set threshold at $1 with email alert

### Step 2: Install Docker on EC2

```bash
# SSH into your instance
ssh -i your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP

# Install Docker
sudo yum update -y
sudo yum install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Log out and back in for docker group to take effect
exit
ssh -i your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

### Step 3: Cloudflare Tunnel Setup

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → Zero Trust → Networks → Tunnels
2. Create a tunnel, name it `jobsheet-tunnel`
3. Choose **Docker** as the connector
4. Copy the tunnel token (looks like `eyJ...`)
5. Under **Public Hostname**, add:
   - Subdomain: `jobsheet` (or whatever you want)
   - Domain: your domain
   - Service: `http://app:5000`
6. Save — your app will be at `https://jobsheet.yourdomain.com`

### Step 4: Deploy the App

```bash
# On EC2
git clone https://github.com/YOUR_USERNAME/jobsheet-system.git
cd jobsheet-system

# Create .env from template
cp .env.example .env
nano .env
# Fill in: SECRET_KEY, CLOUDFLARE_TUNNEL_TOKEN, GRAFANA_PASSWORD

# Start everything
docker compose up -d

# Check logs
docker compose logs -f
```

### Step 5: Verify It's Working

```bash
# Check all containers are running
docker compose ps

# Test health endpoint
curl http://localhost:5000/health
# Should return: {"status": "ok"}

# Check Cloudflare Tunnel status
docker compose logs cloudflared
```

Visit `https://jobsheet.yourdomain.com` — it should load over HTTPS with no Tailscale needed.

---

## GitHub Actions CI/CD Setup

Add these secrets to your GitHub repo (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `EC2_HOST` | Your EC2 public IP |
| `EC2_SSH_KEY` | Contents of your `.pem` file |

Now every `git push` to `main` will automatically build and deploy to EC2.

---

## Monitoring

- **Prometheus**: `http://localhost:9090` (SSH tunnel to access: `ssh -L 9090:localhost:9090 ec2-user@YOUR_EC2_IP`)
- **Grafana**: `http://localhost:3000` (SSH tunnel: `ssh -L 3000:localhost:3000 ec2-user@YOUR_EC2_IP`)
  - Default login: admin / (your GRAFANA_PASSWORD from .env)
  - Add Prometheus as data source: URL = `http://prometheus:9090`

---

## AWS Security Checklist (Cloud Security Portfolio)

- [ ] EC2 Security Group: SSH only from your IP, no HTTP/HTTPS inbound
- [ ] IAM: Create a dedicated IAM user for this project, no root access
- [ ] CloudTrail: Enable in AWS Console → CloudTrail → Create trail (free tier: 1 trail)
- [ ] CloudWatch: Set up billing alarm at $1
- [ ] S3: If you add S3 later, block all public access by default
- [ ] Secrets: All secrets in `.env` (gitignored), never hardcoded

---

## Phase 2 Preview — Claims Feature

When you're ready for Phase 2, these endpoints will be added:
- `POST /claims/submit` — technician submits claim with job details
- `GET /claims/pending` — boss views pending claims
- `POST /claims/approve/<id>` — boss approves/rejects
- Google Maps API integration for auto KM calculation from HQ

---

## Migration Plan (After 12 Months Free Tier)

Since everything runs in Docker, migration to the office server is:

```bash
# On office server
git clone https://github.com/YOUR_USERNAME/jobsheet-system.git
cd jobsheet-system
cp .env.example .env  # fill in same values
docker compose up -d  # identical stack, zero changes needed
```

Update Cloudflare Tunnel to point to the new server IP. Done.

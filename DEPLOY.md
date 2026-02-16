# Deployment Guide

This guide covers how to host your CardTrader Dashboard so it can be accessed from outside your local network.

## 1. Keep the Server Running

You need the server to run in the background, even if you close your terminal.

### Option A: Systemd (Recommended for Linux/VPS)
1. Edit the service file `cardtrader.service` below (replace `/path/to/project` and `your_user`):
   ```ini
   [Unit]
   Description=CardTrader Dashboard
   After=network.target

   [Service]
   User=your_user
   WorkingDirectory=/path/to/project
   ExecStart=/path/to/project/start_server.sh
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. Copy to systemd: `sudo cp cardtrader.service /etc/systemd/system/`
3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable cardtrader
   sudo systemctl start cardtrader
   ```

### Option B: Screen/Tmux (Quick & Dirty)
1. Start a session: `screen -S cardtrader`
2. Run the script: `./start_server.sh`
3. Detach: Press `Ctrl+A`, then `D`.
4. To resume later: `screen -r cardtrader`

---

## 2. Expose to the Internet

### Option A: Cloudflare Tunnel (Easiest & Safest)
Ideal for home servers. No port forwarding required.

1. Install `cloudflared`.
2. Login: `cloudflared tunnel login`
3. Create a tunnel: `cloudflared tunnel create cardtrader`
4. Route traffic: `cloudflared tunnel route dns cardtrader cardtrader.yourdomain.com`
5. Run the tunnel:
   ```bash
   cloudflared tunnel run --url http://localhost:8000 cardtrader
   ```

### Option B: Nginx Reverse Proxy (Standard for VPS)
1. Install Nginx: `sudo apt install nginx`
2. Create config: `sudo nano /etc/nginx/sites-available/cardtrader`
   ```nginx
   server {
       listen 80;
       server_name your-server-ip-or-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
3. Enable it: `sudo ln -s /etc/nginx/sites-available/cardtrader /etc/nginx/sites-enabled/`
4. Restart Nginx: `sudo systemctl restart nginx`

### Option C: Direct Port Access (Not Recommended)
Open port 8000 on your firewall (UFW/AWS Security Group).
- **URL:** `http://your-server-ip:8000`
- **Warning:** This exposes the raw python server directly to the web.

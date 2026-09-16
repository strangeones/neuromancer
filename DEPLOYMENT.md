# Tessier-Ashpool Deployment Guide

This document outlines how to deploy the Neuromancer/Wintermute core onto a headless Proxmox VM.

## 1. Prepare the Proxmox VM
1. Provision a lightweight Linux VM on your Proxmox server (Debian 12 or Alpine Linux recommended).
2. Ensure you allocate at least 2GB of RAM (required for `chromadb` embeddings to load smoothly).
3. SSH into your newly created VM as a standard user.

## 2. Clone and Initialize
Clone the repository (after you push it to GitHub):
```bash
git clone https://github.com/YOUR_USERNAME/neuromancer.git
cd neuromancer
```

Run the bootstrap script. It will automatically detect Debian/Alpine and use `apt` or `apk` to install required dependencies (Python 3, Git, OpenSSH, etc):
```bash
./jack-in.sh
```

## 3. Configuration
Since your VM is headless, you cannot use the `./jack --setup` `pywebview` wizard. You must manually copy or create your `.env` file from your local machine to the server:
```bash
nano .env
```
Ensure it contains:
```env
LITELLM_MODEL_NAME=vertex_ai/gemini-3.1-pro
VERTEX_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/adc.json
WINTERMUTE_AUTH_KEY=Wintermute2009
```
*(Note: If using ADC, you will need to scp your `application_default_credentials.json` to the VM, or run `gcloud auth application-default login` on the VM directly.)*

## 4. Run the API Gateway Daemon
To keep the brain running 24/7 in the background, you can use `screen`, `tmux`, or a `systemd` service to run the FastAPI Gateway:
```bash
./jack --gateway
```
This will start the backend on `http://0.0.0.0:8000`. 

## 5. Connect via Cyberspace Viewer
From your local Mac, run `./jack --viewer`. 
(You may need to modify the Viewer's hardcoded `http://localhost:8000` string in `src/viewer.py` to point to the IP address of your Proxmox VM).

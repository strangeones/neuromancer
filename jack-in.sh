#!/bin/bash
# ==============================================================================
# TESSIER-ASHPOOL AUTOMATED DEPLOYMENT SEQUENCE
# CODENAME: JACK-IN
# ==============================================================================

set -e # Exit on any error

# 1. Boot Sequence Initialization
echo -e "\n[+] INITIALIZING BRAIN HOST BOOTSTRAP SEQUENCE..."
sleep 1
echo -e "[+] ESTABLISHING SECURE HANDSHAKE..."

# Determine OS
if [ "$(uname -s)" = "Darwin" ]; then
    OS="macos"
elif [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "[-] FATAL: OS NOT DETECTED. ABORTING."
    exit 1
fi

echo -e "[+] HOST OS DETECTED: $OS"

# 2. System Dependencies
echo -e "\n[+] DEPLOYING SYSTEM PACKAGES (ICE COMPLIANT)..."
if [ "$OS" = "macos" ]; then
    echo -e "[+] macOS DETECTED: SKIPPING SYSTEM PACKAGE DEPLOYMENT FOR LOCAL DEV..."
elif [ "$OS" = "debian" ] || [ "$OS" = "ubuntu" ]; then
    sudo apt-get update -y -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv git openssh-client curl build-essential nmap
elif [ "$OS" = "alpine" ]; then
    sudo apk update
    sudo apk add python3 py3-pip git openssh curl build-base nmap
else
    echo "[-] WARNING: UNRECOGNIZED OS. ATTEMPTING TO PROCEED..."
fi

# 3. Python Environment Setup
echo -e "\n[+] CONSTRUCTING LOCAL PYTHON SANDBOX..."
python3 -m venv .venv
source .venv/bin/activate

echo -e "[+] INSTALLING NEURAL PATHWAYS (PIP DEPENDENCIES)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 4. Directory Structure & Memory Initialization
echo -e "\n[+] FORMATTING VECTOR MEMORY BANKS..."
mkdir -p data/memory
mkdir -p src/constructs

# 5. Environment Variables
if [ ! -f .env ]; then
    echo -e "[+] GENERATING DEFAULT ENVIRONMENT CONFIG..."
    echo "WINTERMUTE_MODEL=gemini/gemini-1.5-flash" > .env
    echo "NEUROMANCER_DB_PATH=./data/memory" >> .env
    echo "API_KEYS_LOADED=false" >> .env
fi

# 6. Handshake Complete
echo -e "\n=============================================================================="
echo -e "                 TESSIER-ASHPOOL CORE ONLINE"
echo -e "=============================================================================="
echo -e "Wintermute execution loop...... READY"
echo -e "Neuromancer vector core........ READY"
echo -e "Black ICE security middleware.. ARMED"
echo -e "\nType 'source .venv/bin/activate' then 'python src/main.py' to enter The Deck."

import webview
import requests
import json
import os

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            background-color: #050505;
            color: #00ffcc;
            font-family: 'Courier New', Courier, monospace;
            padding: 20px;
            text-align: center;
            overflow: hidden;
            margin: 0;
        }
        h1 {
            color: #ff0055;
            text-transform: uppercase;
            letter-spacing: 3px;
            text-shadow: 0 0 10px #ff0055, 0 0 20px #ff0055;
            margin-top: 30px;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 25px;
            text-align: left;
            width: 85%;
            margin-left: auto;
            margin-right: auto;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #00ffcc;
            text-shadow: 0 0 5px #00ffcc;
            font-size: 14px;
        }
        input {
            width: 100%;
            padding: 12px;
            background-color: #111;
            border: 1px solid #00ffcc;
            color: #fff;
            font-family: inherit;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }
        input:focus {
            outline: none;
            border-color: #ff0055;
            box-shadow: 0 0 10px #ff0055;
        }
        button {
            background-color: transparent;
            color: #ff0055;
            border: 2px solid #ff0055;
            padding: 12px 40px;
            font-size: 18px;
            font-weight: bold;
            text-transform: uppercase;
            cursor: pointer;
            border-radius: 4px;
            box-shadow: 0 0 10px rgba(255,0,85,0.5);
            margin-top: 20px;
            transition: all 0.3s ease;
        }
        button:hover {
            background-color: #ff0055;
            color: #fff;
            box-shadow: 0 0 20px #ff0055;
        }
        .scanline {
            width: 100%;
            height: 100%;
            z-index: 9999;
            position: absolute;
            pointer-events: none;
            background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,0) 50%, rgba(0,0,0,0.1) 50%, rgba(0,0,0,0.1));
            background-size: 100% 4px;
            top: 0;
            left: 0;
        }
        #dashboard {
            display: none;
            text-align: left;
            width: 85%;
            margin: 0 auto;
            border: 1px solid #ff0055;
            padding: 20px;
            box-shadow: 0 0 15px rgba(255,0,85,0.3);
            background-color: rgba(20, 0, 10, 0.5);
        }
        .telemetry-item {
            margin-bottom: 15px;
            font-size: 16px;
        }
        .val {
            color: #ff0055;
            font-weight: bold;
            text-shadow: 0 0 5px #ff0055;
        }
        .err {
            color: #ff0055;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="scanline"></div>
    <h1>Cyberspace Viewer</h1>
    
    <div id="login-section">
        <div class="form-group">
            <label for="auth_key">WINTERMUTE_AUTH_KEY</label>
            <input type="password" id="auth_key" placeholder="Enter master password">
        </div>
        <button onclick="connect()">Connect</button>
        <div id="error-msg" class="err"></div>
    </div>

    <div id="dashboard">
        <div class="telemetry-item">STATUS: <span id="status-val" class="val">OFFLINE</span></div>
        <div class="telemetry-item">ACTIVE CONSTRUCTS: <span id="constructs-val" class="val">0</span></div>
        <div class="telemetry-item">MEMORY CAPACITY: <span id="memory-val" class="val">0</span></div>
        <div class="telemetry-item">UPTIME (s): <span id="uptime-val" class="val">0</span></div>
    </div>

    <script>
        let pollInterval;

        function connect() {
            const password = document.getElementById('auth_key').value;
            const errorMsg = document.getElementById('error-msg');
            errorMsg.innerText = "Connecting...";

            pywebview.api.authenticate(password).then(function(response) {
                if (response.success) {
                    document.getElementById('login-section').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'block';
                    
                    // Start polling
                    pollTelemetry();
                    pollInterval = setInterval(pollTelemetry, 5000);
                } else {
                    errorMsg.innerText = response.error || "Authentication failed.";
                }
            }).catch(function(err) {
                errorMsg.innerText = "Error calling Python API.";
            });
        }

        function pollTelemetry() {
            pywebview.api.get_telemetry().then(function(data) {
                if (data.success) {
                    document.getElementById('status-val').innerText = data.data.status || "UNKNOWN";
                    document.getElementById('constructs-val').innerText = data.data.active_constructs !== undefined ? data.data.active_constructs : "0";
                    document.getElementById('memory-val').innerText = data.data.memory_capacity !== undefined ? data.data.memory_capacity : "0";
                    
                    if (data.data.uptime_seconds !== undefined) {
                        document.getElementById('uptime-val').innerText = Math.round(data.data.uptime_seconds);
                    }
                } else {
                    // Ignore transient errors or show them
                    console.error("Telemetry error: ", data.error);
                }
            });
        }
    </script>
</body>
</html>
"""

class ViewerApi:
    def __init__(self):
        self.token = None
        self.base_url = "http://localhost:8000"

    def authenticate(self, password):
        try:
            response = requests.post(
                f"{self.base_url}/token",
                data={"username": "admin", "password": password},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                return {"success": True}
            else:
                return {"success": False, "error": "Invalid credentials"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def get_telemetry(self):
        if not self.token:
            return {"success": False, "error": "Not authenticated"}
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/telemetry",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

if __name__ == '__main__':
    api = ViewerApi()
    window = webview.create_window(
        'Cyberspace Viewer', 
        html=HTML_CONTENT, 
        js_api=api, 
        width=800, 
        height=600, 
        resizable=True
    )
    webview.start()

import webview
import os

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            background-color: #0a0a0f;
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
        input, select {
            width: 100%;
            padding: 12px;
            background-color: #11111a;
            border: 1px solid #00ffcc;
            color: #fff;
            font-family: inherit;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }
        input:focus, select:focus {
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
    </style>
</head>
<body>
    <div class="scanline"></div>
    <h1>Neuromancer Setup</h1>
    <div class="form-group">
        <label for="model">LITELLM_MODEL_NAME</label>
        <select id="model">
            <option value="gemini/gemini-1.5-pro-latest">Gemini Pro (Latest)</option>
            <option value="gemini/gemini-1.5-flash-latest">Gemini Flash (Latest)</option>
            <option value="gpt-4o">GPT-4 Omni</option>
            <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet</option>
        </select>
    </div>
    <div class="form-group">
        <label for="api_key">LLM_API_KEY</label>
        <input type="password" id="api_key" placeholder="••••••••••••••••">
    </div>
    <div class="form-group">
        <label for="auth_key">WINTERMUTE_AUTH_KEY</label>
        <input type="password" id="auth_key" placeholder="••••••••••••••••">
    </div>
    <button onclick="saveConfig()">Jack In</button>

    <script>
        function saveConfig() {
            var model = document.getElementById('model').value;
            var apiKey = document.getElementById('api_key').value;
            var authKey = document.getElementById('auth_key').value;
            
            pywebview.api.save_env(model, apiKey, authKey).then(function() {
                pywebview.api.close_window();
            });
        }
    </script>
</body>
</html>
"""

class SetupApi:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def save_env(self, model, api_key, auth_key):
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        env_data = {}
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        env_data[k] = v
        
        if model:
            env_data['LITELLM_MODEL_NAME'] = model
        if api_key:
            env_data['LLM_API_KEY'] = api_key
        if auth_key:
            env_data['WINTERMUTE_AUTH_KEY'] = auth_key
            
        with open(env_path, 'w') as f:
            for k, v in env_data.items():
                f.write(f"{k}={v}\n")
        return True

    def close_window(self):
        # On macOS, calling window.destroy() from a JS bridge thread can cause a Cocoa freeze.
        # Since this is a one-off config wizard, we can just forcefully exit.
        os._exit(0)

if __name__ == '__main__':
    api = SetupApi()
    window = webview.create_window('Neuromancer Setup', html=HTML_CONTENT, js_api=api, width=500, height=600, resizable=False)
    api.set_window(window)
    webview.start()

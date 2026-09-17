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
            <option value="gemini/gemini-flash-latest">Gemini Flash (Free Tier Default)</option>
            <option value="vertex_ai/gemini-3.1-pro">Gemini 3.1 Pro (Vertex AI OAuth)</option>
            <option value="gemini/gemini-3.1-pro-preview">Gemini 3.1 Pro (AI Studio API Key)</option>
            <option value="gemini/gemini-3.5-flash-lite">Gemini 3.5 Flash Lite (Free)</option>
            <option value="gemini/antigravity-preview-09-2026">Antigravity 2.0 (Internal)</option>
        </select>
    </div>
    <div class="form-group">
        <label for="vertex_project">VERTEX_PROJECT (For OAuth/Vertex Models)</label>
        <input type="text" id="vertex_project" placeholder="your-gcp-project-id">
    </div>
    <div class="form-group">
        <label for="api_key">LLM_API_KEY (Or use OAuth below)</label>
        <input type="password" id="api_key" placeholder="••••••••••••••••">
    </div>
    <div class="form-group">
        <label for="auth_key">WINTERMUTE_AUTH_KEY</label>
        <input type="password" id="auth_key" placeholder="••••••••••••••••">
    </div>
    <button onclick="saveConfig()">Jack In</button>
    <br><br>
    <button onclick="oauthLogin()" style="border-color: #4285F4; color: #4285F4; box-shadow: 0 0 10px rgba(66, 133, 244, 0.5);">Login with Google (OAuth)</button>

    <script>
        function saveConfig() {
            var model = document.getElementById('model').value;
            var apiKey = document.getElementById('api_key').value;
            var authKey = document.getElementById('auth_key').value;
            var vertexProject = document.getElementById('vertex_project').value;
            
            pywebview.api.save_env(model, apiKey, authKey, vertexProject).then(function() {
                pywebview.api.close_window();
            });
        }
        
        function oauthLogin() {
            pywebview.api.google_oauth().then(function(result) {
                if(result) {
                    alert("OAuth Successful! Credentials saved for Vertex AI.");
                } else {
                    alert("OAuth Failed.");
                }
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

    def save_env(self, model, api_key, auth_key, vertex_project=None):
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
        if vertex_project:
            env_data['VERTEX_PROJECT'] = vertex_project
            env_data['VERTEX_LOCATION'] = 'us-central1'
            
        with open(env_path, 'w') as f:
            for k, v in env_data.items():
                f.write(f"{k}={v}\n")
        return True

    def google_oauth(self):
        try:
            import google_login
            adc_path = google_login.do_login()
            if adc_path:
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
                with open(env_path, 'a') as f:
                    f.write(f"\nGOOGLE_APPLICATION_CREDENTIALS={adc_path}\n")
                return True
            return False
        except Exception as e:
            print(f"OAuth Error: {e}")
            return False

    def close_window(self):
        # On macOS, calling window.destroy() from a JS bridge thread can cause a Cocoa freeze.
        # Since this is a one-off config wizard, we can just forcefully exit.
        os._exit(0)

if __name__ == '__main__':
    api = SetupApi()
    window = webview.create_window('Neuromancer Setup', html=HTML_CONTENT, js_api=api, width=500, height=750, resizable=True)
    api.set_window(window)
    try:
        import sys
        if sys.platform.startswith('linux') and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            raise webview.errors.WebViewException()
        webview.start()
    except webview.errors.WebViewException:
        import rich.prompt
        import litellm
        print("\nHeadless environment detected. Falling back to CLI setup:")
        
        api_key = rich.prompt.Prompt.ask("API Key", default="", password=True)
        if api_key:
            print("Testing API Key...")
            try:
                litellm.completion(
                    model="gemini/gemini-1.5-flash",
                    messages=[{"role": "user", "content": "Hello"}],
                    api_key=api_key
                )
                print("API Key verified successfully!")
            except Exception:
                import rich
                rich.print("[bold red]API Key verification failed: The provided key is invalid.[/bold red]")
                
        do_oauth = rich.prompt.Confirm.ask("Trigger Google OAuth login for Vertex AI (headless)?", default=False)
        if do_oauth:
            import google_login
            adc_path = google_login.do_login(headless=True)
            if adc_path:
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
                with open(env_path, 'a') as f:
                    f.write(f"\nGOOGLE_APPLICATION_CREDENTIALS={adc_path}\n")
                print("OAuth Successful!")

        model = rich.prompt.Prompt.ask("Model", default="")
        auth_key = rich.prompt.Prompt.ask("Auth Key", default="", password=True)
        vertex_project = rich.prompt.Prompt.ask("Vertex Project", default="")
        api.save_env(model, api_key, auth_key, vertex_project)

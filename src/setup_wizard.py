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
            <option value="gemini/gemini-2.5-flash">Gemini 2.5 Flash (Free Tier Default)</option>
            <option value="gemini/gemini-flash-latest">Gemini Flash Latest</option>
            <option value="vertex_ai/gemini-3.1-pro">Gemini 3.1 Pro (Vertex AI OAuth)</option>
            <option value="gemini/gemini-3.1-pro-preview">Gemini 3.1 Pro (AI Studio API Key)</option>
            <option value="gemini/gemini-3.5-flash-lite">Gemini 3.5 Flash Lite (Free)</option>
            <option value="gemini/antigravity-preview-09-2026">Antigravity 2.0 (Internal)</option>
            <option value="ollama/qwen2.5:7b">Ollama Qwen 2.5 7B (Local Core)</option>
            <option value="ollama/llama3.1:8b">Ollama Llama 3.1 8B (Local Core)</option>
            <option value="ollama/qwen2.5:14b">Ollama Qwen 2.5 14B (Local Core)</option>
            <option value="ollama/mistral:7b">Ollama Mistral 7B (Local Core)</option>
        </select>
    </div>
    <div class="form-group">
        <label for="ollama_api_base">OLLAMA_API_BASE (Default: http://localhost:11434)</label>
        <input type="text" id="ollama_api_base" placeholder="http://localhost:11434" value="http://localhost:11434">
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
            var ollamaApiBase = document.getElementById('ollama_api_base') ? document.getElementById('ollama_api_base').value : 'http://localhost:11434';
            
            pywebview.api.save_env(model, apiKey, authKey, vertexProject, ollamaApiBase).then(function() {
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

def test_ollama_connection(api_base=None) -> bool:
    """Test connection to the Ollama endpoint."""
    import urllib.request
    endpoint = api_base or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    url = f"{endpoint.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Neuromancer/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


class SetupApi:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def test_ollama_connection(self, endpoint=None):
        return test_ollama_connection(endpoint)

    def save_env(self, model, api_key, auth_key, vertex_project=None, ollama_api_base=None, env_path=None):
        if env_path is None:
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
            env_data['LLM_API_KEY'] = api_key.strip()
        if auth_key:
            env_data['WINTERMUTE_AUTH_KEY'] = auth_key
        if vertex_project:
            env_data['VERTEX_PROJECT'] = vertex_project
            env_data['VERTEX_LOCATION'] = 'us-central1'
            
        is_ollama = bool(model and (model.startswith("ollama/") or model.startswith("ollama_chat/")))
        base_val = (ollama_api_base or "").strip() or env_data.get('OLLAMA_API_BASE') or os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        if is_ollama or ollama_api_base:
            env_data['OLLAMA_API_BASE'] = base_val

        if is_ollama:
            online = self.test_ollama_connection(base_val)
            if not online:
                print(f"[!] Warning: Ollama daemon unreachable at {base_val}. Ensure 'ollama serve' is active.")

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
        import contextlib
        import io
        
        litellm.suppress_debug_info = True

        print("\nHeadless environment detected. Falling back to CLI setup:")
        
        api_key = rich.prompt.Prompt.ask("API Key", default="", password=True).strip()
        if api_key:
            print("Testing API Key...")
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    litellm.completion(
                        model="gemini/gemini-2.5-flash",
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

        try:
            from src.model_selector import select_model_interactive, discover_local_ollama_models
        except ImportError:
            from model_selector import select_model_interactive, discover_local_ollama_models

        discovered = discover_local_ollama_models()
        model = select_model_interactive(models=discovered)
        auth_key = rich.prompt.Prompt.ask("Auth Key", default="", password=True)
        vertex_project = rich.prompt.Prompt.ask("Vertex Project", default="")
        
        ollama_api_base = "http://localhost:11434"
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            ollama_api_base = rich.prompt.Prompt.ask("OLLAMA_API_BASE", default=os.getenv("OLLAMA_API_BASE", "http://localhost:11434")).strip()
            print(f"Testing connection to Ollama daemon at {ollama_api_base}...")
            if test_ollama_connection(ollama_api_base):
                import rich
                rich.print("[bold green]Ollama endpoint uplink established successfully![/bold green]")
            else:
                import rich
                rich.print(f"[bold yellow][!] Warning: Unable to connect to Ollama daemon at {ollama_api_base}. Ensure 'ollama serve' is running.[/bold yellow]")

        api.save_env(model, api_key, auth_key, vertex_project, ollama_api_base)

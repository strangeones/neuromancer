import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

# The exact Client ID used by gcloud CLI, ensuring full compatibility with Vertex AI without needing a custom project ID
CLIENT_CONFIG = {
    "installed": {
        "client_id": "32555940559.apps.googleusercontent.com",
        "client_secret": "ZmssLNjJy2998hD4CTg2ejr2",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

def do_login():
    print("Initiating Google Cloud Desktop OAuth Flow...")
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Save the credentials in the exact format gcloud ADC expects
    creds_data = {
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
        "type": "authorized_user"
    }
    
    # Write to ~/.config/gcloud/application_default_credentials.json
    config_dir = Path.home() / ".config" / "gcloud"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    adc_path = config_dir / "application_default_credentials.json"
    with open(adc_path, "w") as f:
        json.dump(creds_data, f, indent=2)
        
    print(f"Success! Vertex AI ADC Credentials saved to {adc_path}")
    return str(adc_path)

if __name__ == "__main__":
    do_login()


import os
import requests
import json

def load_env():
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("No API key found")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    response = requests.get(url)
    response.raise_for_status()
    models = response.json().get('models', [])
    print(f"Found {len(models)} models:")
    for m in models:
        if 'generateContent' in m['supportedGenerationMethods']:
            print(f" - {m['name']} (Version: {m['version']})")
except Exception as e:
    print(f"Error: {e}")
    if 'response' in locals():
        print(response.text)

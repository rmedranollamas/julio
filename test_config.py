from config import load_config
import json

def test_config():
    try:
        config = load_config("agent.json")
        print("Config loaded successfully")
        print(f"Gemini API Key: {config.gemini_api_key}")
        print(f"Redis URL: {config.redis_url}")
    except Exception as e:
        print(f"Error loading config: {e}")

if __name__ == "__main__":
    test_config()

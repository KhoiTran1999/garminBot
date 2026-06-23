import httpx
import json
from app.config import Config

token = Config.NOTION_TOKEN
database_id = Config.NOTION_PROMPT_DATABASE_ID

url = f"https://api.notion.com/v1/databases/{database_id}/query"
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

with httpx.Client(timeout=10.0) as client:
    response = client.post(url, headers=headers, json={})
    data = response.json()

for page in data.get("results", []):
    props = page.get("properties", {})
    
    name_prop = props.get("Name", {}).get("title", [])
    name = "".join([t.get("plain_text", "") for t in name_prop]).strip().lower()
    
    # Check active
    is_active = props.get("Active", {}).get("checkbox", True)
    
    system_prop = props.get("System Prompt", {}).get("rich_text", [])
    system_text = "".join([t.get("plain_text", "") for t in system_prop])
    
    user_prop = props.get("User Template", {}).get("rich_text", [])
    user_text = "".join([t.get("plain_text", "") for t in user_prop])
    
    model_prop = props.get("Model", {})
    model_text = ""
    if model_prop.get("type") == "rich_text":
        model_text = "".join([t.get("plain_text", "") for t in model_prop.get("rich_text", [])])
    elif model_prop.get("type") == "select":
        m = model_prop.get("select")
        if m: model_text = m.get("name", "")

    if name in ["daily_report", "sleep_analysis", "workout_analysis"]:
        print(f"\n{'='*80}")
        print(f"PROMPT: {name}")
        print(f"Active: {is_active}")
        print(f"Model: {model_text}")
        print(f"\n--- SYSTEM PROMPT ---")
        print(system_text[:3000] if system_text else "(empty)")
        print(f"\n--- USER TEMPLATE ---")
        print(user_text[:3000] if user_text else "(empty)")
        print(f"{'='*80}")

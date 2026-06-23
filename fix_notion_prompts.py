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

# 1. Fetch all pages
with httpx.Client(timeout=10.0) as client:
    response = client.post(url, headers=headers, json={})
    data = response.json()

pages = data.get("results", [])

# Identify pages
for page in pages:
    props = page.get("properties", {})
    name_prop = props.get("Name", {}).get("title", [])
    raw_name = "".join([t.get("plain_text", "") for t in name_prop])
    name = raw_name.strip().lower()
    
    system_prop = props.get("System Prompt", {}).get("rich_text", [])
    system_text = "".join([t.get("plain_text", "") for t in system_prop])
    
    page_id = page["id"]
    
    print(f"Page: {page_id} | Name: '{name}' | Raw: {repr(raw_name)} | System starts: '{system_text[:50]}...'")

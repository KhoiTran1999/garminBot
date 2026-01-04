import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def get_prompts_from_notion():
    """
    Fetches prompts from the Notion Prompt Database.
    Returns a dictionary where keys are the 'Name' (title) of the prompt 
    and values are the 'Content' (rich_text) of the prompt.
    """
    token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_PROMPT_DATABASE_ID")

    if not token or not database_id:
        print("⚠️ Warning: Missing NOTION_TOKEN or NOTION_PROMPT_DATABASE_ID. Using default prompts may fail if not handled.")
        return {}

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    # Remove filter to avoid 400 if "Active" column is missing or named differently
    # We will filter in Python instead.
    payload = {}

    print("🔄 Loading prompts from Notion...")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                print(f"❌ Notion API Error: {response.status_code} - {response.text}")
                return {}

            data = response.json()
            results = data.get("results", [])
            print(f"DEBUG: Notion API returned {len(results)} raw results.")
            
            prompts = {}

            for page in results:
                props = page.get("properties", {})
                
                # Get Name (Title) - Key
                name_prop = props.get("Name", {}).get("title", [])
                
                # FIX: Join ALL text parts, not just [0]
                full_raw_name = "".join([t.get("plain_text", "") for t in name_prop])
                prompt_key = full_raw_name.strip().lower() # Normalize to lowercase
                
                # Debug: Print Name to see what we got
                print(f"   -> Processing row: '{prompt_key}' (Raw: {repr(full_raw_name)})")

                if not prompt_key:
                    print(f"   -> Skipping row with empty Name.")
                    continue

                # Client-side Active check
                if "Active" in props:
                    is_active = props.get("Active", {}).get("checkbox", False)
                    if not is_active:
                         print(f"   -> Skipping '{prompt_key}' because Active=False")
                         continue

                # Get System Prompt (Rich Text)
                system_prop = props.get("System Prompt", {}).get("rich_text", [])
                system_text = "".join([t.get("plain_text", "") for t in system_prop]) or ""

                # Get User Template (Rich Text)
                user_prop = props.get("User Template", {}).get("rich_text", [])
                user_text = "".join([t.get("plain_text", "") for t in user_prop]) or ""
                
                # Get Model (Rich Text or Select) - Fallback to "gemini-3-flash-preview"
                # Assuming Model is a Rich Text or Select property. Based on image it looks like Multi-select or Select or Text. 
                # Let's try to get it as rich_text first, if empty then check select.
                model_text = "gemini-3-flash-preview"
                model_prop = props.get("Model", {})
                if model_prop.get("type") == "rich_text":
                     m_text = "".join([t.get("plain_text", "") for t in model_prop.get("rich_text", [])])
                     if m_text: model_text = m_text
                elif model_prop.get("type") == "select":
                    m_opt = model_prop.get("select")
                    if m_opt: model_text = m_opt.get("name")
                elif model_prop.get("type") == "multi_select":
                    m_opts = model_prop.get("multi_select", [])
                    if m_opts: model_text = m_opts[0].get("name")

                if prompt_key:
                    prompts[prompt_key] = {
                        "system_prompt": system_text,
                        "user_template": user_text,
                        "model": model_text
                    }

            print(f"✅ Loaded {len(prompts)} prompts from Notion: {', '.join(prompts.keys())}")
            return prompts

    except Exception as e:
        print(f"❌ Exception fetching prompts: {e}")
        return {}

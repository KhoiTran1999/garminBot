import os
import base64
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def inspect_voice():
    print("🔍 Inspecting Gemini Audio Output...")
    if not GEMINI_API_KEY:
        print("❌ No API Key")
        return

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        text = "Hello check."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=f"Read this: {text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Puck"
                        )
                    )
                )
            )
        )
        
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                mime = part.inline_data.mime_type
                print(f"📄 MIME Type reported: {mime}")
                
                data = base64.b64decode(part.inline_data.data)
                print(f"📦 Total Bytes: {len(data)}")
                print(f"✨ First 16 bytes (Hex): {data[:16].hex(' ')}")
                
                # Try saving as bin
                with open("unknown_audio.bin", "wb") as f:
                    f.write(data)
                print("💾 Saved raw data to 'unknown_audio.bin'")
                return

        print("❌ No audio data found")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_voice()

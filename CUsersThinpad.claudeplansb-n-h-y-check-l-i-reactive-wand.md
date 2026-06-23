# Plan to remove ROUTER9_API_KEY rotation logic

## Context
The user stated that unlike `GEMINI_API_KEY`, there is only one `ROUTER9_API_KEY` being used in the project, so there is no need for `ROUTER9_API_KEY_1`, `2`, `3` variables or rotation logic for 9Router API requests. Furthermore, the 9Router API at `https://khoitran1999-claude-server.hf.space/v1` MUST only be used with `ROUTER9_API_KEY`, never with a `GEMINI_API_KEY`. 

We need to strip out the rotation logic for 9Router keys, remove the Gemini API key fallback for 9Router, and update `ai_service.py` accordingly while preserving the rotation logic for Gemini keys (which are used for TTS).

## Modifications

### 1. `.github/workflows/*.yml`
Remove the environment variables `ROUTER9_API_KEY_1`, `ROUTER9_API_KEY_2`, and `ROUTER9_API_KEY_3` from all 4 workflow files:
- `.github/workflows/daily_report.yml`
- `.github/workflows/daily_workout_analysis.yml`
- `.github/workflows/sleep_analysis.yml`
- `.github/workflows/telegram_trigger.yml`

*Leave `ROUTER9_API_KEY: ${{ secrets.ROUTER9_API_KEY }}` intact.*

### 2. `app/config.py`
Remove the fallback `or os.getenv("GEMINI_API_KEY")` from the `ROUTER9_API_KEY` definition.
Remove the loop that dynamically loads `ROUTER9_API_KEY_1`, `2`, etc. into an array.
Change `ROUTER9_API_KEYS` (list) to just `ROUTER9_API_KEY` (string):
```python
    # Load 9Router Key (Only use ROUTER9_API_KEY, no fallback to Gemini)
    ROUTER9_API_KEY = os.getenv("ROUTER9_API_KEY")

    if not ROUTER9_API_KEY:
        print("⚠️ CẢNH BÁO: Không tìm thấy ROUTER9_API_KEY trong .env!")
```

### 3. `app/services/ai_service.py`
- Remove the `Router9KeyManager` class entirely, as rotation is no longer needed.
- Remove the global `key_manager = Router9KeyManager()` initialization.
- Refactor the four AI text generation functions (`get_ai_advice`, `get_battery_analysis_advice`, `get_workout_analysis_advice`, `get_speech_script`) to directly call `call_ai_api(Config.ROUTER9_API_KEY, model_to_use, prompt)` wrapped in a standard try-except block, returning the `default_return` value on failure.
- *Leave `GeminiKeyManager` untouched, as it is still used for the TTS functionality.*

## Verification
- Review modified files via `git diff` to ensure Gemini variables/managers are not affected.
- Observe no syntax errors are introduced in Python files.

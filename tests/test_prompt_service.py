"""
Tests for get_prompts_from_notion() focusing on:
1. Notion DB missing 'ask_help' row
2. Key name mismatch (wrong case, extra spaces)
"""
from unittest.mock import patch, MagicMock
import pytest

from app.services.prompt_service import get_prompts_from_notion


def _make_notion_response(rows: list[dict]) -> dict:
    """Build a fake Notion API response from a list of row dicts.
    Each row dict: {name: str, system_prompt: str, user_template: str, active: bool|None}
    """
    results = []
    for row in rows:
        name_parts = [{"plain_text": row["name"]}]
        props = {
            "Name": {"title": name_parts},
            "System Prompt": {"rich_text": [{"plain_text": row.get("system_prompt", "sys")}]},
            "User Template": {"rich_text": [{"plain_text": row.get("user_template", "usr")}]},
        }
        if row.get("active") is not None:
            props["Active"] = {"checkbox": row["active"]}
        results.append({"properties": props})

    return {"results": results}


def _mock_httpx(response_data: dict, status_code: int = 200):
    """Return a mock httpx.Client context manager that returns given data."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = response_data
    mock_response.text = str(response_data)

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# Case 1: Notion DB has no 'ask_help' row at all
# ---------------------------------------------------------------------------
class TestMissingAskHelp:
    def test_ask_help_absent_returns_empty_for_key(self):
        """DB has rows but none named 'ask_help' → prompts['ask_help'] is None."""
        data = _make_notion_response([
            {"name": "workout_analysis", "active": True},
            {"name": "battery_analysis", "active": True},
        ])
        with patch("app.services.prompt_service.Config") as mock_cfg, \
             patch("app.services.prompt_service.httpx.Client") as mock_cls:
            mock_cfg.NOTION_TOKEN = "fake-token"
            mock_cfg.NOTION_PROMPT_DATABASE_ID = "fake-db-id"
            mock_cfg.ROUTER9_COMBOS_MODEL = "gemini-pro"
            mock_cls.return_value = _mock_httpx(data)

            prompts = get_prompts_from_notion()

        assert "ask_help" not in prompts, (
            f"Expected 'ask_help' absent but got keys: {list(prompts.keys())}"
        )

    def test_empty_db_returns_no_prompts(self):
        """DB has zero rows → empty dict."""
        data = _make_notion_response([])
        with patch("app.services.prompt_service.Config") as mock_cfg, \
             patch("app.services.prompt_service.httpx.Client") as mock_cls:
            mock_cfg.NOTION_TOKEN = "fake-token"
            mock_cfg.NOTION_PROMPT_DATABASE_ID = "fake-db-id"
            mock_cfg.ROUTER9_COMBOS_MODEL = "gemini-pro"
            mock_cls.return_value = _mock_httpx(data)

            prompts = get_prompts_from_notion()

        assert prompts == {}


# ---------------------------------------------------------------------------
# Case 2: Name mismatch — wrong case / extra spaces
# ---------------------------------------------------------------------------
class TestKeyNormalization:
    @pytest.mark.parametrize("raw_name", [
        "Ask_Help",
        "ASK_HELP",
        " ask_help ",
        "ask_help ",   # trailing space
        " ask_help",   # leading space
    ])
    def test_case_and_space_variants_are_normalized(self, raw_name):
        """Case/leading/trailing-space variants of 'ask_help' normalize to key 'ask_help'.
        Note: space-separated ('Ask Help') is a different key ('ask help') — not normalized to underscore.
        """
        data = _make_notion_response([
            {"name": raw_name, "system_prompt": "sys", "user_template": "usr", "active": True}
        ])
        with patch("app.services.prompt_service.Config") as mock_cfg, \
             patch("app.services.prompt_service.httpx.Client") as mock_cls:
            mock_cfg.NOTION_TOKEN = "fake-token"
            mock_cfg.NOTION_PROMPT_DATABASE_ID = "fake-db-id"
            mock_cfg.ROUTER9_COMBOS_MODEL = "gemini-pro"
            mock_cls.return_value = _mock_httpx(data)

            prompts = get_prompts_from_notion()

        assert "ask_help" in prompts, (
            f"Raw name {repr(raw_name)} should normalize to 'ask_help' but got keys: {list(prompts.keys())}"
        )

    def test_key_with_extra_internal_spaces_not_normalized(self):
        """'ask  help' (double space) ≠ 'ask_help' — stays as-is after strip+lower."""
        data = _make_notion_response([
            {"name": "ask  help", "active": True}
        ])
        with patch("app.services.prompt_service.Config") as mock_cfg, \
             patch("app.services.prompt_service.httpx.Client") as mock_cls:
            mock_cfg.NOTION_TOKEN = "fake-token"
            mock_cfg.NOTION_PROMPT_DATABASE_ID = "fake-db-id"
            mock_cfg.ROUTER9_COMBOS_MODEL = "gemini-pro"
            mock_cls.return_value = _mock_httpx(data)

            prompts = get_prompts_from_notion()

        assert "ask_help" not in prompts
        assert "ask  help" in prompts  # stored as-is (double space, no underscore)


# ---------------------------------------------------------------------------
# Case 3: Active=False → skipped
# ---------------------------------------------------------------------------
class TestActiveFilter:
    def test_inactive_ask_help_not_returned(self):
        """ask_help row with Active=False must be skipped."""
        data = _make_notion_response([
            {"name": "ask_help", "active": False}
        ])
        with patch("app.services.prompt_service.Config") as mock_cfg, \
             patch("app.services.prompt_service.httpx.Client") as mock_cls:
            mock_cfg.NOTION_TOKEN = "fake-token"
            mock_cfg.NOTION_PROMPT_DATABASE_ID = "fake-db-id"
            mock_cfg.ROUTER9_COMBOS_MODEL = "gemini-pro"
            mock_cls.return_value = _mock_httpx(data)

            prompts = get_prompts_from_notion()

        assert "ask_help" not in prompts

    def test_active_ask_help_returned(self):
        """ask_help row with Active=True must be present."""
        data = _make_notion_response([
            {"name": "ask_help", "system_prompt": "Help sys", "user_template": "Help usr", "active": True}
        ])
        with patch("app.services.prompt_service.Config") as mock_cfg, \
             patch("app.services.prompt_service.httpx.Client") as mock_cls:
            mock_cfg.NOTION_TOKEN = "fake-token"
            mock_cfg.NOTION_PROMPT_DATABASE_ID = "fake-db-id"
            mock_cfg.ROUTER9_COMBOS_MODEL = "gemini-pro"
            mock_cls.return_value = _mock_httpx(data)

            prompts = get_prompts_from_notion()

        assert "ask_help" in prompts
        assert prompts["ask_help"]["system_prompt"] == "Help sys"
        assert prompts["ask_help"]["user_template"] == "Help usr"


import os
import unittest
from unittest.mock import patch, MagicMock
from app.services.ai_service import GeminiKeyManager

class TestGeminiKeyManager(unittest.TestCase):
    def setUp(self):
        # Reset environment variables for testing
        if "GEMINI_API_KEY" in os.environ: del os.environ["GEMINI_API_KEY"]
        if "GEMINI_API_KEY_1" in os.environ: del os.environ["GEMINI_API_KEY_1"]
        if "GEMINI_API_KEY_2" in os.environ: del os.environ["GEMINI_API_KEY_2"]
        if "GEMINI_API_KEY_3" in os.environ: del os.environ["GEMINI_API_KEY_3"]

    def test_load_single_key(self):
        os.environ["GEMINI_API_KEY"] = "key1"
        manager = GeminiKeyManager()
        self.assertEqual(manager.keys, ["key1"])
        self.assertEqual(manager.get_current_key(), "key1")

    def test_load_multiple_keys(self):
        os.environ["GEMINI_API_KEY"] = "key1"
        os.environ["GEMINI_API_KEY_1"] = "key2"
        os.environ["GEMINI_API_KEY_2"] = "key3"
        manager = GeminiKeyManager()
        self.assertEqual(manager.keys, ["key1", "key2", "key3"])

    def test_rotation(self):
        os.environ["GEMINI_API_KEY"] = "key1"
        os.environ["GEMINI_API_KEY_1"] = "key2"
        manager = GeminiKeyManager()
        
        self.assertEqual(manager.get_current_key(), "key1")
        
        key = manager.rotate_key()
        self.assertEqual(key, "key2")
        self.assertEqual(manager.get_current_key(), "key2")
        
        key = manager.rotate_key()
        self.assertEqual(key, "key1")
        self.assertEqual(manager.get_current_key(), "key1")

    def test_no_keys(self):
        manager = GeminiKeyManager()
        self.assertEqual(manager.keys, [])
        self.assertIsNone(manager.get_current_key())
        self.assertIsNone(manager.rotate_key())

if __name__ == '__main__':
    unittest.main()

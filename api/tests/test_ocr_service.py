import pytest
from unittest.mock import patch, MagicMock
from api.services.ocr_service import parse_questions_from_text, _extract_text_from_pil_image
from PIL import Image

pytestmark = pytest.mark.unit

class TestParseQuestionsFromText:
    def test_empty_string_returns_empty_list(self):
        assert parse_questions_from_text("") == []
        assert parse_questions_from_text(None) == []

    def test_removes_numbers_and_bullets(self):
        raw = "1. What is your name?\n* How old are you?\n- Where do you live?\n2) Do you like dogs?"
        questions = parse_questions_from_text(raw)
        assert questions == [
            "What is your name?",
            "How old are you?",
            "Where do you live?",
            "Do you like dogs?"
        ]

    def test_ignores_short_lines(self):
        raw = "1. Short\nWhat is your name?\nHi\n- Where do you live?"
        questions = parse_questions_from_text(raw)
        assert questions == [
            "What is your name?",
            "Where do you live?"
        ]


class TestExtractTextFromPilImage:
    @patch("api.services.ocr_service._get_api_keys")
    @patch("api.services.ocr_service.genai.GenerativeModel")
    def test_extracts_text_successfully(self, mock_model_cls, mock_get_keys, monkeypatch):
        mock_get_keys.return_value = ["fake-key"]
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "1. Mocked question?"
        mock_model.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_model
        
        image = Image.new('RGB', (10, 10))
        result = _extract_text_from_pil_image(image)
        
        assert result == "1. Mocked question?"
        mock_model.generate_content.assert_called_once()

    @patch("api.services.ocr_service._get_api_keys")
    def test_returns_empty_if_no_keys(self, mock_get_keys):
        mock_get_keys.return_value = []
        image = Image.new('RGB', (10, 10))
        result = _extract_text_from_pil_image(image)
        assert result == ""

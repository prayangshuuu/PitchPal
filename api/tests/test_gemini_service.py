import json
from unittest.mock import MagicMock

import pytest

from api.services import gemini_service

pytestmark = pytest.mark.unit


def _mock_response(payload):
    resp = MagicMock()
    resp.text = json.dumps(payload)
    return resp


def _install_mock_model(monkeypatch, mock_model):
    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", MagicMock(return_value=mock_model))


class TestCleanJsonResponse:
    def test_cleans_markdown_json_blocks(self):
        dirty = "```json\n{\"key\": \"value\"}\n```"
        cleaned = gemini_service._clean_json_response(dirty)
        assert cleaned == "{\"key\": \"value\"}"

    def test_cleans_markdown_blocks_without_language(self):
        dirty = "```\n{\"key\": \"value\"}\n```"
        cleaned = gemini_service._clean_json_response(dirty)
        assert cleaned == "{\"key\": \"value\"}"

    def test_leaves_clean_json_alone(self):
        clean = "{\"key\": \"value\"}"
        assert gemini_service._clean_json_response(clean) == clean

    def test_strips_whitespace(self):
        dirty = "   \n\n  {\"key\": \"value\"}  \n "
        assert gemini_service._clean_json_response(dirty) == "{\"key\": \"value\"}"



class TestGenerateInterviewQuestions:
    def test_returns_list_of_question_dicts_on_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        payload = [{"id": i, "text": f"Question {i}", "category": "technical"} for i in range(1, 6)]
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_response(payload)
        _install_mock_model(monkeypatch, mock_model)

        questions = gemini_service.generate_interview_questions("sde", "junior")

        assert isinstance(questions, list)
        assert len(questions) == 5
        for q in questions:
            assert {"id", "text", "category"} <= set(q.keys())

    def test_can_customize_count(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        payload = [{"id": i, "text": f"Question {i}", "category": "technical"} for i in range(1, 4)]
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_response(payload)
        _install_mock_model(monkeypatch, mock_model)

        questions = gemini_service.generate_interview_questions("pm", "mid", count=3)

        assert len(questions) == 3
        prompt_used = mock_model.generate_content.call_args[0][0]
        assert "3" in prompt_used

    def test_falls_back_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        questions = gemini_service.generate_interview_questions("sde", "junior")

        assert questions == gemini_service._get_fallback_questions("sde", "junior", 5)

    def test_falls_back_on_api_exception(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("Gemini is down")
        _install_mock_model(monkeypatch, mock_model)

        questions = gemini_service.generate_interview_questions("sde", "mid")

        assert questions == gemini_service._get_fallback_questions("sde", "mid", 5)

    def test_falls_back_on_malformed_json(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "not valid json"
        _install_mock_model(monkeypatch, mock_model)

        questions = gemini_service.generate_interview_questions("sde", "senior")

        assert questions == gemini_service._get_fallback_questions("sde", "senior", 5)

    @pytest.mark.parametrize("role", ["sde", "pm", "designer"])
    @pytest.mark.parametrize("difficulty", ["junior", "mid", "senior"])
    def test_fallback_questions_exist_for_every_role_difficulty_combo(self, role, difficulty):
        questions = gemini_service._get_fallback_questions(role, difficulty, 5)

        assert len(questions) == 5
        for q in questions:
            assert {"id", "text", "category"} <= set(q.keys())

    def test_fallback_for_unknown_role_returns_generic_questions(self):
        questions = gemini_service._get_fallback_questions("unknown-role", "junior", 5)

        assert len(questions) == 5
        assert all(q["category"] == "behavioral" for q in questions)


class TestEvaluateAnswer:
    def test_returns_expected_shape_on_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        payload = {
            "score": 82,
            "clarity_score": 80,
            "depth_score": 85,
            "communication_score": 81,
            "feedback": "Well-structured answer with a concrete example.",
            "strengths": ["Clear structure"],
            "improvements": ["Add more metrics"],
        }
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_response(payload)
        _install_mock_model(monkeypatch, mock_model)

        result = gemini_service.evaluate_answer("Tell me about yourself.", "I am a software engineer...")

        assert set(result.keys()) >= {
            "score",
            "clarity_score",
            "depth_score",
            "communication_score",
            "feedback",
            "strengths",
            "improvements",
            "raw_response",
        }
        assert 0 <= result["score"] <= 100
        assert 0 <= result["clarity_score"] <= 100
        assert 0 <= result["depth_score"] <= 100
        assert 0 <= result["communication_score"] <= 100
        assert isinstance(result["feedback"], str)
        assert isinstance(result["strengths"], list)
        assert isinstance(result["improvements"], list)
        assert json.loads(result["raw_response"]) == payload

    def test_falls_back_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        result = gemini_service.evaluate_answer("Q", "A")

        assert result["score"] == 50
        assert result["strengths"] == []
        assert result["improvements"] == []
        assert isinstance(result["feedback"], str) and result["feedback"]

    def test_falls_back_on_api_exception(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("Gemini is down")
        _install_mock_model(monkeypatch, mock_model)

        result = gemini_service.evaluate_answer("Q", "A")

        assert result["score"] == 50

    def test_all_fields_present_on_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        result = gemini_service.evaluate_answer("Q", "A")

        assert set(result.keys()) == {
            "score",
            "clarity_score",
            "depth_score",
            "communication_score",
            "feedback",
            "strengths",
            "improvements",
            "raw_response",
        }
        assert result["raw_response"] is None


class TestGeneratePitchFeedback:
    def test_returns_expected_shape_on_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        payload = {
            "score": 75,
            "feedback": "Engaging pitch, tighten the close.",
            "strengths": ["Strong hook"],
            "improvements": ["Clarify the ask"],
        }
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_response(payload)
        _install_mock_model(monkeypatch, mock_model)

        result = gemini_service.generate_pitch_feedback("Our product helps teams...", pitch_type="elevator")

        assert set(result.keys()) >= {"score", "feedback", "strengths", "improvements"}
        assert 0 <= result["score"] <= 100
        assert isinstance(result["feedback"], str)
        assert isinstance(result["strengths"], list)
        assert isinstance(result["improvements"], list)

    def test_falls_back_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        result = gemini_service.generate_pitch_feedback("Our product helps teams...")

        assert result["score"] == 50
        assert result["strengths"] == []
        assert result["improvements"] == []

    def test_falls_back_on_api_exception(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("Gemini is down")
        _install_mock_model(monkeypatch, mock_model)

        result = gemini_service.generate_pitch_feedback("Our product helps teams...")

        assert result["score"] == 50

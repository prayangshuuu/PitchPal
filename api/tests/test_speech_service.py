from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import ResourceExhausted

from api.services import speech_service

pytestmark = pytest.mark.unit


def _mock_audio_file(name="files/audio-123"):
    f = MagicMock()
    f.name = name
    return f


def _mock_response(text):
    resp = MagicMock()
    resp.text = text
    return resp


def _set_models(monkeypatch, primary="model-a", fallbacks="model-b,model-c"):
    monkeypatch.setenv("GEMINI_MODEL", primary)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", fallbacks)


class TestTranscribeAudioWithConfidence:
    def test_returns_transcript_on_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "key1")
        _set_models(monkeypatch)
        audio_file = _mock_audio_file()
        monkeypatch.setattr(speech_service.genai, "upload_file", MagicMock(return_value=audio_file))
        monkeypatch.setattr(speech_service.genai, "configure", MagicMock())
        delete_file = MagicMock()
        monkeypatch.setattr(speech_service.genai, "delete_file", delete_file)

        model = MagicMock()
        model.generate_content.return_value = _mock_response("Hello, this is my answer.")
        monkeypatch.setattr(speech_service.genai, "GenerativeModel", MagicMock(return_value=model))

        result = speech_service.transcribe_audio_with_confidence(str(tmp_path / "audio.webm"))

        assert result["text"] == "Hello, this is my answer."
        assert result["confidence"] == 0.95
        assert result["language"] == "en"
        delete_file.assert_called_once_with(audio_file.name)

    def test_falls_back_when_api_key_missing(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        result = speech_service.transcribe_audio_with_confidence(str(tmp_path / "audio.webm"))

        assert result["text"] == ""
        assert result["confidence"] == 0
        assert "error" in result

    def test_falls_back_to_next_model_when_primary_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "key1")
        _set_models(monkeypatch, primary="model-a", fallbacks="model-b")
        monkeypatch.setattr(speech_service.genai, "upload_file", MagicMock(return_value=_mock_audio_file()))
        monkeypatch.setattr(speech_service.genai, "configure", MagicMock())
        monkeypatch.setattr(speech_service.genai, "delete_file", MagicMock())

        good_model = MagicMock()
        good_model.generate_content.return_value = _mock_response("Recovered via fallback model.")

        def model_factory(name):
            if name == "model-a":
                raise ResourceExhausted("quota exceeded")
            return good_model

        monkeypatch.setattr(speech_service.genai, "GenerativeModel", MagicMock(side_effect=model_factory))

        result = speech_service.transcribe_audio_with_confidence(str(tmp_path / "audio.webm"))

        assert result["text"] == "Recovered via fallback model."

    def test_falls_back_to_next_key_when_upload_fails(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "key1,key2")
        _set_models(monkeypatch, primary="model-a", fallbacks="")
        monkeypatch.setattr(speech_service.genai, "configure", MagicMock())
        monkeypatch.setattr(speech_service.genai, "delete_file", MagicMock())

        audio_file = _mock_audio_file()

        def upload_factory(*args, **kwargs):
            # First key's upload fails outright; second key's succeeds.
            if upload_factory.calls == 0:
                upload_factory.calls += 1
                raise RuntimeError("upload failed for key1")
            return audio_file
        upload_factory.calls = 0

        monkeypatch.setattr(speech_service.genai, "upload_file", MagicMock(side_effect=upload_factory))

        model = MagicMock()
        model.generate_content.return_value = _mock_response("Transcribed with second key.")
        monkeypatch.setattr(speech_service.genai, "GenerativeModel", MagicMock(return_value=model))

        result = speech_service.transcribe_audio_with_confidence(str(tmp_path / "audio.webm"))

        assert result["text"] == "Transcribed with second key."

    def test_returns_error_when_every_model_and_key_fail(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "key1,key2")
        _set_models(monkeypatch, primary="model-a", fallbacks="model-b")
        monkeypatch.setattr(speech_service.genai, "configure", MagicMock())
        monkeypatch.setattr(speech_service.genai, "delete_file", MagicMock())
        monkeypatch.setattr(speech_service.genai, "upload_file", MagicMock(return_value=_mock_audio_file()))

        model = MagicMock()
        model.generate_content.side_effect = ResourceExhausted("quota exceeded")
        monkeypatch.setattr(speech_service.genai, "GenerativeModel", MagicMock(return_value=model))

        result = speech_service.transcribe_audio_with_confidence(str(tmp_path / "audio.webm"))

        assert result["text"] == ""
        assert result["confidence"] == 0
        assert "error" in result


class TestValidateAudioFile:
    def test_accepts_allowed_type(self):
        audio_file = MagicMock(content_type="audio/webm", size=1000)
        assert speech_service.validate_audio_file(audio_file) == {"valid": True}

    def test_rejects_disallowed_type(self):
        audio_file = MagicMock(content_type="application/zip", size=1000)
        result = speech_service.validate_audio_file(audio_file)
        assert result["valid"] is False

    def test_rejects_oversized_file(self):
        audio_file = MagicMock(content_type="audio/webm", size=52428800 + 1)
        result = speech_service.validate_audio_file(audio_file)
        assert result["valid"] is False

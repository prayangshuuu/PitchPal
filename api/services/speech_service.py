import os
import logging
import google.generativeai as genai
from google.api_core.exceptions import NotFound, ResourceExhausted, ServiceUnavailable, InternalServerError, PermissionDenied, InvalidArgument

from .gemini_service import _get_api_keys, _get_models_to_try

logger = logging.getLogger(__name__)

TRANSCRIBE_PROMPT = (
    "Transcribe this audio to text as accurately as possible, including any technical "
    "terms, names, and numbers. Return ONLY the transcribed text, nothing else."
)


def transcribe_audio_with_confidence(audio_file_path):
    """Transcribe audio using Gemini, retrying across every configured API key
    and model so a single unavailable model/key doesn't sink transcription."""
    keys = _get_api_keys()
    if not keys:
        logger.error("GEMINI_API_KEY environment variable not found.")
        return {"text": "", "confidence": 0, "error": "Missing API key"}

    models_to_try = _get_models_to_try()
    last_error = None

    for key in keys:
        genai.configure(api_key=key)
        audio_file = None
        try:
            audio_file = genai.upload_file(audio_file_path, mime_type="audio/webm", display_name="audio_recording")

            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([TRANSCRIBE_PROMPT, audio_file])
                    transcribed_text = response.text.strip()
                    if transcribed_text:
                        return {
                            "text": transcribed_text,
                            "confidence": 0.95,  # Gemini doesn't return confidence, assume high
                            "language": "en"
                        }
                except (NotFound, ResourceExhausted, ServiceUnavailable, InternalServerError, PermissionDenied, InvalidArgument) as e:
                    logger.warning(f"Model {model_name} unavailable for transcription, trying next. Error: {e}")
                    last_error = e
                except Exception as e:
                    logger.warning(f"Unexpected error transcribing with model {model_name}: {e}")
                    last_error = e

        except Exception as e:
            logger.warning(f"Audio upload failed with key {key[:8]}..., trying next key. Error: {e}")
            last_error = e
        finally:
            if audio_file is not None:
                try:
                    genai.delete_file(audio_file.name)
                except Exception:
                    pass

    logger.error(f"Transcription failed after exhausting all models/keys: {last_error}")
    return {
        "text": "",
        "confidence": 0,
        "error": str(last_error) if last_error else "Unknown transcription error"
    }

def validate_audio_file(audio_file):
    ALLOWED_TYPES = ['audio/webm', 'audio/wav', 'audio/mpeg', 'audio/m4a', 'audio/mp4', 'audio/ogg', 'video/webm']
    MAX_FILE_SIZE = 52428800  # 50MB
    MAX_DURATION = 300  # 5 minutes
    
    # Check MIME type
    if audio_file.content_type not in ALLOWED_TYPES:
        return {"valid": False, "error": f"Invalid file type: {audio_file.content_type}. Allowed: webm, wav, mp3, m4a, mp4, ogg"}
    
    # Check file size
    if audio_file.size > MAX_FILE_SIZE:
        return {"valid": False, "error": "File too large. Max 50MB"}
    
    return {"valid": True}

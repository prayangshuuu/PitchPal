import os
import json
import logging
import google.generativeai as genai
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.split(',')[0].strip())

def transcribe_audio_with_confidence(audio_file_path):
    try:
        # Read audio file
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        # Upload to Gemini (temporary)
        audio_file = genai.upload_file(audio_file_path, mime_type="audio/webm", display_name="audio_recording")
        
        # Transcribe using Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([
            "Please transcribe this audio to text. Return ONLY the transcribed text, nothing else.",
            audio_file
        ])
        
        transcribed_text = response.text.strip()
        
        # Delete uploaded file from Gemini
        genai.delete_file(audio_file.name)
        
        return {
            "text": transcribed_text,
            "confidence": 0.95,  # Gemini doesn't return confidence, assume high
            "language": "en"
        }
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "text": "",
            "confidence": 0,
            "error": str(e)
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

import logging
import os
import re

import google.generativeai as genai
from PIL import Image

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = (
    "You are looking at an image containing a list of interview or pitch practice questions "
    "(it may be a screenshot, a photo of a printed page, or a slide). Extract every distinct "
    "question exactly as written, one per line, with no numbering, bullets, or commentary. "
    "If the image contains no readable questions, respond with an empty string."
)


from google.api_core.exceptions import NotFound

def _get_api_keys():
    api_key_str = os.getenv('GEMINI_API_KEY')
    if not api_key_str:
        logger.error("GEMINI_API_KEY environment variable not found; cannot run OCR extraction.")
        return []
    return [k.strip() for k in api_key_str.split(',') if k.strip()]

def _extract_text_from_pil_image(image: Image.Image) -> str:
    keys = _get_api_keys()
    if not keys:
        return ""
        
    primary_model = os.getenv('GEMINI_MODEL', 'gemini-3.7-flash')
    fallback_models_str = os.getenv('GEMINI_FALLBACK_MODELS', 'gemini-2.5-flash,gemini-3.5-flash')
    models_to_try = [primary_model] + [m.strip() for m in fallback_models_str.split(',') if m.strip()]
    
    last_error = None
    for model_name in models_to_try:
        for key in keys:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    [_EXTRACTION_PROMPT, image],
                    generation_config=genai.types.GenerationConfig(temperature=0.0, max_output_tokens=800),
                )
                return (response.text or "").strip()
            except NotFound as e:
                logger.warning(f"Model {model_name} not found with key {key[:8]}..., trying next fallback. Error: {e}")
                last_error = e
            except Exception as e:
                logger.warning(f"Error extracting text from image via Gemini model {model_name} and key {key[:8]}...: {e}")
                last_error = e
            
    if last_error:
        logger.error(f"Failed to extract text after trying all models and keys. Last error: {last_error}")
    return ""


def extract_text_from_image(file_path: str) -> str:
    """Extract question text from an uploaded image file using Gemini vision."""
    with Image.open(file_path) as image:
        image.load()
        return _extract_text_from_pil_image(image)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract question text from an uploaded PDF by rendering each page to an image."""
    try:
        from pdf2image import convert_from_path

        pages = convert_from_path(file_path, dpi=200)
    except Exception as e:
        logger.error(f"Error rendering PDF to images (is poppler installed?): {e}")
        return ""

    texts = [_extract_text_from_pil_image(page) for page in pages]
    return "\n".join(t for t in texts if t)


def parse_questions_from_text(raw_text: str) -> list:
    """Split Gemini's extracted text into a clean list of individual question strings."""
    if not raw_text:
        return []
    questions = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        cleaned = re.sub(r'^[\d]+[.)]\s*', '', cleaned)
        cleaned = re.sub(r'^[-•*]\s*', '', cleaned)
        cleaned = cleaned.strip()
        if len(cleaned) >= 8:
            questions.append(cleaned)
    return questions

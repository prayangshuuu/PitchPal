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


def _get_model():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not found; cannot run OCR extraction.")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _extract_text_from_pil_image(image: Image.Image) -> str:
    model = _get_model()
    if model is None:
        return ""
    try:
        response = model.generate_content(
            [_EXTRACTION_PROMPT, image],
            generation_config=genai.types.GenerationConfig(temperature=0.0, max_output_tokens=800),
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.error(f"Error extracting text from image via Gemini: {e}")
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

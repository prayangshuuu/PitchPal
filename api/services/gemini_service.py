import os
import json
import logging
import google.generativeai as genai
from google.api_core.exceptions import NotFound, ResourceExhausted, ServiceUnavailable, InternalServerError, PermissionDenied, InvalidArgument
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _get_api_keys():
    api_key_str = os.getenv('GEMINI_API_KEY')
    if not api_key_str:
        logger.error("GEMINI_API_KEY environment variable not found.")
        return []
    return [k.strip() for k in api_key_str.split(',') if k.strip()]

api_keys = _get_api_keys()
if api_keys:
    genai.configure(api_key=api_keys[0])

def _clean_json_response(text: str) -> str:
    """Helper to clean markdown code blocks from Gemini JSON response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def _generate_content_with_fallback(prompt: str, generation_config=None):
    """Helper to call Gemini API with fallback models."""
    primary_model = os.getenv('GEMINI_MODEL', 'gemini-3.7-flash')
    fallback_models_str = os.getenv('GEMINI_FALLBACK_MODELS', 'gemini-2.5-flash,gemini-3.5-flash')
    models_to_try = [primary_model] + [m.strip() for m in fallback_models_str.split(',') if m.strip()]
    keys = _get_api_keys()
    if not keys:
        models_to_try = []

    last_error = None
    for model_name in models_to_try:
        for key in keys:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name)
                if generation_config:
                    return model.generate_content(prompt, generation_config=generation_config)
                else:
                    return model.generate_content(prompt)
            except (NotFound, ResourceExhausted, ServiceUnavailable, InternalServerError, PermissionDenied, InvalidArgument) as e:
                logger.warning(f"Model {model_name} with key {key[:8]}... failed or unavailable, trying next. Error: {e}")
                last_error = e
            except Exception as e:
                logger.warning(f"Unexpected error with model {model_name} and key {key[:8]}..., trying next. Error: {e}")
                last_error = e

    if last_error:
        raise last_error
    raise RuntimeError("No models available to try")

def _get_fallback_questions(role: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
    """Return hardcoded fallback questions."""
    role = role.lower()
    difficulty = difficulty.lower()
    
    fallbacks = {
        "sde": {
            "junior": [
                {"id": 1, "text": "Can you explain the difference between a list and a tuple in Python?", "category": "technical"},
                {"id": 2, "text": "Describe a time when you had to learn a new technology quickly.", "category": "behavioral"},
                {"id": 3, "text": "How do you handle errors and exceptions in your code?", "category": "technical"},
                {"id": 4, "text": "What is version control and why is it important?", "category": "technical"},
                {"id": 5, "text": "Tell me about a challenging bug you fixed.", "category": "behavioral"}
            ],
            "mid": [
                {"id": 1, "text": "How would you design a rate limiter for an API?", "category": "system design"},
                {"id": 2, "text": "Explain the concept of dependency injection.", "category": "technical"},
                {"id": 3, "text": "Describe a time you had to optimize the performance of an application.", "category": "behavioral"},
                {"id": 4, "text": "How do you ensure your code is testable and maintainable?", "category": "technical"},
                {"id": 5, "text": "Tell me about a time you disagreed with a senior engineer's technical decision.", "category": "behavioral"}
            ],
            "senior": [
                {"id": 1, "text": "Design a scalable microservices architecture for an e-commerce platform.", "category": "system design"},
                {"id": 2, "text": "How do you mentor junior developers and foster a good engineering culture?", "category": "leadership"},
                {"id": 3, "text": "Discuss the trade-offs between SQL and NoSQL databases for different use cases.", "category": "technical"},
                {"id": 4, "text": "Tell me about a project that failed and what you learned from it.", "category": "behavioral"},
                {"id": 5, "text": "How do you approach securing a large-scale web application?", "category": "technical"}
            ]
        },
        "pm": {
            "junior": [
                {"id": 1, "text": "What is your favorite product and how would you improve it?", "category": "product sense"},
                {"id": 2, "text": "How do you prioritize features for a new release?", "category": "product execution"},
                {"id": 3, "text": "Tell me about a time you worked with a difficult stakeholder.", "category": "behavioral"},
                {"id": 4, "text": "How would you measure the success of a new feature?", "category": "analytical"},
                {"id": 5, "text": "What is Agile methodology in your own words?", "category": "technical"}
            ],
            "mid": [
                {"id": 1, "text": "How do you handle a situation where engineering says a feature will take twice as long as expected?", "category": "behavioral"},
                {"id": 2, "text": "Design a new feature for Uber to improve accessibility.", "category": "product sense"},
                {"id": 3, "text": "How do you define the MVP for a complex new product?", "category": "product execution"},
                {"id": 4, "text": "Describe a time you used data to change a product decision.", "category": "analytical"},
                {"id": 5, "text": "How do you balance technical debt with shipping new features?", "category": "technical"}
            ],
            "senior": [
                {"id": 1, "text": "How do you develop a product strategy and align the company around it?", "category": "leadership"},
                {"id": 2, "text": "You notice a 15% drop in user engagement. How do you investigate this?", "category": "analytical"},
                {"id": 3, "text": "Tell me about a time you launched a product that failed to meet its goals.", "category": "behavioral"},
                {"id": 4, "text": "How do you manage a portfolio of products with competing resources?", "category": "product execution"},
                {"id": 5, "text": "Design a monetization strategy for a free social media app.", "category": "product sense"}
            ]
        },
        "designer": {
            "junior": [
                {"id": 1, "text": "Walk me through your design process for a recent project.", "category": "process"},
                {"id": 2, "text": "How do you handle negative feedback on your designs?", "category": "behavioral"},
                {"id": 3, "text": "What is the difference between UX and UI?", "category": "technical"},
                {"id": 4, "text": "How do you ensure your designs are accessible?", "category": "technical"},
                {"id": 5, "text": "Tell me about a design challenge you faced and how you overcame it.", "category": "behavioral"}
            ],
            "mid": [
                {"id": 1, "text": "How do you balance business goals with user needs?", "category": "process"},
                {"id": 2, "text": "Describe a time you advocated for the user against stakeholder pushback.", "category": "behavioral"},
                {"id": 3, "text": "How do you hand off designs to engineering to ensure smooth implementation?", "category": "process"},
                {"id": 4, "text": "Critique the design of a popular app. What would you change?", "category": "technical"},
                {"id": 5, "text": "How do you incorporate user research into your design decisions?", "category": "process"}
            ],
            "senior": [
                {"id": 1, "text": "How do you establish and scale a design system across multiple products?", "category": "leadership"},
                {"id": 2, "text": "Tell me about a time you led a major redesign of a product.", "category": "behavioral"},
                {"id": 3, "text": "How do you mentor and grow other designers on your team?", "category": "leadership"},
                {"id": 4, "text": "How do you measure the impact of design on business metrics?", "category": "analytical"},
                {"id": 5, "text": "Design an interface for a complex dashboard. What are the key considerations?", "category": "technical"}
            ]
        }
    }
    
    # Provide generic questions if role is not found
    generic_questions = [
        {"id": 1, "text": "Tell me about yourself.", "category": "behavioral"},
        {"id": 2, "text": "Why do you want to work here?", "category": "behavioral"},
        {"id": 3, "text": "What are your strengths and weaknesses?", "category": "behavioral"},
        {"id": 4, "text": "Describe a time you overcame a challenge.", "category": "behavioral"},
        {"id": 5, "text": "Where do you see yourself in 5 years?", "category": "behavioral"}
    ]
    
    questions = fallbacks.get(role, {}).get(difficulty, generic_questions)
    return questions[:count]

def generate_interview_questions(role: str, difficulty: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate realistic interview questions using Gemini."""
    if not os.getenv('GEMINI_API_KEY'):
        logger.error("API key missing. Falling back to default questions.")
        return _get_fallback_questions(role, difficulty, count)
        
    try:
        prompt = (
            f"Generate exactly {count} realistic interview questions for a {role} role at "
            f"{difficulty} level. Return ONLY valid JSON as a list of dictionaries with "
            f"keys 'id', 'text', and 'category'. Do not include markdown formatting like ```json."
        )
        
        response = _generate_content_with_fallback(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )

        cleaned_response = _clean_json_response(response.text)
        return json.loads(cleaned_response)

    except Exception as e:
        logger.error(f"Error generating interview questions: {e}")
        return _get_fallback_questions(role, difficulty, count)

def evaluate_answer(question_text: str, answer_text: str, mode: str = "interview") -> Dict[str, Any]:
    """Evaluate an answer using Gemini."""
    fallback_response = {
        "score": 50,
        "clarity_score": 50,
        "depth_score": 50,
        "communication_score": 50,
        "feedback": "Unable to generate detailed feedback at this time. Keep practicing!",
        "strengths": [],
        "improvements": [],
        "raw_response": None
    }
    
    if not os.getenv('GEMINI_API_KEY'):
        logger.error("API key missing. Returning fallback evaluation.")
        return fallback_response

    try:
        prompt = (
            f"Evaluate this {mode} answer to the question: '{question_text}'.\n"
            f"Answer: '{answer_text}'\n"
            "Evaluate on clarity (0-100), depth (0-100), communication (0-100). "
            "Return ONLY JSON with keys: 'score' (average), 'clarity_score', 'depth_score', "
            "'communication_score', 'feedback' (string), 'strengths' (list of strings), "
            "'improvements' (list of strings). Do not include markdown formatting."
        )
        
        response = _generate_content_with_fallback(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )

        cleaned_response = _clean_json_response(response.text)
        parsed = json.loads(cleaned_response)
        parsed["raw_response"] = cleaned_response
        return parsed

    except Exception as e:
        finish_reason = None
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            pass
        logger.error(f"Error evaluating answer (finish_reason={finish_reason}): {e}")
        return fallback_response

def generate_pitch_feedback(pitch_text: str, pitch_type: str = "elevator") -> Dict[str, Any]:
    """Evaluate a pitch using Gemini."""
    fallback_response = {
        "score": 50,
        "feedback": "Unable to generate detailed pitch feedback at this time.",
        "strengths": [],
        "improvements": []
    }
    
    if not os.getenv('GEMINI_API_KEY'):
        logger.error("API key missing. Returning fallback pitch evaluation.")
        return fallback_response

    try:
        prompt = (
            f"Evaluate this {pitch_type} pitch on clarity, persuasiveness, engagement, and pacing.\n"
            f"Pitch: '{pitch_text}'\n"
            "Return ONLY JSON with keys: 'score' (0-100), 'feedback' (string summary), "
            "'strengths' (list of strings), 'improvements' (list of strings). "
            "Do not include markdown formatting."
        )
        
        response = _generate_content_with_fallback(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )

        cleaned_response = _clean_json_response(response.text)
        return json.loads(cleaned_response)

    except Exception as e:
        logger.error(f"Error generating pitch feedback: {e}")
        return fallback_response

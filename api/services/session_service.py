import json

from django.db.models import Avg, Max, Min
from django.utils import timezone

from ..models import Answer, Evaluation, ProgressMetric, Question, Session
from . import gemini_service

QUESTIONS_PER_SESSION = 5


def generate_questions_for_session(session, uploaded_questions=None, count=QUESTIONS_PER_SESSION):
    """Populate a freshly created session with questions.

    Uses any user-supplied question text first (from an OCR'd upload), then tops up
    the remainder with AI-generated questions so every session has exactly `count`
    questions regardless of how many were successfully extracted from an upload.
    """
    uploaded_questions = [q.strip() for q in (uploaded_questions or []) if q and q.strip()]
    entries = [(text, "behavioral") for text in uploaded_questions[:count]]

    remaining = count - len(entries)
    if remaining > 0:
        generated = gemini_service.generate_interview_questions(session.role, session.difficulty, count=remaining)
        entries += [
            (g.get("text", ""), str(g.get("category", "behavioral"))[:20]) for g in generated[:remaining]
        ]

    return Question.objects.bulk_create([
        Question(session=session, question_number=index, text=text, category=category)
        for index, (text, category) in enumerate(entries, start=1)
    ])


def submit_answer(session, question, answer_text, answer_type='text', audio_file=None, transcribed_text=None, transcription_confidence=0, is_transcribed=False):
    """Record an answer, evaluate it, and complete the session if this was the last question."""
    answer = Answer.objects.create(
        question=question, 
        user_text=answer_text,
        answer_type=answer_type,
        audio_file=audio_file,
        transcribed_text=transcribed_text,
        transcription_confidence=transcription_confidence,
        is_transcribed=is_transcribed
    )

    result = gemini_service.evaluate_answer(question.text, answer_text, mode=session.mode)
    evaluation = Evaluation.objects.create(
        answer=answer,
        score=result.get("score", 50),
        clarity_score=result.get("clarity_score"),
        depth_score=result.get("depth_score"),
        communication_score=result.get("communication_score"),
        feedback=result.get("feedback", ""),
        strengths=json.dumps(result.get("strengths", [])),
        improvements=json.dumps(result.get("improvements", [])),
    )

    total_questions = session.questions.count()
    is_last_question = question.question_number >= total_questions
    if is_last_question:
        _complete_session(session)

    return answer, evaluation, is_last_question


def _complete_session(session):
    evaluations = Evaluation.objects.filter(answer__question__session=session)
    avg = evaluations.aggregate(avg=Avg("score"))["avg"]
    session.overall_score = round(avg) if avg is not None else None
    session.status = "completed"
    session.save(update_fields=["overall_score", "status", "updated_at"])
    update_progress_metric(session.user, session.role, session.mode)


def update_progress_metric(user, role, mode):
    completed = Session.objects.filter(
        user=user, role=role, mode=mode, status="completed", overall_score__isnull=False
    )
    aggregates = completed.aggregate(avg=Avg("overall_score"), best=Max("overall_score"), worst=Min("overall_score"))
    metric, _ = ProgressMetric.objects.get_or_create(user=user, role=role, mode=mode)
    metric.sessions_completed = completed.count()
    metric.average_score = aggregates["avg"]
    metric.best_score = aggregates["best"]
    metric.worst_score = aggregates["worst"]
    metric.last_practiced = timezone.now()
    metric.save()
    return metric

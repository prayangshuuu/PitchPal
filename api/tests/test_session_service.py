import pytest
from unittest.mock import patch, MagicMock
from api.models import Session, Question, Answer, Evaluation, User, ProgressMetric
from api.services.session_service import (
    generate_questions_for_session,
    submit_answer,
    update_progress_metric,
    _complete_session
)
from django.utils import timezone

pytestmark = pytest.mark.django_db

@pytest.fixture
def user():
    return User.objects.create(email="test@example.com", username="testuser")

@pytest.fixture
def session(user):
    return Session.objects.create(
        user=user, 
        mode=Session.Mode.INTERVIEW, 
        role=Session.Role.SDE, 
        difficulty=Session.Difficulty.JUNIOR,
        status=Session.Status.IN_PROGRESS
    )

class TestGenerateQuestions:
    @patch("api.services.session_service.gemini_service.generate_interview_questions")
    def test_generate_questions_ai_only(self, mock_gen, session):
        mock_gen.return_value = [
            {"text": f"Generated {i}", "category": "technical"} for i in range(5)
        ]
        
        questions = generate_questions_for_session(session, count=3)
        assert len(questions) == 3
        assert questions[0].text == "Generated 0"
        mock_gen.assert_called_once_with(Session.Role.SDE, Session.Difficulty.JUNIOR, count=3)

    @patch("api.services.session_service.gemini_service.generate_interview_questions")
    def test_generate_questions_mixed(self, mock_gen, session):
        mock_gen.return_value = [{"text": "Generated 0", "category": "behavioral"}]
        
        questions = generate_questions_for_session(session, uploaded_questions=["Uploaded 1", "Uploaded 2"], count=3)
        
        assert len(questions) == 3
        texts = [q.text for q in questions]
        assert "Uploaded 1" in texts
        assert "Uploaded 2" in texts
        assert "Generated 0" in texts
        mock_gen.assert_called_once_with(Session.Role.SDE, Session.Difficulty.JUNIOR, count=1)


class TestSubmitAnswer:
    @patch("api.services.session_service.gemini_service.evaluate_answer")
    def test_submit_answer(self, mock_eval, session):
        q1 = Question.objects.create(session=session, question_number=1, text="Q1", category="behavioral")
        q2 = Question.objects.create(session=session, question_number=2, text="Q2", category="behavioral")
        
        mock_eval.return_value = {
            "score": 85,
            "clarity_score": 80,
            "depth_score": 90,
            "communication_score": 85,
            "feedback": "Good job",
            "strengths": ["Clear"],
            "improvements": ["Talk slower"],
            "raw_response": "{}"
        }
        
        answer, evaluation, is_last = submit_answer(session, q1, "My answer")
        
        assert answer.user_text == "My answer"
        assert evaluation.score == 85
        assert not is_last
        assert session.status == Session.Status.IN_PROGRESS
        
        mock_eval.assert_called_once_with("Q1", "My answer", mode=Session.Mode.INTERVIEW)

    @patch("api.services.session_service.gemini_service.evaluate_answer")
    def test_submit_last_answer_completes_session(self, mock_eval, session):
        q1 = Question.objects.create(session=session, question_number=1, text="Q1", category="behavioral")
        mock_eval.return_value = {"score": 90}
        
        answer, evaluation, is_last = submit_answer(session, q1, "My answer")
        
        assert is_last
        session.refresh_from_db()
        assert session.status == Session.Status.COMPLETED
        assert session.overall_score == 90


class TestCompleteSession:
    def test_update_progress_metric(self, user):
        s1 = Session.objects.create(
            user=user, role=Session.Role.SDE, mode=Session.Mode.INTERVIEW,
            status=Session.Status.COMPLETED, overall_score=80
        )
        s2 = Session.objects.create(
            user=user, role=Session.Role.SDE, mode=Session.Mode.INTERVIEW,
            status=Session.Status.COMPLETED, overall_score=100
        )
        
        metric = update_progress_metric(user, Session.Role.SDE, Session.Mode.INTERVIEW)
        
        assert metric.sessions_completed == 2
        assert metric.average_score == 90
        assert metric.best_score == 100
        assert metric.worst_score == 80

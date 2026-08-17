import json

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from api.models import Evaluation, ProgressMetric, Question, Session

User = get_user_model()

pytestmark = pytest.mark.unit


class TestUserModel:
    def test_create_user_with_required_fields(self, db):
        user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Sup3rSecret!",
        )
        assert user.pk is not None
        assert user.email == "alice@example.com"



    def test_email_unique_constraint(self, user):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username="dupe", email=user.email, password="AnotherPass1!")

    def test_str_returns_email(self, user):
        assert str(user) == user.email

    def test_timestamps_auto_set(self, user):
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_password_is_hashed_and_verifiable(self, db):
        user = User.objects.create_user(username="carol", email="carol@example.com", password="PlainText123!")
        assert user.password != "PlainText123!"
        assert user.check_password("PlainText123!")
        assert not user.check_password("wrong-password")


class TestSessionModel:
    def test_create_session_with_all_fields(self, user):
        s = Session.objects.create(
            user=user, mode="pitch", role="pm", difficulty="senior", overall_score=90, status="completed"
        )
        assert s.mode == "pitch"
        assert s.role == "pm"
        assert s.difficulty == "senior"
        assert s.overall_score == 90
        assert s.status == "completed"

    def test_foreign_key_to_user(self, session, user):
        assert session.user_id == user.id
        assert session in user.sessions.all()

    def test_status_choices_are_validated_via_full_clean(self, session):
        # CharField choices aren't enforced at the DB layer, only via full_clean()/forms.
        session.status = "bogus-status"
        with pytest.raises(ValidationError):
            session.full_clean()

    def test_overall_score_is_nullable(self, session):
        assert session.overall_score is None

    def test_timestamps_present(self, session):
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_ordering_by_created_at_desc(self, user):
        older = Session.objects.create(user=user, mode="interview", role="sde", difficulty="junior")
        newer = Session.objects.create(user=user, mode="pitch", role="pm", difficulty="mid")
        ids_in_order = list(Session.objects.filter(user=user).values_list("id", flat=True))
        assert ids_in_order == [newer.id, older.id]


class TestQuestionModel:
    def test_create_question_linked_to_session(self, session):
        q = Question.objects.create(
            session=session, question_number=1, text="Tell me about yourself.", category="behavioral"
        )
        assert q.session_id == session.id

    def test_question_number_accepts_1_through_5(self, session):
        # question_number has no DB-level bound; this documents the intended 1-5 range.
        for n in range(1, 6):
            q = Question(session=session, question_number=n, text=f"Q{n}", category="technical")
            q.full_clean()

    def test_text_field(self, question):
        assert question.text

    def test_category_choices_are_validated_via_full_clean(self, question):
        question.category = "not-a-real-category"
        with pytest.raises(ValidationError):
            question.full_clean()

    def test_related_name_questions(self, session, question):
        assert question in session.questions.all()

    def test_str_format(self, question):
        assert str(question) == f"Q{question.question_number}: {question.text[:50]}"


class TestAnswerModel:
    def test_create_answer_linked_to_question(self, question):
        from api.models import Answer

        a = Answer.objects.create(question=question, user_text="My answer text.")
        assert a.question_id == question.id

    def test_user_text_field(self, answer):
        assert answer.user_text

    def test_submitted_at_timestamp(self, answer):
        assert answer.submitted_at is not None

    def test_related_name_answers(self, question, answer):
        assert answer in question.answers.all()


class TestEvaluationModel:
    def test_create_evaluation_linked_to_answer(self, answer):
        e = Evaluation.objects.create(
            answer=answer, score=70, feedback="Good", strengths=json.dumps(["a"]), improvements=json.dumps(["b"])
        )
        assert e.answer_id == answer.id

    def test_one_to_one_relationship(self, evaluation, answer):
        answer.refresh_from_db()
        assert answer.evaluation == evaluation
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Evaluation.objects.create(answer=answer, score=10, feedback="dup", strengths="[]", improvements="[]")

    def test_score_in_range(self, evaluation):
        assert 0 <= evaluation.score <= 100

    def test_sub_scores_in_range(self, evaluation):
        assert 0 <= evaluation.clarity_score <= 100
        assert 0 <= evaluation.depth_score <= 100
        assert 0 <= evaluation.communication_score <= 100

    def test_feedback_is_text(self, evaluation):
        assert isinstance(evaluation.feedback, str) and evaluation.feedback

    def test_strengths_and_improvements_round_trip_as_json_text(self, evaluation):
        # strengths/improvements are stored as TextField; the app is responsible for
        # JSON-encoding/decoding on the way in and out.
        assert json.loads(evaluation.strengths) == ["Clear structure", "Concrete example"]
        assert json.loads(evaluation.improvements) == ["Quantify the impact"]

    def test_str_format(self, evaluation):
        assert str(evaluation) == f"Evaluation: {evaluation.score}/100"

    def test_example_refined_and_missing_skills_default(self, evaluation):
        assert evaluation.example_answer == ''
        assert evaluation.refined_answer == ''
        assert json.loads(evaluation.missing_skills) == []


class TestProgressMetricModel:
    def test_create_metric_linked_to_user(self, user):
        pm = ProgressMetric.objects.create(user=user, role="sde", mode="interview")
        assert pm.user_id == user.id

    def test_unique_together_user_role_mode(self, user):
        ProgressMetric.objects.create(user=user, role="sde", mode="interview")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProgressMetric.objects.create(user=user, role="sde", mode="interview")

    def test_same_role_different_mode_is_allowed(self, user):
        ProgressMetric.objects.create(user=user, role="sde", mode="interview")
        pm2 = ProgressMetric.objects.create(user=user, role="sde", mode="pitch")
        assert pm2.pk is not None

    def test_sessions_completed_counter(self, user):
        pm = ProgressMetric.objects.create(user=user, role="pm", mode="pitch")
        pm.sessions_completed += 1
        pm.save(update_fields=["sessions_completed"])
        pm.refresh_from_db()
        assert pm.sessions_completed == 1

    def test_average_score_calculation(self, user):
        pm = ProgressMetric.objects.create(user=user, role="qa", mode="interview")
        scores = [70, 90]
        pm.average_score = sum(scores) / len(scores)
        pm.save(update_fields=["average_score"])
        pm.refresh_from_db()
        assert pm.average_score == 80.0

    def test_best_and_worst_score(self, user):
        pm = ProgressMetric.objects.create(
            user=user, role="designer", mode="presentation", best_score=95, worst_score=40
        )
        assert pm.best_score == 95
        assert pm.worst_score == 40

    def test_last_practiced_timestamp(self, user):
        from django.utils import timezone

        pm = ProgressMetric.objects.create(
            user=user, role="other", mode="interview", last_practiced=timezone.now()
        )
        assert pm.last_practiced is not None

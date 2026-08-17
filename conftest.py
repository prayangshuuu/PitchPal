import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from api.models import Answer, Evaluation, Question, Session

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_django_cache():
    """Prevent cache_service tests from leaking state into each other via LocMemCache."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="jane_doe",
        email="jane@example.com",
        password="StrongPass123!",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="john_doe",
        email="john@example.com",
        password="StrongPass123!",
    )


@pytest.fixture
def session(user):
    return Session.objects.create(
        user=user,
        mode="interview",
        role="sde",
        difficulty="junior",
    )


@pytest.fixture
def question(session):
    return Question.objects.create(
        session=session,
        question_number=1,
        text="Tell me about a time you had to learn something quickly.",
        category="behavioral",
    )


@pytest.fixture
def answer(question):
    return Answer.objects.create(
        question=question,
        user_text="I once had to learn Kubernetes in a week for a production migration.",
    )


@pytest.fixture
def evaluation(answer):
    return Evaluation.objects.create(
        answer=answer,
        score=80,
        clarity_score=85,
        depth_score=75,
        communication_score=80,
        feedback="Solid answer with a clear structure and a concrete example.",
        strengths=json.dumps(["Clear structure", "Concrete example"]),
        improvements=json.dumps(["Quantify the impact"]),
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

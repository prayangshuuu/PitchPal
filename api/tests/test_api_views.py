import pytest
from django.urls import reverse
from rest_framework import status
from api.models import Session, Question, Answer, Evaluation, ProgressMetric

pytestmark = pytest.mark.django_db

def test_session_create(authenticated_client, user, monkeypatch):
    # Mock session_service to prevent external API calls
    def mock_generate(*args, **kwargs):
        pass
    monkeypatch.setattr('api.services.session_service.generate_questions_for_session', mock_generate)

    url = reverse('api-session-list')
    data = {
        'mode': 'interview',
        'role': 'sde',
        'difficulty': 'junior',
    }
    response = authenticated_client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert Session.objects.filter(user=user).count() == 1

def test_session_submit_answer(authenticated_client, session, question, monkeypatch):
    def mock_submit(*args, **kwargs):
        from api.models import Answer, Evaluation
        answer = Answer(question=question, user_text="mocked answer")
        answer.save()
        evaluation = Evaluation(
            answer=answer, score=100, clarity_score=100, depth_score=100,
            communication_score=100, feedback="mock", strengths="[]", improvements="[]"
        )
        evaluation.save()
        return answer, evaluation, True

    monkeypatch.setattr('api.services.session_service.submit_answer', mock_submit)

    url = reverse('api-session-submit-answer', kwargs={'pk': session.pk})
    data = {
        'question_id': question.id,
        'answer_text': 'This is my answer'
    }
    response = authenticated_client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert 'answer' in response.data

def test_unauthenticated_requests(api_client, session):
    url = reverse('api-session-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

import pytest
from django.core.management import call_command
from api.models import User, Session, Question, Answer, Evaluation, ProgressMetric

pytestmark = pytest.mark.django_db

def test_seed_demo_data_command():
    # Calling the command
    call_command('seed_demo_data')
    
    # Asserting data was created
    assert User.objects.filter(email='demo@example.com').exists()
    assert Session.objects.filter(user__email='demo@example.com').exists()
    assert Question.objects.exists()
    assert Answer.objects.exists()
    assert Evaluation.objects.exists()
    assert ProgressMetric.objects.exists()

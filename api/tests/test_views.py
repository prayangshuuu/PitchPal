import pytest
from django.urls import reverse
from api.models import User, Session

pytestmark = pytest.mark.django_db

def test_login_view_get(client):
    url = reverse('login')
    response = client.get(url)
    assert response.status_code == 200
    assert 'api/login.html' in [t.name for t in response.templates]

def test_login_view_post(client, user):
    url = reverse('login')
    response = client.post(url, data={'email': user.email, 'password': 'StrongPass123!'})
    assert response.status_code == 302
    assert response.url == reverse('home')

def test_signup_view_post(client):
    url = reverse('signup')
    response = client.post(url, data={'email': 'newuser@example.com', 'password': 'Password123!', 'confirm_password': 'Password123!'})
    assert response.status_code == 302
    assert response.url == reverse('home')
    assert User.objects.filter(email='newuser@example.com').exists()

def test_logout_view(client, user):
    client.force_login(user)
    url = reverse('logout')
    response = client.post(url)
    assert response.status_code == 302
    assert response.url == reverse('home')

@pytest.fixture(autouse=True)
def mock_static_storage(settings):
    settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

def test_home_view(client):
    url = reverse('home')
    response = client.get(url)
    assert response.status_code == 200
    assert 'api/landing.html' in [t.name for t in response.templates]

def test_session_practice_view(client, user, session, question):
    client.force_login(user)
    url = reverse('session_practice', kwargs={'session_id': session.id})
    response = client.get(url)
    assert response.status_code == 200
    assert 'api/session_practice.html' in [t.name for t in response.templates]

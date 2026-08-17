from django.urls import path
from .views import (
    HomeView, SessionStartView, SessionPracticeView, AnswerSubmitView,
    SessionResultsView, ProgressDashboardView, LoginView, SignupView, LogoutView,
    ExtractQuestionsView
)
from . import views

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', ProgressDashboardView.as_view(), name='dashboard'),
    path('sessions/start/', SessionStartView.as_view(), name='session_start'),
    path('sessions/extract-questions/', ExtractQuestionsView.as_view(), name='extract_questions'),
    path('sessions/<uuid:session_id>/practice/', SessionPracticeView.as_view(), name='session_practice'),
    path('sessions/<uuid:session_id>/submit/', AnswerSubmitView.as_view(), name='answer_submit'),
    path('sessions/<uuid:session_id>/transcribe-voice/', views.transcribe_voice_view, name='transcribe-voice'),
    path('sessions/<uuid:session_id>/results/', SessionResultsView.as_view(), name='session_results'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
]

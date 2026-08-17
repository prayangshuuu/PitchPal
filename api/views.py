from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import SessionForm, LoginForm, SignupForm

class HomeView(View):
    def get(self, request):
        context = {}
        if request.user.is_authenticated:
            # Mock Data
            context['recent_sessions'] = [{'created_at': '2023-10-01', 'mode': 'interview', 'role': 'sde', 'score': 85}]
            context['avg_score'] = 82
            context['top_role'] = 'Software Engineer'
        return render(request, 'api/home.html', context)

class SessionStartView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'api/session_start.html', {'form': SessionForm()})
        
    def post(self, request):
        form = SessionForm(request.POST)
        if form.is_valid():
            # session = Session.objects.create(...)
            # return redirect('session_practice', session_id=session.id)
            return redirect('session_practice', session_id=1)
        return render(request, 'api/session_start.html', {'form': form})

class SessionPracticeView(LoginRequiredMixin, View):
    def get(self, request, session_id):
        context = {
            'session': {'id': session_id, 'get_mode_display': 'Interview', 'get_role_display': 'Software Engineer'},
            'question_number': 1, 'progress_percentage': 20,
            'current_question': {'id': 1, 'text': 'Tell me about a difficult challenge you solved.'}
        }
        return render(request, 'api/session_practice.html', context)

class AnswerSubmitView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        import time
        time.sleep(1) # Simulating API latency
        context = {
            'session': {'id': session_id},
            'feedback': {
                'overall_score': 85, 'clarity_score': 90, 'depth_score': 80, 'communication_score': 85,
                'text_feedback': 'Strong answer with clear structure.',
                'strengths': ['Clear STAR method', 'Good technical depth'],
                'improvements': ['Could discuss impact more']
            },
            'is_last_question': False, 'next_question': 2
        }
        return render(request, 'api/partials/feedback.html', context)

class SessionResultsView(LoginRequiredMixin, View):
    def get(self, request, session_id):
        context = {
            'session': {'get_role_display': 'Software Engineer', 'get_mode_display': 'Interview', 'difficulty': 'mid', 'average_score': 82, 'created_at': '2023-10-01'},
            'top_strengths': ['Communication'], 'top_improvements': ['Depth'],
            'answers': [{'overall_score': 85, 'clarity_score': 90, 'depth_score': 80, 'communication_score': 85, 'feedback_text': 'Good answer.', 'category': 'Technical'}, {'overall_score': 65, 'clarity_score': 70, 'depth_score': 60, 'communication_score': 65, 'feedback_text': 'Needed more depth.', 'category': 'Behavioral'}]
        }
        return render(request, 'api/session_results.html', context)

class ProgressDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            'total_sessions': 12, 'avg_score': 78.5, 'best_score': 92, 'favorite_role': 'Product Manager',
            'role_stats': [{'role': 'pm', 'count': 8, 'avg_score': 80.2}],
            'recent_sessions': [{'created_at': '2023-10-01', 'get_role_display': 'Software Engineer', 'get_mode_display': 'Interview', 'get_difficulty_display': 'Mid', 'average_score': 85, 'id': 1}]
        }
        return render(request, 'api/progress_dashboard.html', context)

class LoginView(View):
    def get(self, request): return render(request, 'api/login.html', {'form': LoginForm()})
    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password'])
            if user: 
                login(request, user)
                return redirect('home')
            form.add_error(None, "Invalid credentials.")
        return render(request, 'api/login.html', {'form': form})

class SignupView(View):
    def get(self, request): return render(request, 'api/signup.html', {'form': SignupForm()})
    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid(): return redirect('home')
        return render(request, 'api/signup.html', {'form': form})

class LogoutView(View):
    def post(self, request): 
        logout(request)
        return redirect('home')

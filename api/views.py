import json
import os
import uuid

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db.models import Avg, Count, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .forms import LoginForm, SessionForm, SignupForm
from .models import Question, Session
from .services import session_service
from .services.ocr_service import extract_text_from_image, extract_text_from_pdf, parse_questions_from_text

User = get_user_model()


class HomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return render(request, 'api/landing.html', {'is_landing_page': True})

        recent_sessions = (
            Session.objects.filter(user=request.user, status=Session.Status.COMPLETED).order_by('-created_at')[:5]
        )
        completed = Session.objects.filter(
            user=request.user, status=Session.Status.COMPLETED, overall_score__isnull=False
        )
        avg = completed.aggregate(avg=Avg('overall_score'))['avg']
        top_role_row = completed.values('role').annotate(count=Count('id')).order_by('-count').first()
        context = {
            'recent_sessions': recent_sessions,
            'avg_score': round(avg) if avg is not None else None,
            'top_role': top_role_row['role'] if top_role_row else None,
        }
        return render(request, 'api/home.html', context)


def _extract_questions_from_upload(uploaded_file):
    fs = FileSystemStorage()
    filename = fs.save(uploaded_file.name, uploaded_file)
    file_path = fs.path(filename)
    try:
        if filename.lower().endswith('.pdf'):
            raw_text = extract_text_from_pdf(file_path)
        else:
            raw_text = extract_text_from_image(file_path)
        return parse_questions_from_text(raw_text) if raw_text else []
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


class SessionStartView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'api/session_start.html', {'form': SessionForm()})

    def post(self, request):
        form = SessionForm(request.POST)
        if not form.is_valid():
            return render(request, 'api/session_start.html', {'form': form})

        uploaded_file = request.FILES.get('questions_file')
        edited_questions_raw = request.POST.get('edited_questions')

        uploaded_questions = []
        if edited_questions_raw:
            try:
                uploaded_questions = json.loads(edited_questions_raw)
            except (TypeError, ValueError):
                uploaded_questions = []
        elif uploaded_file:
            # Fallback: extract synchronously if the JS-driven OCR preview wasn't used.
            uploaded_questions = _extract_questions_from_upload(uploaded_file)

        session = form.save(commit=False)
        session.user = request.user
        session.questions_source = 'user_uploaded' if uploaded_questions else 'ai_generated'
        if uploaded_questions:
            session.user_uploaded_questions = json.dumps(uploaded_questions)
        session.save()

        session_service.generate_questions_for_session(session, uploaded_questions=uploaded_questions)
        return redirect('session_practice', session_id=session.id)


@method_decorator(csrf_exempt, name='dispatch')
class ExtractQuestionsView(View):
    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({"error": "File upload failed", "detail": "No file provided"}, status=400)

        max_size = getattr(settings, 'OCR_MAX_FILE_SIZE', 10485760)
        if uploaded_file.size > int(max_size):
            return JsonResponse({"error": "File must be under 10MB"}, status=400)

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.pdf']:
            return JsonResponse({"error": "Please upload JPG, PNG, or PDF only"}, status=400)

        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)

        try:
            if ext == '.pdf':
                raw_text = extract_text_from_pdf(file_path)
            else:
                raw_text = extract_text_from_image(file_path)

            if not raw_text:
                return JsonResponse({
                    "error": "Couldn't extract text from image. Try a clearer image or upload PDF"
                }, status=400)

            questions = parse_questions_from_text(raw_text)
            if not questions:
                return JsonResponse({
                    "error": "No questions found in image. Please upload a file with clearly written questions"
                }, status=400)

            return JsonResponse({"extracted_questions": questions, "raw_text": raw_text})
        except Exception as e:
            return JsonResponse({"error": "File upload failed", "detail": str(e)}, status=500)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


class SessionPracticeView(LoginRequiredMixin, View):
    def get(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, user=request.user)
        total_questions = session.questions.count() or 1
        try:
            question_number = int(request.GET.get('q', 1))
        except (TypeError, ValueError):
            question_number = 1
        question_number = max(1, min(question_number, total_questions))

        current_question = get_object_or_404(Question, session=session, question_number=question_number)
        progress_percentage = int((question_number / total_questions) * 100)

        return render(request, 'api/session_practice.html', {
            'session': session,
            'current_question': current_question,
            'question_number': question_number,
            'total_questions': total_questions,
            'progress_percentage': progress_percentage,
        })


class AnswerSubmitView(LoginRequiredMixin, View):
    def post(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, user=request.user)
        question = get_object_or_404(Question, id=request.POST.get('question_id'), session=session)
        answer_text = request.POST.get('answer_text', '').strip()
        answer_type = request.POST.get('answer_type', 'text')

        answer, evaluation, is_last_question = session_service.submit_answer(
            session=session, 
            question=question, 
            answer_text=answer_text,
            answer_type=answer_type,
            transcribed_text=answer_text if answer_type == 'voice' else None,
            is_transcribed=answer_type == 'voice'
        )

        return JsonResponse({
            'overall_score': evaluation.score,
            'clarity_score': evaluation.clarity_score,
            'depth_score': evaluation.depth_score,
            'communication_score': evaluation.communication_score,
            'text_feedback': evaluation.feedback,
            'strengths': json.loads(evaluation.strengths),
            'improvements': json.loads(evaluation.improvements),
            'example_answer': evaluation.example_answer,
            'refined_answer': evaluation.refined_answer,
            'missing_skills': json.loads(evaluation.missing_skills or '[]'),
            'is_last_question': is_last_question,
            'next_question': question.question_number + 1,
            'session_id': str(session.id),
        })


class SessionResultsView(LoginRequiredMixin, View):
    def get(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, user=request.user)
        answers = []
        for question in session.questions.order_by('question_number'):
            answer = question.answers.first()
            evaluation = getattr(answer, 'evaluation', None) if answer else None
            answers.append({
                'overall_score': evaluation.score if evaluation else None,
                'clarity_score': evaluation.clarity_score if evaluation else None,
                'depth_score': evaluation.depth_score if evaluation else None,
                'communication_score': evaluation.communication_score if evaluation else None,
                'feedback_text': evaluation.feedback if evaluation else '',
            })
        return render(request, 'api/session_results.html', {'session': session, 'answers': answers})


class ProgressDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        completed = Session.objects.filter(
            user=request.user, status=Session.Status.COMPLETED, overall_score__isnull=False
        )
        aggregates = completed.aggregate(avg=Avg('overall_score'), best=Max('overall_score'))
        role_stats = list(
            completed.values('role').annotate(count=Count('id'), avg_score=Avg('overall_score')).order_by('-count')
        )
        recent_sessions = Session.objects.filter(user=request.user).order_by('-created_at')[:10]

        return render(request, 'api/progress_dashboard.html', {
            'total_sessions': completed.count(),
            'avg_score': aggregates['avg'],
            'best_score': aggregates['best'],
            'favorite_role': role_stats[0]['role'] if role_stats else None,
            'role_stats': role_stats,
            'recent_sessions': recent_sessions,
        })


class LoginView(View):
    def get(self, request):
        return render(request, 'api/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request, username=form.cleaned_data['email'], password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                return redirect('home')
            form.add_error(None, "Invalid email or password.")
        return render(request, 'api/login.html', {'form': form})


class SignupView(View):
    def get(self, request):
        return render(request, 'api/signup.html', {'form': SignupForm()})

    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.create_user(
                username=f"{email.split('@')[0]}-{uuid.uuid4().hex[:6]}",
                email=email,
                password=form.cleaned_data['password'],
            )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        return render(request, 'api/signup.html', {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('home')


def handler404(request, exception=None):
    return render(request, 'api/error.html', {'error_code': 404, 'error_message': "Page not found."}, status=404)


def handler500(request):
    return render(request, 'api/error.html', {
        'error_code': 500,
        'error_message': "Something went wrong on our end. Please try again later.",
    }, status=500)

@csrf_exempt
def transcribe_voice_view(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    if 'audio_file' not in request.FILES:
        return JsonResponse({'error': 'No audio file provided'}, status=400)
    
    audio_file = request.FILES['audio_file']
    
    from api.services.speech_service import transcribe_audio_with_confidence, validate_audio_file
    import tempfile
    
    # Validate
    validation = validate_audio_file(audio_file)
    if not validation['valid']:
        return JsonResponse({'error': validation['error']}, status=400)
    
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
        for chunk in audio_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    # Transcribe
    result = transcribe_audio_with_confidence(tmp_path)
    
    # Clean up
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    
    if not result.get('text'):
        return JsonResponse({'error': 'Could not transcribe audio. Please try again.'}, status=400)
    
    return JsonResponse({
        'transcribed_text': result['text'],
        'confidence': result['confidence'],
        'status': 'success'
    }, status=200)

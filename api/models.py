import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # Required by AbstractUser

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.email

class Session(models.Model):
    class Mode(models.TextChoices):
        INTERVIEW = 'interview', 'Interview'
        PITCH = 'pitch', 'Pitch'
        PRESENTATION = 'presentation', 'Presentation'

    class Role(models.TextChoices):
        SDE = 'sde', 'Software Development Engineer'
        PM = 'pm', 'Product Manager'
        DESIGNER = 'designer', 'Designer'
        QA = 'qa', 'Quality Assurance'
        OTHER = 'other', 'Other'

    class Difficulty(models.TextChoices):
        JUNIOR = 'junior', 'Junior'
        MID = 'mid', 'Mid-Level'
        SENIOR = 'senior', 'Senior'

    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    class Source(models.TextChoices):
        AI_GENERATED = 'ai_generated', 'AI Generated'
        USER_UPLOADED = 'user_uploaded', 'User Uploaded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    mode = models.CharField(max_length=20, choices=Mode.choices)
    role = models.CharField(max_length=20, choices=Role.choices)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices)
    overall_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    user_uploaded_questions = models.TextField(null=True, blank=True)
    questions_source = models.CharField(max_length=20, choices=Source.choices, default=Source.AI_GENERATED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.get_mode_display()} ({self.created_at.date() if self.created_at else ''})"

    @property
    def average_score(self) -> int:
        """Template-facing alias for the stored overall_score."""
        return self.overall_score

    @property
    def score(self) -> int:
        """Template-facing alias for the stored overall_score."""
        return self.overall_score

class Question(models.Model):
    class Category(models.TextChoices):
        BEHAVIORAL = 'behavioral', 'Behavioral'
        TECHNICAL = 'technical', 'Technical'
        PROBLEM_SOLVING = 'problem_solving', 'Problem Solving'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()
    text = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question_number']
        indexes = [
            models.Index(fields=['session']),
        ]

    def __str__(self) -> str:
        return f"Q{self.question_number}: {self.text[:50]}"

class Answer(models.Model):
    class AnswerType(models.TextChoices):
        TEXT = 'text', 'Text'
        VOICE = 'voice', 'Voice Recording'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_type = models.CharField(max_length=10, choices=AnswerType.choices, default=AnswerType.TEXT)
    user_text = models.TextField()  # Final text (typed or transcribed)
    audio_file = models.FileField(upload_to='voice_answers/', null=True, blank=True)
    transcribed_text = models.TextField(null=True, blank=True)
    transcription_confidence = models.FloatField(null=True, blank=True, default=0)
    is_transcribed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['submitted_at']
        indexes = [
            models.Index(fields=['question']),
        ]

    def __str__(self) -> str:
        return f"Answer to Q{self.question.question_number}"

class Evaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.OneToOneField(Answer, on_delete=models.CASCADE, related_name='evaluation')
    score = models.IntegerField()
    clarity_score = models.IntegerField(null=True, blank=True)
    depth_score = models.IntegerField(null=True, blank=True)
    communication_score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField()
    strengths = models.TextField()
    improvements = models.TextField()
    raw_response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['answer']),
        ]

    def __str__(self) -> str:
        return f"Evaluation: {self.score}/100"

class ProgressMetric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_metrics')
    role = models.CharField(max_length=20, choices=Session.Role.choices)
    mode = models.CharField(max_length=20, choices=Session.Mode.choices)
    sessions_completed = models.IntegerField(default=0)
    average_score = models.FloatField(null=True, blank=True)
    best_score = models.IntegerField(null=True, blank=True)
    worst_score = models.IntegerField(null=True, blank=True)
    last_practiced = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('user', 'role', 'mode'),)
        ordering = ['-last_practiced']
        indexes = [
            models.Index(fields=['user', 'role']),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.get_role_display()} ({self.get_mode_display()})"

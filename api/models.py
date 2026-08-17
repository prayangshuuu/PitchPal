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

    def __str__(self):
        return self.email

class Session(models.Model):
    MODE_CHOICES = (
        ('interview', 'Interview'),
        ('pitch', 'Pitch'),
        ('presentation', 'Presentation'),
    )
    ROLE_CHOICES = (
        ('sde', 'Software Development Engineer'),
        ('pm', 'Product Manager'),
        ('designer', 'Designer'),
        ('qa', 'Quality Assurance'),
        ('other', 'Other'),
    )
    DIFFICULTY_CHOICES = (
        ('junior', 'Junior'),
        ('mid', 'Mid-Level'),
        ('senior', 'Senior'),
    )
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )

    SOURCE_CHOICES = (
        ('ai_generated', 'AI Generated'),
        ('user_uploaded', 'User Uploaded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    overall_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    user_uploaded_questions = models.TextField(null=True, blank=True)
    questions_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='ai_generated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_mode_display()} ({self.created_at.date() if self.created_at else ''})"

    @property
    def average_score(self):
        """Template-facing alias for the stored overall_score."""
        return self.overall_score

    @property
    def score(self):
        """Template-facing alias for the stored overall_score."""
        return self.overall_score

class Question(models.Model):
    CATEGORY_CHOICES = (
        ('behavioral', 'Behavioral'),
        ('technical', 'Technical'),
        ('problem_solving', 'Problem Solving'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()
    text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question_number']
        indexes = [
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"Q{self.question_number}: {self.text[:50]}"

class Answer(models.Model):
    ANSWER_TYPE_CHOICES = [
        ('text', 'Text'),
        ('voice', 'Voice Recording'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_type = models.CharField(max_length=10, choices=ANSWER_TYPE_CHOICES, default='text')
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

    def __str__(self):
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

    def __str__(self):
        return f"Evaluation: {self.score}/100"

class ProgressMetric(models.Model):
    ROLE_CHOICES = (
        ('sde', 'Software Development Engineer'),
        ('pm', 'Product Manager'),
        ('designer', 'Designer'),
        ('qa', 'Quality Assurance'),
        ('other', 'Other'),
    )
    MODE_CHOICES = (
        ('interview', 'Interview'),
        ('pitch', 'Pitch'),
        ('presentation', 'Presentation'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_metrics')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
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

    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()} ({self.get_mode_display()})"

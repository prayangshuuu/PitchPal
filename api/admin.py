from django.contrib import admin
from .models import User, Session, Question, Answer, Evaluation, ProgressMetric

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'subscription_tier', 'created_at', 'updated_at')
    search_fields = ('email', 'username')
    list_filter = ('subscription_tier',)
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mode', 'role', 'difficulty', 'status', 'overall_score', 'created_at')
    search_fields = ('user__email', 'mode', 'role')
    list_filter = ('mode', 'role', 'difficulty', 'status')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('session', 'question_number', 'category', 'created_at')
    search_fields = ('text', 'session__user__email')
    list_filter = ('category',)
    readonly_fields = ('id', 'created_at')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'submitted_at')
    search_fields = ('user_text', 'question__text')
    list_filter = ('submitted_at',)
    readonly_fields = ('id', 'submitted_at')

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('answer', 'score', 'clarity_score', 'depth_score', 'communication_score', 'created_at')
    search_fields = ('feedback', 'strengths', 'improvements')
    list_filter = ('score', 'created_at')
    readonly_fields = ('id', 'created_at')

@admin.register(ProgressMetric)
class ProgressMetricAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'mode', 'sessions_completed', 'average_score', 'last_practiced')
    search_fields = ('user__email', 'role', 'mode')
    list_filter = ('role', 'mode')
    readonly_fields = ('id', 'updated_at')

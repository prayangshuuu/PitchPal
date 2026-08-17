from rest_framework.routers import DefaultRouter

from .api_views import (
    AnswerViewSet,
    EvaluationViewSet,
    ProgressMetricViewSet,
    QuestionViewSet,
    SessionViewSet,
)

router = DefaultRouter()
router.register('sessions', SessionViewSet, basename='api-session')
router.register('questions', QuestionViewSet, basename='api-question')
router.register('answers', AnswerViewSet, basename='api-answer')
router.register('evaluations', EvaluationViewSet, basename='api-evaluation')
router.register('progress-metrics', ProgressMetricViewSet, basename='api-progressmetric')

urlpatterns = router.urls

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Answer, Evaluation, ProgressMetric, Question, Session
from .serializers import (
    AnswerSerializer,
    AnswerSubmitSerializer,
    EvaluationSerializer,
    ProgressMetricSerializer,
    QuestionSerializer,
    SessionSerializer,
)
from .services import session_service


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return Session.objects.filter(user=self.request.user).prefetch_related('questions')

    def perform_create(self, serializer):
        session = serializer.save(user=self.request.user)
        session_service.generate_questions_for_session(session)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        session = self.get_object()
        serializer = AnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = get_object_or_404(
            Question, id=serializer.validated_data['question_id'], session=session
        )
        answer, evaluation, is_last_question = session_service.submit_answer(
            session, question, serializer.validated_data['answer_text']
        )

        return Response(
            {
                'answer': AnswerSerializer(answer).data,
                'is_last_question': is_last_question,
                'session': SessionSerializer(session).data,
            },
            status=status.HTTP_201_CREATED,
        )


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Question.objects.filter(session__user=self.request.user)


class AnswerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnswerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Answer.objects.filter(question__session__user=self.request.user)


class EvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EvaluationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Evaluation.objects.filter(answer__question__session__user=self.request.user)


class ProgressMetricViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProgressMetricSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProgressMetric.objects.filter(user=self.request.user)

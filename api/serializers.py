import json

from rest_framework import serializers

from .models import Answer, Evaluation, ProgressMetric, Question, Session


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_number', 'text', 'category', 'created_at']
        read_only_fields = fields


class SessionSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)

    class Meta:
        model = Session
        fields = [
            'id', 'user_id', 'role', 'difficulty', 'mode', 'status',
            'overall_score', 'created_at', 'updated_at', 'questions',
        ]
        read_only_fields = ['id', 'user_id', 'status', 'overall_score', 'created_at', 'updated_at', 'questions']


class EvaluationSerializer(serializers.ModelSerializer):
    strengths = serializers.SerializerMethodField()
    improvements = serializers.SerializerMethodField()
    missing_skills = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = [
            'id', 'answer', 'score', 'clarity_score', 'depth_score',
            'communication_score', 'feedback', 'strengths', 'improvements',
            'example_answer', 'refined_answer', 'missing_skills', 'created_at',
        ]
        read_only_fields = fields

    def get_strengths(self, obj):
        return self._safe_json(obj.strengths)

    def get_improvements(self, obj):
        return self._safe_json(obj.improvements)

    def get_missing_skills(self, obj):
        return self._safe_json(obj.missing_skills)

    @staticmethod
    def _safe_json(value):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return []


class AnswerSerializer(serializers.ModelSerializer):
    evaluation = EvaluationSerializer(read_only=True)

    class Meta:
        model = Answer
        fields = ['id', 'question', 'user_text', 'submitted_at', 'evaluation']
        read_only_fields = ['id', 'submitted_at', 'evaluation']


class AnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    answer_text = serializers.CharField()


class ProgressMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressMetric
        fields = [
            'id', 'role', 'mode', 'sessions_completed', 'average_score',
            'best_score', 'worst_score', 'last_practiced', 'updated_at',
        ]
        read_only_fields = fields

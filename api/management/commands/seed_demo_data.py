import json
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Answer, Evaluation, ProgressMetric, Question, Session
from api.services import gemini_service
from api.services.session_service import update_progress_metric

User = get_user_model()

DEMO_PASSWORD = "StrongPass123!"

# (role, difficulty, mode) — matches the choices already wired in api/models.py
SESSION_PLAN = [
    ("sde", "junior", "interview"),
    ("sde", "senior", "interview"),
    ("pm", "mid", "pitch"),
    ("designer", "junior", "interview"),
    ("designer", "senior", "presentation"),
]

SAMPLE_ANSWERS = [
    "I approached this by first breaking the problem into smaller pieces, then validating my "
    "assumptions with the team before committing to a direction.",
    "In my last role I ran into a similar situation and resolved it by communicating early with "
    "stakeholders and adjusting scope rather than the deadline.",
    "I'd start by gathering data on the current state, identify the biggest bottleneck, and "
    "propose a small experiment before rolling out a full solution.",
    "My instinct is to prioritize the user-facing impact first, then work backward to the "
    "technical or process changes needed to support it.",
    "I try to stay calm under pressure by focusing on what's controllable, documenting decisions, "
    "and looping in the right people as soon as a risk becomes visible.",
]

FEEDBACK_POOL = [
    (
        "Clear, structured answer with a concrete example.",
        ["Clear structure", "Concrete example"],
        ["Quantify the impact with metrics"],
    ),
    (
        "Good instincts, but the answer could go one level deeper on trade-offs.",
        ["Good instincts", "Confident delivery"],
        ["Discuss trade-offs explicitly"],
    ),
    (
        "Strong communication and pacing throughout the answer.",
        ["Strong communication", "Good pacing"],
        ["Tie the answer back to the original question"],
    ),
    (
        "Solid technical grounding with room to be more concise.",
        ["Solid fundamentals"],
        ["Be more concise", "Lead with the conclusion"],
    ),
]


class Command(BaseCommand):
    help = "Seed a demo user and an admin user with sample completed practice sessions."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data before reseeding.")

    def handle(self, *args, **options):
        demo_user = self._get_or_create_user("demo_user", "demo@example.com", "free")
        admin_user = self._get_or_create_user(
            "admin_user", "admin@example.com", "pro", is_staff=True, is_superuser=True
        )

        if options["reset"]:
            Session.objects.filter(user__in=[demo_user, admin_user]).delete()
            ProgressMetric.objects.filter(user__in=[demo_user, admin_user]).delete()

        for user in (demo_user, admin_user):
            if Session.objects.filter(user=user).exists():
                self.stdout.write(f"Skipping {user.email}: already has sessions (use --reset to reseed).")
                continue
            self._seed_sessions_for_user(user)

        self.stdout.write(self.style.SUCCESS("Demo data ready:"))
        self.stdout.write(f"  demo@example.com  / {DEMO_PASSWORD}")
        self.stdout.write(f"  admin@example.com / {DEMO_PASSWORD}")

    def _get_or_create_user(self, username, email, tier, **extra):
        user, created = User.objects.get_or_create(
            email=email, defaults={"username": username, "subscription_tier": tier, **extra}
        )
        # Always pin the demo password so the login page's demo-login buttons keep working,
        # even if this user already existed from an earlier version of this command.
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    @transaction.atomic
    def _seed_sessions_for_user(self, user):
        rng = random.Random(f"pitchpal-demo-{user.email}")
        for role, difficulty, mode in SESSION_PLAN:
            session = Session.objects.create(
                user=user, role=role, difficulty=difficulty, mode=mode, status="completed"
            )
            questions = gemini_service._get_fallback_questions(role, difficulty, 5)
            scores = []
            for index, question_data in enumerate(questions, start=1):
                question = Question.objects.create(
                    session=session,
                    question_number=index,
                    text=question_data["text"],
                    category=str(question_data["category"])[:20],
                )
                answer = Answer.objects.create(
                    question=question, user_text=rng.choice(SAMPLE_ANSWERS)
                )
                score = rng.randint(62, 96)
                spread = rng.randint(-8, 8)
                feedback_text, strengths, improvements = rng.choice(FEEDBACK_POOL)
                Evaluation.objects.create(
                    answer=answer,
                    score=score,
                    clarity_score=max(0, min(100, score + spread)),
                    depth_score=max(0, min(100, score - spread)),
                    communication_score=max(0, min(100, score + rng.randint(-5, 5))),
                    feedback=feedback_text,
                    strengths=json.dumps(strengths),
                    improvements=json.dumps(improvements),
                )
                scores.append(score)

            session.overall_score = round(sum(scores) / len(scores))
            session.save(update_fields=["overall_score"])
            update_progress_metric(user, role, mode)

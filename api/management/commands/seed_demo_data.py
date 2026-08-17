from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Session, Question, Answer, Evaluation, ProgressMetric

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with demo data.'

    def handle(self, *args, **options):
        # Create or update demo user
        user, created = User.objects.get_or_create(
            email='demo@example.com',
            defaults={
                'username': 'demo_user',
                'first_name': 'Demo',
                'last_name': 'User',
                'subscription_tier': 'pro'
            }
        )
        # Always set the password so it doesn't get messed up
        user.set_password('demo123')
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created demo user (demo@example.com / demo123)'))
        else:
            self.stdout.write(self.style.SUCCESS('Demo user already exists, updated password to demo123'))

        # Seed some progress metrics if they don't exist
        metric, m_created = ProgressMetric.objects.get_or_create(
            user=user,
            role='sde',
            mode='interview',
            defaults={
                'sessions_completed': 5,
                'average_score': 85.5,
                'best_score': 95,
                'worst_score': 75
            }
        )
        if m_created:
            self.stdout.write(self.style.SUCCESS('Seeded progress metrics for demo user'))

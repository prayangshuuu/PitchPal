from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Session, Question, Answer, Evaluation, ProgressMetric

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with demo data.'

    def handle(self, *args, **options):
        # Create or update regular user
        user, created = User.objects.get_or_create(
            email='user@pitchpal.com',
            defaults={
                'username': 'user',
                'first_name': 'Regular',
                'last_name': 'User',
                'subscription_tier': 'pro',
                'is_staff': False,
                'is_superuser': False
            }
        )
        user.set_password('pitchpal')
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created user (user@pitchpal.com / pitchpal)'))
        else:
            self.stdout.write(self.style.SUCCESS('User already exists, updated password'))

        # Create or update admin user
        admin, admin_created = User.objects.get_or_create(
            email='admin@pitchpal.com',
            defaults={
                'username': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'subscription_tier': 'pro',
                'is_staff': True,
                'is_superuser': True
            }
        )
        admin.set_password('pitchpal')
        admin.save()

        if admin_created:
            self.stdout.write(self.style.SUCCESS('Successfully created admin (admin@pitchpal.com / pitchpal)'))
        else:
            self.stdout.write(self.style.SUCCESS('Admin already exists, updated password'))

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

import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Safely bootstrap or promote an initial administrator account for ForenX."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="Username for the admin user (can also be read from ADMIN_USERNAME env var)",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Email address for the admin user (can also be read from ADMIN_EMAIL env var)",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Password for the admin user (can also be read from ADMIN_PASSWORD env var)",
        )
        parser.add_argument(
            "--promote",
            type=str,
            help="Email or username of an existing account to promote to ADMIN",
        )

    def handle(self, *args, **options):
        promote_target = options.get("promote")

        if promote_target:
            target = promote_target.strip()
            user = (
                User.objects.filter(email__iexact=target).first()
                or User.objects.filter(username=target).first()
            )
            if not user:
                raise CommandError(f"User '{target}' does not exist.")

            user.role = "ADMIN"
            user.is_staff = True
            user.is_active = True
            user.is_email_verified = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully promoted existing user '{user.username}' ({user.email}) to ADMIN."
                )
            )
            return

        username = options.get("username") or os.environ.get("ADMIN_USERNAME")
        email = options.get("email") or os.environ.get("ADMIN_EMAIL")
        password = options.get("password") or os.environ.get("ADMIN_PASSWORD")

        if not username or not email or not password:
            raise CommandError(
                "Please provide --username, --email, and --password (or set ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD environment variables), or use --promote <user>."
            )

        username = username.strip()
        email = email.strip().lower()

        user = User.objects.filter(username=username).first() or User.objects.filter(email__iexact=email).first()

        if user:
            user.username = username
            user.email = email
            user.set_password(password)
            user.role = "ADMIN"
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.is_email_verified = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated existing user '{user.username}' to ADMIN with new credentials."
                )
            )
        else:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role="ADMIN",
                is_email_verified=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created initial ADMIN user: '{user.username}' ({user.email})."
                )
            )

from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "إرجاع أرقام الهواتف للصيغة القديمة (بدون +)"

    def handle(self, *args, **options):
        users = User.objects.filter(phone_number__startswith="+")
        updated = 0

        for user in users:
            phone = user.phone_number
            # شيل الـ +
            new_phone = phone[1:]

            if User.objects.filter(phone_number=new_phone).exclude(id=user.id).exists():
                self.stdout.write(
                    self.style.WARNING(f"SKIP {phone} → {new_phone} (duplicate)")
                )
                continue

            user.phone_number = new_phone
            user.save(update_fields=["phone_number"])
            updated += 1
            self.stdout.write(f"  {phone} → {new_phone}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Reverted {updated} phone numbers."))

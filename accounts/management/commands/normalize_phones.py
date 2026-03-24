from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "تحديث أرقام الهواتف القديمة لصيغة +[كود الدولة][الرقم]"

    def handle(self, *args, **options):
        users = User.objects.all()
        updated = 0

        for user in users:
            phone = user.phone_number
            new_phone = phone

            if phone.startswith("+"):
                continue  # already normalized

            digits = "".join(filter(str.isdigit, phone))

            if digits.startswith("00"):
                new_phone = "+" + digits[2:]
            elif digits.startswith("09") and len(digits) == 10:
                new_phone = "+963" + digits[1:]
            elif digits.startswith("0") and len(digits) > 10:
                new_phone = "+" + digits[1:]
            else:
                new_phone = "+" + digits

            if new_phone != phone:
                # check for duplicates
                if User.objects.filter(phone_number=new_phone).exclude(id=user.id).exists():
                    self.stdout.write(
                        self.style.WARNING(f"SKIP {phone} → {new_phone} (duplicate)")
                    )
                    continue

                user.phone_number = new_phone
                user.save(update_fields=["phone_number"])
                updated += 1
                self.stdout.write(f"  {phone} → {new_phone}")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Updated {updated} phone numbers."))

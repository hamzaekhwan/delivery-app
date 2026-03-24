"""
Accounts Models - Simplified Driver Session Tracking
"""

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import random
import string


# ═══════════════════════════════════════════════════════════
#                    Hero Model
# ═══════════════════════════════════════════════════════════
class Hero(models.Model):
    """
    الأبطال - يمكن للسائق اختيار بطل واحد
    """

    number = models.PositiveIntegerField(unique=True, verbose_name="رقم البطل")
    name = models.CharField(max_length=100, verbose_name="اسم البطل")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="اسم البطل (إنجليزي)"
    )
    image = models.ImageField(
        upload_to="heroes/", blank=True, null=True, verbose_name="صورة البطل"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "بطل"
        verbose_name_plural = "الأبطال"
        ordering = ["number"]

    def __str__(self):
        return f"البطل #{self.number} - {self.name}"


# ═══════════════════════════════════════════════════════════
#                    User Manager
# ═══════════════════════════════════════════════════════════
class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("رقم الهاتف مطلوب")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone_number, password, **extra_fields)


# ═══════════════════════════════════════════════════════════
#                    User Model
# ═══════════════════════════════════════════════════════════
class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        USER = "user", "مستخدم"
        ADMIN = "admin", "مدير"
        DRIVER = "driver", "سائق"

    class Governorate(models.TextChoices):
        DAMASCUS = "damascus", "دمشق"
        RIF_DIMASHQ = "rif_dimashq", "ريف دمشق"
        ALEPPO = "aleppo", "حلب"
        HOMS = "homs", "حمص"
        HAMA = "hama", "حماة"
        LATAKIA = "latakia", "اللاذقية"
        TARTOUS = "tartous", "طرطوس"
        IDLIB = "idlib", "إدلب"
        DEIR_EZ_ZOR = "deir_ez_zor", "دير الزور"
        RAQQA = "raqqa", "الرقة"
        HASAKAH = "hasakah", "الحسكة"
        DARA = "daraa", "درعا"
        SUWAYDA = "suwayda", "السويداء"
        QUNEITRA = "quneitra", "القنيطرة"

    # ✅ إضافة اختيارات اللغة
    class Language(models.TextChoices):
        ARABIC = "ar", "العربية"
        ENGLISH = "en", "English"

    phone_number = models.CharField(
        max_length=20, unique=True, verbose_name="رقم الهاتف"
    )
    first_name = models.CharField(max_length=50, verbose_name="الاسم الأول")
    last_name = models.CharField(max_length=50, verbose_name="الاسم الأخير")
    governorate = models.CharField(
        max_length=20,
        choices=Governorate.choices,
        verbose_name="المحافظة",
        blank=True,
        null=True,
    )
    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.USER, verbose_name="الدور"
    )
    is_active = models.BooleanField(default=False, verbose_name="نشط")
    is_staff = models.BooleanField(default=False, verbose_name="موظف")
    date_joined = models.DateTimeField(
        default=timezone.now, verbose_name="تاريخ الانضمام"
    )

    # ✅ حقل اللغة - الافتراضي عربي
    language = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.ARABIC,
        verbose_name="اللغة المفضلة",
    )

    # Driver specific fields
    is_online = models.BooleanField(default=False, verbose_name="متصل")
    last_online = models.DateTimeField(null=True, blank=True, verbose_name="آخر اتصال")
    hero = models.ForeignKey(
        Hero,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drivers",
        verbose_name="البطل",
        help_text="البطل الذي اختاره السائق",
    )

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name", "last_name", "governorate"]

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def save(self, *args, **kwargs):
        if self.phone_number:
            phone = "".join(filter(str.isdigit, self.phone_number))
            if phone.startswith("00"):
                phone = phone[2:]
            elif phone.startswith("09") and len(phone) == 10:
                phone = "963" + phone[1:]
            elif phone.startswith("0") and len(phone) > 10:
                phone = phone[1:]
            self.phone_number = "+" + phone
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.phone_number}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_driver(self):
        return self.role == self.Role.DRIVER

    @property
    def is_hero(self):
        return self.role == self.Role.DRIVER and self.hero is not None

    def go_online(self):
        """Set driver/admin as online and start a new session"""
        if self.role == self.Role.DRIVER:
            self.is_online = True
            self.last_online = timezone.now()
            self.save(update_fields=["is_online", "last_online"])
            DriverSession.start_session(self)
            return True
        elif self.role == self.Role.ADMIN or self.is_staff:
            self.is_online = True
            self.last_online = timezone.now()
            self.save(update_fields=["is_online", "last_online"])
            AdminSession.start_session(self)
            return True
        return False

    def go_offline(self):
        """Set driver/admin as offline and end current session"""
        if self.role == self.Role.DRIVER:
            # Check minimum online drivers limit
            from core.models import AppConfiguration

            config = AppConfiguration.get_config()
            if config.min_online_drivers > 0:
                online_count = (
                    User.objects.filter(role=self.Role.DRIVER, is_online=True)
                    .exclude(id=self.id)
                    .count()
                )
                if online_count < config.min_online_drivers:
                    return (
                        False,
                        "لا يمكنك الخروج، عدد السائقين المتصلين سيصبح أقل من الحد الأدنى",
                    )

            self.is_online = False
            self.last_online = timezone.now()
            self.save(update_fields=["is_online", "last_online"])
            DriverSession.end_active_session(self)
            return True, None
        elif self.role == self.Role.ADMIN or self.is_staff:
            self.is_online = False
            self.last_online = timezone.now()
            self.save(update_fields=["is_online", "last_online"])
            AdminSession.end_active_session(self)
            return True, None
        return False, None


# ═══════════════════════════════════════════════════════════
#                    Driver Session Model
# ═══════════════════════════════════════════════════════════
class DriverSession(models.Model):
    """
    Single model for tracking driver work sessions
    Replaces: DriverWorkLog + DriverDailyStats
    """

    driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sessions",
        limit_choices_to={"role": "driver"},
        verbose_name="السائق",
    )
    date = models.DateField(
        verbose_name="التاريخ", db_index=True, null=True, blank=True
    )
    started_at = models.DateTimeField(verbose_name="وقت البداية", null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت النهاية")
    duration_seconds = models.PositiveIntegerField(
        default=0, verbose_name="المدة (ثواني)"
    )
    is_active = models.BooleanField(default=True, verbose_name="جلسة نشطة")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "جلسة عمل"
        verbose_name_plural = "جلسات عمل السائقين"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["driver", "date"]),
            models.Index(fields=["driver", "is_active"]),
            models.Index(fields=["date", "driver"]),
        ]

    def __str__(self):
        driver_name = self.driver.full_name if self.driver_id else "Unknown"
        date_str = str(self.date) if self.date else "No date"
        return f"{driver_name} - {date_str} ({self.duration_display})"

    def save(self, *args, **kwargs):
        if self.started_at and not self.date:
            self.date = self.started_at.date()
        super().save(*args, **kwargs)

    @property
    def duration_display(self):
        seconds = self.get_duration_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @property
    def duration_hours(self):
        seconds = self.get_duration_seconds()
        if seconds == 0:
            return 0.0
        return round(seconds / 3600, 2)

    def get_duration_seconds(self):
        if not self.started_at:
            return self.duration_seconds or 0

        if self.is_active:
            delta = timezone.now() - self.started_at
            return max(0, int(delta.total_seconds()))

        return self.duration_seconds or 0

    @classmethod
    def start_session(cls, driver):
        cls.end_active_session(driver)
        now = timezone.now()
        return cls.objects.create(
            driver=driver, date=now.date(), started_at=now, is_active=True
        )

    @classmethod
    def end_active_session(cls, driver):
        active_session = cls.objects.filter(driver=driver, is_active=True).first()
        if active_session:
            active_session.end_session()
        return active_session

    def end_session(self):
        if not self.is_active:
            return False

        self.ended_at = timezone.now()
        self.is_active = False

        if self.started_at and self.ended_at:
            self.duration_seconds = max(
                0, int((self.ended_at - self.started_at).total_seconds())
            )
        else:
            self.duration_seconds = 0

        self.save(
            update_fields=["ended_at", "is_active", "duration_seconds", "updated_at"]
        )
        return True

    @classmethod
    def get_daily_stats(cls, driver, date):
        sessions = cls.objects.filter(driver=driver, date=date)

        total_seconds = 0
        first_online = None
        last_offline = None

        for session in sessions.order_by("started_at"):
            total_seconds += session.get_duration_seconds()

            if first_online is None and session.started_at:
                first_online = session.started_at

            if session.ended_at:
                last_offline = session.ended_at
            elif session.is_active:
                last_offline = timezone.now()

        return {
            "date": date,
            "total_online_seconds": total_seconds,
            "total_hours": round(total_seconds / 3600, 2) if total_seconds > 0 else 0.0,
            "formatted_hours": cls._format_seconds(total_seconds),
            "total_sessions": sessions.count(),
            "first_online": first_online,
            "last_offline": last_offline,
        }

    @classmethod
    def get_range_stats(cls, driver, start_date, end_date):
        daily_stats = []
        current_date = start_date

        while current_date <= end_date:
            stats = cls.get_daily_stats(driver, current_date)
            daily_stats.append(stats)
            current_date += timedelta(days=1)

        total_seconds = sum(s["total_online_seconds"] for s in daily_stats)
        total_sessions = sum(s["total_sessions"] for s in daily_stats)

        return {
            "daily_stats": daily_stats,
            "total_seconds": total_seconds,
            "total_hours": round(total_seconds / 3600, 2) if total_seconds > 0 else 0.0,
            "formatted_total": cls._format_seconds(total_seconds),
            "total_sessions": total_sessions,
            "days_count": len(daily_stats),
        }

    @classmethod
    def get_today_stats(cls, driver):
        return cls.get_daily_stats(driver, timezone.now().date())

    @classmethod
    def get_week_stats(cls, driver, date=None):
        if date is None:
            date = timezone.now().date()
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        today = timezone.now().date()
        if end_of_week > today:
            end_of_week = today
        return cls.get_range_stats(driver, start_of_week, end_of_week)

    @classmethod
    def get_month_stats(cls, driver, month=None, year=None):
        today = timezone.now().date()
        if month is None:
            month = today.month
        if year is None:
            year = today.year
        from datetime import date as date_class

        start_of_month = date_class(year, month, 1)
        if month == 12:
            end_of_month = date_class(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date_class(year, month + 1, 1) - timedelta(days=1)
        if end_of_month > today:
            end_of_month = today
        return cls.get_range_stats(driver, start_of_month, end_of_month)

    @classmethod
    def get_logs_for_date(cls, driver, date):
        sessions = cls.objects.filter(driver=driver, date=date).order_by("started_at")
        logs = []
        for session in sessions:
            if session.started_at:
                logs.append(
                    {
                        "id": session.id,
                        "status": "online",
                        "timestamp": session.started_at,
                    }
                )
            if session.ended_at:
                logs.append(
                    {
                        "id": session.id,
                        "status": "offline",
                        "timestamp": session.ended_at,
                    }
                )
        return logs

    @staticmethod
    def _format_seconds(total_seconds):
        if not total_seconds or total_seconds < 0:
            return "00:00:00"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# ═══════════════════════════════════════════════════════════
#                    Admin Session Model
# ═══════════════════════════════════════════════════════════
class AdminSession(models.Model):
    """
    تتبع جلسات عمل الأدمن — نفس نموذج DriverSession
    """

    admin_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="admin_sessions",
        limit_choices_to={"is_staff": True},
        verbose_name="المشرف",
    )
    date = models.DateField(
        verbose_name="التاريخ", db_index=True, null=True, blank=True
    )
    started_at = models.DateTimeField(verbose_name="وقت البداية", null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت النهاية")
    duration_seconds = models.PositiveIntegerField(
        default=0, verbose_name="المدة (ثواني)"
    )
    is_active = models.BooleanField(default=True, verbose_name="جلسة نشطة")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "جلسة عمل مشرف"
        verbose_name_plural = "جلسات عمل المشرفين"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["admin_user", "date"]),
            models.Index(fields=["admin_user", "is_active"]),
            models.Index(fields=["date", "admin_user"]),
        ]

    def __str__(self):
        name = self.admin_user.full_name if self.admin_user_id else "Unknown"
        date_str = str(self.date) if self.date else "No date"
        return f"{name} - {date_str} ({self.duration_display})"

    def save(self, *args, **kwargs):
        if self.started_at and not self.date:
            self.date = self.started_at.date()
        super().save(*args, **kwargs)

    @property
    def duration_display(self):
        seconds = self.get_duration_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @property
    def duration_hours(self):
        seconds = self.get_duration_seconds()
        if seconds == 0:
            return 0.0
        return round(seconds / 3600, 2)

    def get_duration_seconds(self):
        if not self.started_at:
            return self.duration_seconds or 0
        if self.is_active:
            delta = timezone.now() - self.started_at
            return max(0, int(delta.total_seconds()))
        return self.duration_seconds or 0

    @classmethod
    def start_session(cls, admin_user):
        cls.end_active_session(admin_user)
        now = timezone.now()
        return cls.objects.create(
            admin_user=admin_user, date=now.date(), started_at=now, is_active=True
        )

    @classmethod
    def end_active_session(cls, admin_user):
        active_session = cls.objects.filter(
            admin_user=admin_user, is_active=True
        ).first()
        if active_session:
            active_session.end_session()
        return active_session

    def end_session(self):
        if not self.is_active:
            return False
        self.ended_at = timezone.now()
        self.is_active = False
        if self.started_at and self.ended_at:
            self.duration_seconds = max(
                0, int((self.ended_at - self.started_at).total_seconds())
            )
        else:
            self.duration_seconds = 0
        self.save(
            update_fields=["ended_at", "is_active", "duration_seconds", "updated_at"]
        )
        return True

    @classmethod
    def get_daily_stats(cls, admin_user, date):
        sessions = cls.objects.filter(admin_user=admin_user, date=date)
        total_seconds = 0
        first_online = None
        last_offline = None

        for session in sessions.order_by("started_at"):
            total_seconds += session.get_duration_seconds()
            if first_online is None and session.started_at:
                first_online = session.started_at
            if session.ended_at:
                last_offline = session.ended_at
            elif session.is_active:
                last_offline = timezone.now()

        return {
            "date": date,
            "total_online_seconds": total_seconds,
            "total_hours": round(total_seconds / 3600, 2) if total_seconds > 0 else 0.0,
            "formatted_hours": cls._format_seconds(total_seconds),
            "total_sessions": sessions.count(),
            "first_online": first_online,
            "last_offline": last_offline,
        }

    @classmethod
    def get_range_stats(cls, admin_user, start_date, end_date):
        daily_stats = []
        current_date = start_date
        while current_date <= end_date:
            stats = cls.get_daily_stats(admin_user, current_date)
            daily_stats.append(stats)
            current_date += timedelta(days=1)

        total_seconds = sum(s["total_online_seconds"] for s in daily_stats)
        total_sessions = sum(s["total_sessions"] for s in daily_stats)

        return {
            "daily_stats": daily_stats,
            "total_seconds": total_seconds,
            "total_hours": round(total_seconds / 3600, 2) if total_seconds > 0 else 0.0,
            "formatted_total": cls._format_seconds(total_seconds),
            "total_sessions": total_sessions,
            "days_count": len(daily_stats),
        }

    @classmethod
    def get_today_stats(cls, admin_user):
        return cls.get_daily_stats(admin_user, timezone.now().date())

    @classmethod
    def get_week_stats(cls, admin_user, date=None):
        if date is None:
            date = timezone.now().date()
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        today = timezone.now().date()
        if end_of_week > today:
            end_of_week = today
        return cls.get_range_stats(admin_user, start_of_week, end_of_week)

    @classmethod
    def get_month_stats(cls, admin_user, month=None, year=None):
        today = timezone.now().date()
        if month is None:
            month = today.month
        if year is None:
            year = today.year
        from datetime import date as date_class

        start_of_month = date_class(year, month, 1)
        if month == 12:
            end_of_month = date_class(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date_class(year, month + 1, 1) - timedelta(days=1)
        if end_of_month > today:
            end_of_month = today
        return cls.get_range_stats(admin_user, start_of_month, end_of_month)

    @classmethod
    def get_logs_for_date(cls, admin_user, date):
        sessions = cls.objects.filter(admin_user=admin_user, date=date).order_by(
            "started_at"
        )
        logs = []
        for session in sessions:
            if session.started_at:
                logs.append(
                    {
                        "id": session.id,
                        "status": "online",
                        "timestamp": session.started_at,
                    }
                )
            if session.ended_at:
                logs.append(
                    {
                        "id": session.id,
                        "status": "offline",
                        "timestamp": session.ended_at,
                    }
                )
        return logs

    @staticmethod
    def _format_seconds(total_seconds):
        if not total_seconds or total_seconds < 0:
            return "00:00:00"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# ═══════════════════════════════════════════════════════════
#                    OTP Model
# ═══════════════════════════════════════════════════════════
class OTP(models.Model):
    class OTPType(models.TextChoices):
        SIGNUP = "signup", "تسجيل حساب"
        FORGOT_PASSWORD = "forgot_password", "نسيت كلمة المرور"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="otps", verbose_name="المستخدم"
    )
    code = models.CharField(max_length=6, verbose_name="الرمز")
    otp_type = models.CharField(
        max_length=20, choices=OTPType.choices, verbose_name="نوع الرمز"
    )
    is_used = models.BooleanField(default=False, verbose_name="مستخدم")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    expires_at = models.DateTimeField(verbose_name="تاريخ الانتهاء")

    class Meta:
        verbose_name = "رمز التحقق"
        verbose_name_plural = "رموز التحقق"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user.phone_number} - {self.otp_type}"

    @staticmethod
    def generate_code():
        return "".join(random.choices(string.digits, k=6))

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def create_otp(cls, user, otp_type):
        cls.objects.filter(user=user, otp_type=otp_type, is_used=False).update(
            is_used=True
        )
        return cls.objects.create(
            user=user,
            code=cls.generate_code(),
            otp_type=otp_type,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

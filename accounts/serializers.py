"""
Accounts Serializers - Simplified
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, OTP, Hero


def normalize_phone(value):
    """
    تطبيع رقم الهاتف لصيغة موحدة: +[كود الدولة][الرقم]
    - سوري محلي 09XXXXXXXX → +9639XXXXXXXX
    - دولي بصفرين 00971... → +971...
    - دولي بصفر زيادة 0971... → +971...
    - دولي بـ + → يبقى كما هو
    - أرقام بدون + → +[الأرقام]
    """
    phone = "".join(filter(str.isdigit, value))

    if phone.startswith("00"):
        phone = phone[2:]
    elif phone.startswith("09") and len(phone) == 10:
        # رقم سوري محلي: 09XXXXXXXX → 9639XXXXXXXX
        phone = "963" + phone[1:]
    elif phone.startswith("0") and len(phone) > 10:
        phone = phone[1:]

    return "+" + phone


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "password",
            "confirm_password",
        ]
        extra_kwargs = {
            "phone_number": {"validators": []},  # أزل UniqueValidator التلقائي
        }

    def validate_phone_number(self, value):
        phone = normalize_phone(value)
        if len(phone) < 9 or len(phone) > 15:
            raise serializers.ValidationError("رقم الهاتف غير صالح")

        # احذف غير المفعّلين أولاً
        User.objects.filter(phone_number=phone, is_active=False).delete()

        # ثم تحقق من المفعّلين
        if User.objects.filter(phone_number=phone, is_active=True).exists():
            raise serializers.ValidationError("رقم الهاتف مسجل مسبقاً")

        return phone

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)

        user = User.objects.create_user(
            phone_number=validated_data["phone_number"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=False,
        )
        return user


class LanguageSerializer(serializers.ModelSerializer):
    """Serializer لعرض وتحديث اللغة المفضلة"""

    language_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["language", "language_display"]

    def get_language_display(self, obj):
        return obj.get_language_display()

    def validate_language(self, value):
        allowed = [choice[0] for choice in User.Language.choices]
        if value not in allowed:
            raise serializers.ValidationError(
                f"اللغة غير مدعومة. الخيارات المتاحة: {allowed}"
            )
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    otp_type = serializers.ChoiceField(choices=OTP.OTPType.choices)

    def validate(self, data):
        phone = normalize_phone(data["phone_number"])
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError({"phone_number": "المستخدم غير موجود"})

        otp = (
            OTP.objects.filter(
                user=user,
                code=data["otp_code"],
                otp_type=data["otp_type"],
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            raise serializers.ValidationError({"otp_code": "رمز التحقق غير صحيح"})

        if not otp.is_valid():
            raise serializers.ValidationError({"otp_code": "رمز التحقق منتهي الصلاحية"})

        data["user"] = user
        data["otp"] = otp
        return data


class ResendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp_type = serializers.ChoiceField(choices=OTP.OTPType.choices)

    def validate_phone_number(self, value):
        phone = normalize_phone(value)
        if not User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError("المستخدم غير موجود")
        return phone


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = normalize_phone(data.get("phone_number", ""))
        password = data.get("password")

        if phone_number and password:
            user = authenticate(username=phone_number, password=password)

            if not user:
                raise serializers.ValidationError("رقم الهاتف أو كلمة المرور غير صحيحة")

            if not user.is_active:
                raise serializers.ValidationError(
                    "الحساب غير مفعل. يرجى التحقق من رمز OTP"
                )
        else:
            raise serializers.ValidationError("يجب إدخال رقم الهاتف وكلمة المرور")

        data["user"] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        phone = normalize_phone(value)
        try:
            user = User.objects.get(phone_number=phone, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("لا يوجد حساب مفعل بهذا الرقم")
        return phone


class ResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "كلمتا المرور غير متطابقتين"}
            )

        try:
            user = User.objects.get(phone_number=normalize_phone(data["phone_number"]))
        except User.DoesNotExist:
            raise serializers.ValidationError({"phone_number": "المستخدم غير موجود"})

        otp = (
            OTP.objects.filter(
                user=user,
                code=data["otp_code"],
                otp_type=OTP.OTPType.FORGOT_PASSWORD,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            raise serializers.ValidationError({"otp_code": "رمز التحقق غير صحيح"})

        if not otp.is_valid():
            raise serializers.ValidationError({"otp_code": "رمز التحقق منتهي الصلاحية"})

        data["user"] = user
        data["otp"] = otp
        return data


class UserSerializer(serializers.ModelSerializer):
    is_online = serializers.BooleanField(read_only=True)
    last_online = serializers.DateTimeField(read_only=True)
    is_hero = serializers.BooleanField(read_only=True)
    hero_id = serializers.IntegerField(
        source="hero.id", read_only=True, allow_null=True
    )
    hero_number = serializers.IntegerField(
        source="hero.number", read_only=True, allow_null=True
    )
    hero_name = serializers.CharField(
        source="hero.name", read_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "governorate",
            "role",
            "date_joined",
            "is_online",
            "last_online",
            "is_hero",
            "hero_id",
            "hero_number",
            "hero_name",
        ]
        read_only_fields = [
            "id",
            "phone_number",
            "role",
            "date_joined",
            "is_online",
            "last_online",
        ]


class DriverStatusSerializer(serializers.Serializer):
    is_online = serializers.BooleanField()

    def validate(self, data):
        user = self.context["request"].user
        if user.role != User.Role.DRIVER:
            raise serializers.ValidationError(
                "This feature is only available for drivers"
            )
        return data


class DriverDailyStatsSerializer(serializers.Serializer):
    """Serializer for daily stats response"""

    date = serializers.DateField()
    total_online_seconds = serializers.IntegerField()
    total_hours = serializers.FloatField()
    formatted_hours = serializers.CharField()
    total_sessions = serializers.IntegerField()
    first_online = serializers.DateTimeField(allow_null=True)
    last_offline = serializers.DateTimeField(allow_null=True)


class DriverRangeStatsSerializer(serializers.Serializer):
    """Serializer for range stats input validation"""

    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        if data["start_date"] > data["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date"}
            )

        from datetime import timedelta

        if (data["end_date"] - data["start_date"]).days > 90:
            raise serializers.ValidationError(
                {"end_date": "Date range cannot exceed 90 days"}
            )

        return data


class DriverStatsResponseSerializer(serializers.Serializer):
    """Serializer for stats response"""

    daily_stats = DriverDailyStatsSerializer(many=True)
    total_seconds = serializers.IntegerField()
    total_hours = serializers.FloatField()
    formatted_total = serializers.CharField()
    total_sessions = serializers.IntegerField()
    days_count = serializers.IntegerField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "كلمتا المرور غير متطابقتين"}
            )
        return data

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("كلمة المرور الحالية غير صحيحة")
        return value


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout request"""

    refresh = serializers.CharField(
        required=False, help_text="Refresh token to blacklist"
    )


class HeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hero
        fields = ["id", "number", "name", "image", "is_active"]


class SelectHeroSerializer(serializers.Serializer):
    hero_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="معرف البطل (أرسل null لإزالة البطل)"
    )

    def validate_hero_id(self, value):
        if value is not None:
            if not Hero.objects.filter(id=value, is_active=True).exists():
                raise serializers.ValidationError("البطل غير موجود أو غير نشط")
        return value


class EmptySerializer(serializers.Serializer):
    """Empty serializer for endpoints that don't require input"""

    pass


class DeleteAccountSerializer(serializers.Serializer):
    """Serializer for account deletion confirmation"""

    password = serializers.CharField(required=True, write_only=True)
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("كلمة المرور غير صحيحة")
        return value

"""
Core Utilities - Helper functions and utilities
"""

import math
import re
import uuid
from decimal import Decimal
from django.utils import timezone
from django.conf import settings


def generate_order_number():
    """Generate a short sequential order number: ORD-1001, ORD-1002, ..."""
    from orders.models import Order

    last_order = (
        Order.objects.filter(order_number__startswith="ORD-")
        .order_by("-id")
        .values_list("order_number", flat=True)
        .first()
    )

    if last_order:
        try:
            last_num = int(last_order.split("-")[1])
            new_num = last_num + 1
        except (IndexError, ValueError):
            new_num = 1001
    else:
        new_num = 1001

    # Handle race condition: if number exists, find the actual max
    while Order.objects.filter(order_number=f"ORD-{new_num}").exists():
        new_num += 1

    return f"ORD-{new_num}"


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    if not all([lat1, lon1, lat2, lon2]):
        return None

    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c * 1.3  # Road correction factor (Haversine gives straight-line)


def round_decimal(value, places=2):
    """Round a decimal value to specified places"""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal(10) ** -places)


def calculate_delivery_fee(distance_km, config=None):
    """
    Calculate delivery fee based on distance.
    Formula:
      - 0 to free_distance_km: base_delivery_fee
      - beyond: base_delivery_fee + (distance - free_distance_km) * per_km_fee
      - capped at max_delivery_fee if set
    """
    from core.models import AppConfiguration

    if config is None:
        config = AppConfiguration.get_config()

    base = config.base_delivery_fee
    free_km = config.free_distance_km
    per_km = config.per_km_fee
    max_fee = config.max_delivery_fee

    if distance_km is None:
        return base

    distance = Decimal(str(distance_km))

    if distance <= free_km:
        fee = base
    else:
        extra_km = distance - free_km
        fee = base + (extra_km * per_km)

    # Round up to nearest 1000
    fee = math.ceil(fee / 1000) * 1000
    fee = Decimal(str(fee))

    if max_fee and max_fee > 0 and fee > max_fee:
        fee = max_fee

    return fee


def calculate_delivery_fee_between(lat1, lon1, lat2, lon2, config=None):
    """
    Calculate delivery fee between two coordinates.
    Applies road correction factor to convert straight-line to road distance.
    Returns (fee, distance_km) tuple.
    Returns (None, None) if coordinates are missing.
    """
    from core.models import AppConfiguration

    if not all([lat1, lon1, lat2, lon2]):
        return None, None

    if config is None:
        config = AppConfiguration.get_config()

    straight_distance = calculate_distance(lat1, lon1, lat2, lon2)
    if straight_distance is None:
        return None, None

    # Apply road correction factor
    road_distance = straight_distance
    road_distance = round(road_distance, 2)

    fee = calculate_delivery_fee(road_distance, config)
    return fee, road_distance


def is_within_working_hours(open_time, close_time):
    """
    Check if current time is within working hours.
    open_time and close_time are strings in 24h format (HH:MM)
    """
    if not open_time or not close_time:
        return True

    now = timezone.localtime().time()

    try:
        open_parts = open_time.split(":")
        close_parts = close_time.split(":")

        from datetime import time

        open_t = time(int(open_parts[0]), int(open_parts[1]))
        close_t = time(int(close_parts[0]), int(close_parts[1]))

        # Handle overnight hours (e.g., 22:00 - 02:00)
        if close_t < open_t:
            return now >= open_t or now <= close_t

        return open_t <= now <= close_t
    except (ValueError, IndexError):
        return True


def calculate_discount(original_price, discount_type, discount_value):
    """
    Calculate discounted price.
    discount_type: 'percentage' or 'fixed'
    """
    from core.constants import DiscountType

    original = Decimal(str(original_price))
    value = Decimal(str(discount_value))

    if discount_type == DiscountType.PERCENTAGE:
        discount_amount = original * (value / 100)
    else:
        discount_amount = value

    final_price = original - discount_amount
    return max(final_price, Decimal("0"))


def is_discount_active(start_date, end_date):
    """Check if a discount is currently active based on dates"""
    now = timezone.now()

    if start_date and now < start_date:
        return False
    if end_date and now > end_date:
        return False

    return True


def format_price(price, currency="SYP"):
    """Format price with currency"""
    return f"{price:,.2f} {currency}"


def paginate_queryset(queryset, page=1, per_page=10):
    """
    Simple pagination helper.
    Returns (paginated_queryset, total_pages, total_count)
    """
    total_count = queryset.count()
    total_pages = math.ceil(total_count / per_page)

    start = (page - 1) * per_page
    end = start + per_page

    return queryset[start:end], total_pages, total_count


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def create_snapshot(data):
    """
    Create a JSON-serializable snapshot of data.
    Used for storing order snapshots.
    """
    import json
    from decimal import Decimal
    from datetime import datetime, date

    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return str(obj)
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super().default(obj)

    return json.loads(json.dumps(data, cls=CustomEncoder))


def validate_phone_number(phone):
    """Validate Syrian phone number format"""
    # Syrian phone numbers: 09XXXXXXXX
    pattern = r"^09\d{8}$"
    return bool(re.match(pattern, phone))


def normalize_arabic(text):
    """
    تطبيع النص العربي للبحث — يعالج:
    1. الهمزات: أ إ آ → ا، ئ → ي، ؤ → و
    2. التاء المربوطة: ة → ه
    3. الألف المقصورة: ى → ي
    4. التشكيل: حذف الفتحة والضمة والكسرة...
    """
    if not text:
        return ""

    # حذف التشكيل
    text = re.sub(r"[\u0617-\u061A\u064B-\u0652\u0670]", "", text)

    # توحيد الهمزات
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ٱ", "ا")
    text = text.replace("ئ", "ي")
    text = text.replace("ؤ", "و")

    # التاء المربوطة → هاء
    text = text.replace("ة", "ه")

    # الألف المقصورة → ياء
    text = text.replace("ى", "ي")

    return text.strip()


def build_arabic_search_pattern(text):
    """
    بناء regex pattern للبحث العربي — يستبدل كل حرف عربي متغير بمجموعة تشمل كل أشكاله.
    مثال: "ابو" → "[اأإآٱ]بو" — فيلاقي "أبو" و "ابو" و "إبو" و "آبو"
    يُستخدم مع Django __iregex
    """
    if not text:
        return ""

    # حذف التشكيل أولاً
    text = re.sub(r"[\u0617-\u061A\u064B-\u0652\u0670]", "", text)

    alef_group = "اأإآٱ"
    ya_group = "يئى"
    waw_group = "وؤ"
    ta_group = "ةه"

    pattern = ""
    for ch in text:
        if ch in alef_group:
            pattern += "[اأإآٱ]"
        elif ch in ya_group:
            pattern += "[يئى]"
        elif ch in waw_group:
            pattern += "[وؤ]"
        elif ch in ta_group:
            pattern += "[ةه]"
        else:
            pattern += re.escape(ch)

    return pattern


def mask_phone_number(phone):
    """Mask phone number for privacy"""
    if not phone or len(phone) < 4:
        return phone
    return phone[:4] + "*" * (len(phone) - 7) + phone[-3:]


def get_time_ago(dt):
    """Get human-readable time ago string"""
    if not dt:
        return ""

    now = timezone.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "الآن"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"منذ {minutes} دقيقة" if minutes == 1 else f"منذ {minutes} دقائق"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"منذ {hours} ساعة" if hours == 1 else f"منذ {hours} ساعات"
    else:
        days = int(seconds / 86400)
        return f"منذ {days} يوم" if days == 1 else f"منذ {days} أيام"

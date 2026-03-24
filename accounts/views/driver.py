"""
Driver Views - Status, Stats, Work Logs, Heroes
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
)

from ..models import User, DriverSession, Hero
from ..serializers import (
    DriverStatusSerializer,
    UserSerializer,
    EmptySerializer,
    HeroSerializer,
    SelectHeroSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DRIVER STATUS VIEWS
# =============================================================================


@extend_schema(tags=["Driver"])
class DriverStatusView(APIView):
    """Get and update driver online status"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Driver Status",
        description="Get current driver online status",
        responses={
            200: OpenApiResponse(description="Driver status"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get active session info if online
        active_session = None
        if user.is_online:
            active_session = DriverSession.objects.filter(
                driver=user, is_active=True
            ).first()

        return Response(
            {
                "success": True,
                "is_online": user.is_online,
                "last_online": user.last_online,
                "active_session": {
                    "started_at": active_session.started_at,
                    "duration": active_session.duration_display,
                }
                if active_session
                else None,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update Driver Status",
        description="Set driver as online or offline",
        request=DriverStatusSerializer,
        responses={
            200: OpenApiResponse(description="Status updated"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def post(self, request):
        serializer = DriverStatusSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            user = request.user
            is_online = serializer.validated_data["is_online"]

            if is_online:
                user.go_online()
                message = "You are now online"
            else:
                success, error = user.go_offline()
                if not success:
                    return Response(
                        {
                            "success": False,
                            "message": error,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                message = "You are now offline"

            return Response(
                {
                    "success": True,
                    "message": message,
                    "is_online": user.is_online,
                    "last_online": user.last_online,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Driver"])
class DriverGoOnlineView(APIView):
    """Quick endpoint to go online"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Go Online",
        description="Quick endpoint to set driver as online",
        request=EmptySerializer,
        responses={
            200: OpenApiResponse(description="Now online"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def post(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user.go_online()

        return Response(
            {
                "success": True,
                "message": "You are now online",
                "is_online": True,
                "last_online": user.last_online,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver"])
class DriverGoOfflineView(APIView):
    """Quick endpoint to go offline"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Go Offline",
        description="Quick endpoint to set driver as offline",
        request=EmptySerializer,
        responses={
            200: OpenApiResponse(description="Now offline"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def post(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        success, error = user.go_offline()
        if not success:
            return Response(
                {
                    "success": False,
                    "message": error,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "You are now offline",
                "is_online": False,
                "last_online": user.last_online,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# DRIVER STATS VIEWS (Using DriverSession only)
# =============================================================================


@extend_schema(tags=["Driver Stats"])
class DriverTodayStatsView(APIView):
    """Get today's work hours for driver"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Today's Stats",
        description="Get driver's work hours for today",
        responses={
            200: OpenApiResponse(description="Today's statistics"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        stats = DriverSession.get_today_stats(user)

        return Response(
            {
                "success": True,
                "date": str(stats["date"]),
                "total_hours": stats["total_hours"],
                "formatted_hours": stats["formatted_hours"],
                "total_online_seconds": stats["total_online_seconds"],
                "total_sessions": stats["total_sessions"],
                "first_online": stats["first_online"],
                "last_offline": stats["last_offline"],
                "is_currently_online": user.is_online,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver Stats"])
class DriverDailyStatsView(APIView):
    """Get work hours for a specific date"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Daily Stats",
        description="Get driver's work hours for a specific date",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Date in YYYY-MM-DD format",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={
            200: OpenApiResponse(description="Daily statistics"),
            400: OpenApiResponse(description="Invalid date format"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {
                    "success": False,
                    "message": "Date parameter is required (YYYY-MM-DD)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stats = DriverSession.get_daily_stats(user, date)

        return Response(
            {
                "success": True,
                "date": str(date),
                "total_hours": stats["total_hours"],
                "formatted_hours": stats["formatted_hours"],
                "total_online_seconds": stats["total_online_seconds"],
                "total_sessions": stats["total_sessions"],
                "first_online": stats["first_online"],
                "last_offline": stats["last_offline"],
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver Stats"])
class DriverRangeStatsView(APIView):
    """Get work hours for a date range"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Range Stats",
        description="Get driver's work hours for a date range (max 90 days)",
        parameters=[
            OpenApiParameter(
                name="start_date",
                description="Start date in YYYY-MM-DD format",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="end_date",
                description="End date in YYYY-MM-DD format",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Range statistics"),
            400: OpenApiResponse(description="Invalid parameters"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str or not end_date_str:
            return Response(
                {
                    "success": False,
                    "message": "Both start_date and end_date are required (YYYY-MM-DD)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date > end_date:
            return Response(
                {"success": False, "message": "start_date must be before end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (end_date - start_date).days > 90:
            return Response(
                {"success": False, "message": "Date range cannot exceed 90 days"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        range_stats = DriverSession.get_range_stats(user, start_date, end_date)

        # Convert daily_stats to serializable format
        daily_stats_data = []
        for stat in range_stats["daily_stats"]:
            daily_stats_data.append(
                {
                    "date": str(stat["date"]),
                    "total_hours": stat["total_hours"],
                    "formatted_hours": stat["formatted_hours"],
                    "total_online_seconds": stat["total_online_seconds"],
                    "total_sessions": stat["total_sessions"],
                    "first_online": stat["first_online"],
                    "last_offline": stat["last_offline"],
                }
            )

        return Response(
            {
                "success": True,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "total_hours": range_stats["total_hours"],
                "formatted_total": range_stats["formatted_total"],
                "total_seconds": range_stats["total_seconds"],
                "total_sessions": range_stats["total_sessions"],
                "days_count": range_stats["days_count"],
                "daily_stats": daily_stats_data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver Stats"])
class DriverWeeklyStatsView(APIView):
    """Get work hours for current week"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="This Week's Stats",
        description="Get driver's work hours for the current week (Monday to Sunday)",
        responses={
            200: OpenApiResponse(description="Weekly statistics"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        if end_of_week > today:
            end_of_week = today

        range_stats = DriverSession.get_range_stats(user, start_of_week, end_of_week)

        daily_stats_data = []
        for stat in range_stats["daily_stats"]:
            daily_stats_data.append(
                {
                    "date": str(stat["date"]),
                    "day_name": stat["date"].strftime("%A"),
                    "total_hours": stat["total_hours"],
                    "formatted_hours": stat["formatted_hours"],
                    "total_sessions": stat["total_sessions"],
                }
            )

        return Response(
            {
                "success": True,
                "week_start": str(start_of_week),
                "week_end": str(end_of_week),
                "total_hours": range_stats["total_hours"],
                "formatted_total": range_stats["formatted_total"],
                "total_sessions": range_stats["total_sessions"],
                "days_worked": sum(
                    1
                    for s in range_stats["daily_stats"]
                    if s["total_online_seconds"] > 0
                ),
                "daily_stats": daily_stats_data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver Stats"])
class DriverMonthlyStatsView(APIView):
    """Get work hours for current month"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="This Month's Stats",
        description="Get driver's work hours for the current month",
        parameters=[
            OpenApiParameter(
                name="month",
                description="Month (1-12), defaults to current month",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="year",
                description="Year (e.g., 2024), defaults to current year",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Monthly statistics"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.now().date()

        month = request.query_params.get("month")
        year = request.query_params.get("year")

        try:
            month = int(month) if month else today.month
            year = int(year) if year else today.year

            if not (1 <= month <= 12):
                raise ValueError("Invalid month")
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid month or year"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        range_stats = DriverSession.get_month_stats(user, month, year)

        # Group by week
        weekly_summary = {}
        for stat in range_stats["daily_stats"]:
            week_num = stat["date"].isocalendar()[1]
            if week_num not in weekly_summary:
                weekly_summary[week_num] = {
                    "week_number": week_num,
                    "total_seconds": 0,
                    "total_sessions": 0,
                    "days_worked": 0,
                }
            weekly_summary[week_num]["total_seconds"] += stat["total_online_seconds"]
            weekly_summary[week_num]["total_sessions"] += stat["total_sessions"]
            if stat["total_online_seconds"] > 0:
                weekly_summary[week_num]["days_worked"] += 1

        weekly_data = []
        for week_num, data in sorted(weekly_summary.items()):
            hours = data["total_seconds"] / 3600
            weekly_data.append(
                {
                    "week_number": week_num,
                    "total_hours": round(hours, 2),
                    "formatted_hours": DriverSession._format_seconds(
                        data["total_seconds"]
                    ),
                    "total_sessions": data["total_sessions"],
                    "days_worked": data["days_worked"],
                }
            )

        # Get month name
        from datetime import date as date_class

        start_of_month = date_class(year, month, 1)

        return Response(
            {
                "success": True,
                "month": month,
                "year": year,
                "month_name": start_of_month.strftime("%B"),
                "total_hours": range_stats["total_hours"],
                "formatted_total": range_stats["formatted_total"],
                "total_sessions": range_stats["total_sessions"],
                "days_worked": sum(
                    1
                    for s in range_stats["daily_stats"]
                    if s["total_online_seconds"] > 0
                ),
                "total_days": range_stats["days_count"],
                "weekly_breakdown": weekly_data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver Stats"])
class DriverWorkLogsView(APIView):
    """Get raw work logs for driver"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Work Logs",
        description="Get raw online/offline logs for a specific date",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Date in YYYY-MM-DD format (defaults to today)",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={
            200: OpenApiResponse(description="Work logs"),
            403: OpenApiResponse(description="Not a driver"),
        },
    )
    def get(self, request):
        user = request.user

        if user.role != User.Role.DRIVER:
            return Response(
                {
                    "success": False,
                    "message": "This feature is only available for drivers",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        date_str = request.query_params.get("date")

        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid date format. Use YYYY-MM-DD",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            date = timezone.now().date()

        logs = DriverSession.get_logs_for_date(user, date)

        return Response(
            {
                "success": True,
                "date": str(date),
                "total_logs": len(logs),
                "logs": logs,
            },
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════
#                    Hero Views
# ═══════════════════════════════════════════════════════════


@extend_schema(tags=["Driver - Heroes"])
class HeroListView(APIView):
    """قائمة الأبطال المتاحة"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="قائمة الأبطال المتاحة",
        description="الحصول على قائمة الأبطال المتاحة (غير المحجوزة) + بطل السائق الحالي إن وجد",
        responses={200: HeroSerializer(many=True)},
    )
    def get(self, request):
        # Heroes that are active AND (not taken OR taken by current user)
        taken_hero_ids = (
            User.objects.filter(role=User.Role.DRIVER, hero__isnull=False)
            .exclude(id=request.user.id)
            .values_list("hero_id", flat=True)
        )

        heroes = Hero.objects.filter(is_active=True).exclude(id__in=taken_hero_ids)
        serializer = HeroSerializer(heroes, many=True)

        my_hero = None
        try:
            if request.user.hero:
                my_hero = HeroSerializer(request.user.hero).data
        except (Hero.DoesNotExist, AttributeError):
            pass

        return Response(
            {
                "success": True,
                "my_hero": my_hero,
                "available_heroes": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Driver - Heroes"])
class SelectHeroView(APIView):
    """اختيار بطل للسائق"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="اختيار بطل",
        description="يختار السائق بطلاً من الأبطال المتاحة (أرسل hero_id=null لإزالة البطل)",
        request=SelectHeroSerializer,
        responses={200: UserSerializer},
    )
    def post(self, request):
        user = request.user
        if user.role != User.Role.DRIVER:
            return Response(
                {"success": False, "error": "هذه الخدمة للسائقين فقط"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SelectHeroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hero_id = serializer.validated_data.get("hero_id")
        if hero_id is not None:
            user.hero = Hero.objects.get(id=hero_id)
        else:
            user.hero = None
        user.save(update_fields=["hero"])

        return Response(
            {
                "success": True,
                "message": "تم تحديث البطل بنجاح",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

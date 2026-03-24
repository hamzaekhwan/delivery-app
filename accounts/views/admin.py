"""
Admin Views - Status, Stats, Work Logs
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
)

from ..models import AdminSession

logger = logging.getLogger(__name__)


# =============================================================================
# ADMIN STATUS & STATS VIEWS
# =============================================================================


@extend_schema(tags=["Admin Stats"])
class AdminStatusView(APIView):
    """Get and update admin online status"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Admin Status",
        description="Get current admin online status",
    )
    def get(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
                status=status.HTTP_403_FORBIDDEN,
            )

        active_session = None
        if user.is_online:
            active_session = AdminSession.objects.filter(
                admin_user=user, is_active=True
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
            }
        )


@extend_schema(tags=["Admin Stats"])
class AdminGoOnlineView(APIView):
    """Set admin as online"""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Admin Go Online")
    def post(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.go_online()
        return Response(
            {
                "success": True,
                "message": "أنت الآن متصل",
                "is_online": True,
                "last_online": user.last_online,
            }
        )


@extend_schema(tags=["Admin Stats"])
class AdminGoOfflineView(APIView):
    """Set admin as offline"""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Admin Go Offline")
    def post(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.go_offline()
        return Response(
            {
                "success": True,
                "message": "أنت الآن غير متصل",
                "is_online": False,
                "last_online": user.last_online,
            }
        )


@extend_schema(tags=["Admin Stats"])
class AdminTodayStatsView(APIView):
    """Get today's work hours for admin"""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Admin Today Stats")
    def get(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
                status=status.HTTP_403_FORBIDDEN,
            )

        stats = AdminSession.get_today_stats(user)
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
            }
        )


@extend_schema(tags=["Admin Stats"])
class AdminDailyStatsView(APIView):
    """Get work hours for a specific date"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Admin Daily Stats",
        parameters=[
            OpenApiParameter(
                name="date", description="YYYY-MM-DD", required=True, type=str
            ),
        ],
    )
    def get(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
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

        stats = AdminSession.get_daily_stats(user, date)
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
            }
        )


@extend_schema(tags=["Admin Stats"])
class AdminRangeStatsView(APIView):
    """Get work hours for a date range"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Admin Range Stats",
        parameters=[
            OpenApiParameter(
                name="start_date", description="YYYY-MM-DD", required=True, type=str
            ),
            OpenApiParameter(
                name="end_date", description="YYYY-MM-DD", required=True, type=str
            ),
        ],
    )
    def get(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
                status=status.HTTP_403_FORBIDDEN,
            )

        start_str = request.query_params.get("start_date")
        end_str = request.query_params.get("end_date")
        if not start_str or not end_str:
            return Response(
                {
                    "success": False,
                    "message": "Both start_date and end_date are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
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

        range_stats = AdminSession.get_range_stats(user, start_date, end_date)
        daily_data = [
            {
                "date": str(s["date"]),
                "total_hours": s["total_hours"],
                "formatted_hours": s["formatted_hours"],
                "total_online_seconds": s["total_online_seconds"],
                "total_sessions": s["total_sessions"],
                "first_online": s["first_online"],
                "last_offline": s["last_offline"],
            }
            for s in range_stats["daily_stats"]
        ]

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
                "daily_stats": daily_data,
            }
        )


@extend_schema(tags=["Admin Stats"])
class AdminWorkLogsView(APIView):
    """Get admin on/off logs for a specific date"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Admin Work Logs",
        parameters=[
            OpenApiParameter(
                name="date", description="YYYY-MM-DD", required=True, type=str
            ),
        ],
    )
    def get(self, request):
        user = request.user
        if not user.is_staff:
            return Response(
                {"success": False, "message": "هذه الخدمة للمشرفين فقط"},
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

        logs = AdminSession.get_logs_for_date(user, date)
        return Response({"success": True, "date": str(date), "logs": logs})

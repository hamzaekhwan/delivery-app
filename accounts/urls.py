"""
Accounts URL Configuration - Same endpoints, simplified backend
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = "accounts"

urlpatterns = [
    # Registration & Verification
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("verify-otp/", views.VerifyOTPView.as_view(), name="verify-otp"),
    path("resend-otp/", views.ResendOTPView.as_view(), name="resend-otp"),
    # Login & Logout
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # Password
    path(
        "forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"
    ),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change-password"
    ),
    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    # Driver Status
    path("driver/status/", views.DriverStatusView.as_view(), name="driver-status"),
    path(
        "driver/go-online/", views.DriverGoOnlineView.as_view(), name="driver-go-online"
    ),
    path(
        "driver/go-offline/",
        views.DriverGoOfflineView.as_view(),
        name="driver-go-offline",
    ),
    # Driver Work Hours Stats (same endpoints!)
    path(
        "driver/stats/today/",
        views.DriverTodayStatsView.as_view(),
        name="driver-stats-today",
    ),
    path(
        "driver/stats/daily/",
        views.DriverDailyStatsView.as_view(),
        name="driver-stats-daily",
    ),
    path(
        "driver/stats/weekly/",
        views.DriverWeeklyStatsView.as_view(),
        name="driver-stats-weekly",
    ),
    path(
        "driver/stats/monthly/",
        views.DriverMonthlyStatsView.as_view(),
        name="driver-stats-monthly",
    ),
    path(
        "driver/stats/range/",
        views.DriverRangeStatsView.as_view(),
        name="driver-stats-range",
    ),
    path("driver/logs/", views.DriverWorkLogsView.as_view(), name="driver-work-logs"),
    path("language/", views.LanguageView.as_view(), name="user-language"),
    # Admin Status & Stats
    path("admin/status/", views.AdminStatusView.as_view(), name="admin-status"),
    path("admin/go-online/", views.AdminGoOnlineView.as_view(), name="admin-go-online"),
    path(
        "admin/go-offline/",
        views.AdminGoOfflineView.as_view(),
        name="admin-go-offline",
    ),
    path(
        "admin/stats/today/",
        views.AdminTodayStatsView.as_view(),
        name="admin-stats-today",
    ),
    path(
        "admin/stats/daily/",
        views.AdminDailyStatsView.as_view(),
        name="admin-stats-daily",
    ),
    path(
        "admin/stats/range/",
        views.AdminRangeStatsView.as_view(),
        name="admin-stats-range",
    ),
    path("admin/logs/", views.AdminWorkLogsView.as_view(), name="admin-work-logs"),
    # Account Deletion
    path(
        "delete-account/",
        views.DeleteAccountView.as_view(),
        name="delete-account",
    ),
    # Heroes
    path("heroes/", views.HeroListView.as_view(), name="hero-list"),
    path(
        "driver/select-hero/", views.SelectHeroView.as_view(), name="driver-select-hero"
    ),
]

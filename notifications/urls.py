"""
Notifications URL Configuration
"""

from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadCountView,
    RegisterDeviceView,
    UnregisterDeviceView,
    UserDevicesView,
    NotificationPreferencesView,
    DeleteNotificationView,
    ClearNotificationsView,
    BroadcastNotificationListView,
    SendBroadcastView,
)

app_name = "notifications"

urlpatterns = [
    # User notifications
    path("", NotificationListView.as_view(), name="list"),
    path("<int:pk>/", NotificationDetailView.as_view(), name="detail"),
    path("<int:pk>/read/", MarkNotificationReadView.as_view(), name="mark-read"),
    path("read-all/", MarkAllNotificationsReadView.as_view(), name="mark-all-read"),
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
    path("<int:pk>/delete/", DeleteNotificationView.as_view(), name="delete"),
    path("clear/", ClearNotificationsView.as_view(), name="clear"),
    # Device management
    path("devices/", UserDevicesView.as_view(), name="devices"),
    path("devices/register/", RegisterDeviceView.as_view(), name="register-device"),
    path(
        "devices/unregister/", UnregisterDeviceView.as_view(), name="unregister-device"
    ),
    # Preferences
    path("preferences/", NotificationPreferencesView.as_view(), name="preferences"),
    # Admin - Broadcasts
    path("broadcasts/", BroadcastNotificationListView.as_view(), name="broadcasts"),
    path(
        "broadcasts/<int:pk>/send/", SendBroadcastView.as_view(), name="send-broadcast"
    ),
]

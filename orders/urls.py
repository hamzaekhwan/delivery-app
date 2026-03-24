"""
Orders URLs - Complete order routing
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"", views.OrderViewSet, basename="order")

# Driver router
driver_router = DefaultRouter()
driver_router.register(r"orders", views.DriverOrderViewSet, basename="driver-order")

# Admin router
admin_router = DefaultRouter()
admin_router.register(r"orders/new", views.AdminOrderViewSet, basename="admin-orders")

app_name = "orders"

urlpatterns = [
    # User Order APIs
    path("create/", views.CreateOrderView.as_view(), name="create-order"),
    path("<int:order_id>/place/", views.PlaceOrderView.as_view(), name="place-order"),
    path(
        "<int:order_id>/cancel/", views.CancelOrderView.as_view(), name="cancel-order"
    ),
    path("<int:order_id>/reorder/", views.ReorderView.as_view(), name="reorder"),
    # Driver APIs
    path(
        "driver/pending/",
        views.DriverPendingRequestsView.as_view(),
        name="driver-pending",
    ),
    path(
        "driver/request/<int:request_id>/accept/",
        views.AcceptOrderRequestView.as_view(),
        name="accept-request",
    ),
    path(
        "driver/request/<int:request_id>/reject/",
        views.RejectOrderRequestView.as_view(),
        name="reject-request",
    ),
    path(
        "driver/<int:order_id>/status/",
        views.DriverUpdateOrderStatusView.as_view(),
        name="driver-update-status",
    ),
    path(
        "driver/<int:order_id>/set-price/",
        views.DriverSetOrderPriceView.as_view(),
        name="driver-set-price",
    ),
    path(
        "driver/<int:order_id>/delivery-report/",
        views.DriverSubmitDeliveryReportView.as_view(),
        name="driver-delivery-report",
    ),
    path("driver/", include(driver_router.urls)),
    # Restaurant APIs
    path(
        "restaurant/<int:order_id>/status/",
        views.RestaurantUpdateOrderStatusView.as_view(),
        name="restaurant-update-status",
    ),
    # Admin APIs
    path(
        "admin/orders/manual/create/",
        views.CreateManualOrderView.as_view(),
        name="create-manual-order",
    ),
    path("admin/", include(admin_router.urls)),
    # ViewSet routes
    path("", include(router.urls)),
]

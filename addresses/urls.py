from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "addresses"


class CustomRouter(DefaultRouter):
    """Custom router to use integer IDs"""

    pass


router = DefaultRouter()
router.register("", views.AddressViewSet, basename="address")


urlpatterns = [
    path("", include(router.urls)),
    path("locations/governorates/", views.list_governorates, name="governorates"),
    path("locations/areas/", views.list_areas, name="areas"),
]

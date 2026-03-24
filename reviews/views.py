"""
Reviews Views
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import RestaurantReview, DriverReview
from .serializers import (
    RestaurantReviewListSerializer,
    RestaurantReviewDetailSerializer,
    CreateRestaurantReviewSerializer,
    DriverReviewListSerializer,
    DriverReviewDetailSerializer,
    CreateDriverReviewSerializer,
    ReviewStatsSerializer,
)
from restaurants.models import Restaurant


class RestaurantReviewsView(generics.ListAPIView):
    """
    List all reviews for a restaurant
    """

    serializer_class = RestaurantReviewListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Reviews"],
        summary="List restaurant reviews",
        parameters=[
            OpenApiParameter(
                name="rating", type=int, description="Filter by rating (1-5)"
            ),
            OpenApiParameter(
                name="sort", type=str, description="Sort by: recent, highest, lowest"
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        restaurant_id = self.kwargs["restaurant_id"]
        queryset = (
            RestaurantReview.objects.filter(
                restaurant_id=restaurant_id, is_approved=True, is_hidden=False
            )
            .select_related("user")
            .prefetch_related("images")
        )

        # Filter by rating
        rating = self.request.query_params.get("rating")
        if rating:
            queryset = queryset.filter(overall_rating=rating)

        # Sort options
        sort = self.request.query_params.get("sort", "recent")
        if sort == "highest":
            queryset = queryset.order_by("-overall_rating", "-created_at")
        elif sort == "lowest":
            queryset = queryset.order_by("overall_rating", "-created_at")
        else:  # recent
            queryset = queryset.order_by("-created_at")

        return queryset


class RestaurantReviewStatsView(APIView):
    """
    Get review statistics for a restaurant
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Reviews"],
        summary="Get restaurant review statistics",
        responses={200: ReviewStatsSerializer},
    )
    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

        reviews = RestaurantReview.objects.filter(
            restaurant=restaurant, is_approved=True, is_hidden=False
        )

        # Calculate statistics
        stats = reviews.aggregate(
            average_rating=Avg("overall_rating"),
            total_reviews=Count("id"),
            avg_food_quality=Avg("food_quality_rating"),
            avg_packaging=Avg("packaging_rating"),
            avg_value=Avg("value_rating"),
        )

        # Rating distribution
        distribution = {}
        for i in range(1, 6):
            distribution[str(i)] = reviews.filter(overall_rating=i).count()

        stats["rating_distribution"] = distribution

        serializer = ReviewStatsSerializer(stats)
        return Response(serializer.data)


class CreateRestaurantReviewView(generics.CreateAPIView):
    """
    Create a review for a restaurant order
    """

    serializer_class = CreateRestaurantReviewSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Reviews"], summary="Create restaurant review")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DriverReviewsView(generics.ListAPIView):
    """
    List all reviews for a driver
    """

    serializer_class = DriverReviewListSerializer
    permission_classes = [AllowAny]

    @extend_schema(tags=["Reviews"], summary="List driver reviews")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        driver_id = self.kwargs["driver_id"]
        return (
            DriverReview.objects.filter(
                driver_id=driver_id, is_approved=True, is_hidden=False
            )
            .select_related("user")
            .order_by("-created_at")
        )


class DriverReviewStatsView(APIView):
    """
    Get review statistics for a driver
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Reviews"],
        summary="Get driver review statistics",
        responses={200: ReviewStatsSerializer},
    )
    def get(self, request, driver_id):
        reviews = DriverReview.objects.filter(
            driver_id=driver_id, is_approved=True, is_hidden=False
        )

        stats = reviews.aggregate(
            average_rating=Avg("overall_rating"),
            total_reviews=Count("id"),
        )

        # Rating distribution
        distribution = {}
        for i in range(1, 6):
            distribution[str(i)] = reviews.filter(overall_rating=i).count()

        stats["rating_distribution"] = distribution

        serializer = ReviewStatsSerializer(stats)
        return Response(serializer.data)


class CreateDriverReviewView(generics.CreateAPIView):
    """
    Create a review for a driver
    """

    serializer_class = CreateDriverReviewSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Reviews"], summary="Create driver review")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserReviewsView(generics.ListAPIView):
    """
    List all reviews by the current user
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Reviews"],
        summary="List user's reviews",
        parameters=[
            OpenApiParameter(
                name="type", type=str, description="Filter by type: restaurant, driver"
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        review_type = request.query_params.get("type", "all")

        data = {"restaurant_reviews": [], "driver_reviews": []}

        if review_type in ["all", "restaurant"]:
            restaurant_reviews = (
                RestaurantReview.objects.filter(user=request.user)
                .select_related("restaurant")
                .order_by("-created_at")
            )
            data["restaurant_reviews"] = RestaurantReviewDetailSerializer(
                restaurant_reviews, many=True, context={"request": request}
            ).data

        if review_type in ["all", "driver"]:
            driver_reviews = (
                DriverReview.objects.filter(user=request.user)
                .select_related("driver")
                .order_by("-created_at")
            )
            data["driver_reviews"] = DriverReviewDetailSerializer(
                driver_reviews, many=True, context={"request": request}
            ).data

        return Response(data)


class PendingReviewsView(APIView):
    """
    Get orders that haven't been reviewed yet
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Reviews"], summary="Get orders pending review")
    def get(self, request):
        from orders.models import Order

        # Orders that are delivered but not reviewed
        pending_restaurant_reviews = (
            Order.objects.filter(user=request.user, status="delivered")
            .exclude(restaurant_review__isnull=False)
            .select_related("restaurant")
            .order_by("-delivered_at")[:10]
        )

        pending_driver_reviews = (
            Order.objects.filter(
                user=request.user, status="delivered", driver__isnull=False
            )
            .exclude(driver_review__isnull=False)
            .select_related("driver")
            .order_by("-delivered_at")[:10]
        )

        return Response(
            {
                "pending_restaurant_reviews": [
                    {
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "restaurant_id": order.restaurant_id,
                        "restaurant_name": order.restaurant.name,
                        "delivered_at": order.delivered_at,
                    }
                    for order in pending_restaurant_reviews
                ],
                "pending_driver_reviews": [
                    {
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "driver_id": order.driver_id,
                        "driver_name": order.driver.full_name if order.driver else None,
                        "delivered_at": order.delivered_at,
                    }
                    for order in pending_driver_reviews
                ],
            }
        )

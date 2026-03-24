"""
Reviews Models - Restaurant and Driver Reviews
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from core.models import BaseModel


class RestaurantReview(BaseModel):
    """
    Review for a restaurant from an order
    """

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="restaurant_review"
    )
    restaurant = models.ForeignKey(
        "restaurants.Restaurant", on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurant_reviews",
    )

    # Ratings (1-5 stars)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    food_quality_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True
    )
    packaging_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True
    )
    value_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Value for money rating",
    )

    # Text review
    comment = models.TextField(blank=True, null=True)

    # Review images
    # Will be handled by ReviewImage model

    # Admin moderation
    is_approved = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False)

    # Restaurant response
    restaurant_response = models.TextField(blank=True, null=True)
    restaurant_response_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"Review by {self.user} for {self.restaurant} - {self.overall_rating}★"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update restaurant's cached rating
        self.update_restaurant_rating()

    def update_restaurant_rating(self):
        """Update restaurant's average rating and review count"""
        from restaurants.models import Restaurant

        stats = RestaurantReview.objects.filter(
            restaurant=self.restaurant, is_approved=True, is_hidden=False
        ).aggregate(avg_rating=Avg("overall_rating"), count=models.Count("id"))

        Restaurant.objects.filter(pk=self.restaurant_id).update(
            average_rating=stats["avg_rating"] or 0, total_reviews=stats["count"]
        )


class RestaurantReviewImage(BaseModel):
    """
    Images attached to a restaurant review
    """

    review = models.ForeignKey(
        RestaurantReview, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="reviews/restaurant/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.review}"


class DriverReview(BaseModel):
    """
    Review for a driver after delivery
    """

    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="driver_review"
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_driver_reviews",
    )

    # Ratings (1-5 stars)
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    # Text review
    comment = models.TextField(blank=True, null=True)

    # Admin moderation
    is_approved = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["driver", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]
        verbose_name = "تقييم السائق"  # ← مفرد
        verbose_name_plural = "تقييمات السائقين"  # ← جمع (يظهر بالسايدبار)

    def __str__(self):
        return (
            f"Review by {self.user} for Driver {self.driver} - {self.overall_rating}★"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update driver's cached rating
        self.update_driver_rating()

    def update_driver_rating(self):
        """Update driver's average rating (logged only, no User field to update)"""
        stats = DriverReview.objects.filter(
            driver=self.driver, is_approved=True, is_hidden=False
        ).aggregate(avg_rating=Avg("overall_rating"), count=models.Count("id"))

        # Note: User model doesn't have driver_rating/total_driver_reviews fields.
        # Stats are calculated on-the-fly via DriverReviewStatsView.
        # If you want cached stats, add these fields to User model first:
        #   driver_rating = models.DecimalField(...)
        #   total_driver_reviews = models.PositiveIntegerField(...)
        return stats

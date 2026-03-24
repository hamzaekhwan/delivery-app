"""
Core Serializers
"""

from rest_framework import serializers
from .models import Banner, AppConfiguration


class BannerSerializer(serializers.ModelSerializer):
    is_currently_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Banner
        fields = [
            "id",
            "title",
            "title_en",
            "subtitle",
            "subtitle_en",
            "image",
            "banner_type",
            "link",
            "is_active",
            "is_currently_active",
            "order",
        ]


class AppConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppConfiguration
        fields = [
            "base_delivery_fee",
            "free_delivery_threshold",
            "min_order_amount",
            "app_version",
            "maintenance_mode",
            "maintenance_message",
            "maintenance_message_en",
        ]

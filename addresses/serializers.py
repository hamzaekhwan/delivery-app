from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Address, Governorate, Area


class AddressSerializer(serializers.ModelSerializer):
    full_address = serializers.SerializerMethodField()
    governorate_name = serializers.CharField(source="governorate.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True)

    class Meta:
        model = Address
        fields = [
            "id",
            "title",
            "governorate",
            "governorate_name",
            "area",
            "area_name",
            "street",
            "building_number",
            "floor",
            "apartment",
            "landmark",
            "additional_notes",
            "latitude",
            "longitude",
            "is_current",
            "full_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    @extend_schema_field(str)
    def get_full_address(self, obj) -> str:
        return obj.full_address

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class AddressListSerializer(AddressSerializer):
    class Meta(AddressSerializer.Meta):
        pass


class SetCurrentAddressSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        user = self.context["request"].user
        if not Address.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("العنوان غير موجود")
        return value


class AreaSerializer(serializers.ModelSerializer):
    governorate_name = serializers.CharField(source="governorate.name", read_only=True)
    governorate_name_en = serializers.CharField(
        source="governorate.name_en", read_only=True
    )

    class Meta:
        model = Area
        fields = [
            "id",
            "name",
            "name_en",
            "slug",
            "governorate",
            "governorate_name",
            "governorate_name_en",
        ]


class GovernorateSerializer(serializers.ModelSerializer):
    areas = AreaSerializer(many=True, read_only=True)

    class Meta:
        model = Governorate
        fields = ["id", "name", "name_en", "slug", "areas"]

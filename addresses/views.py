from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiResponse,
    OpenApiParameter,
)
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from .models import Address, Area, Governorate
from .serializers import (
    AddressSerializer,
    AddressListSerializer,
    AreaSerializer,
    GovernorateSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List Addresses",
        description="Get all addresses for current user",
        tags=["Addresses"],
    ),
    create=extend_schema(
        summary="Create Address", description="Add a new address", tags=["Addresses"]
    ),
    retrieve=extend_schema(
        summary="Get Address", description="Get address details", tags=["Addresses"]
    ),
    update=extend_schema(
        summary="Update Address", description="Update address", tags=["Addresses"]
    ),
    partial_update=extend_schema(
        summary="Partial Update",
        description="Partially update address",
        tags=["Addresses"],
    ),
    destroy=extend_schema(
        summary="Delete Address", description="Delete address", tags=["Addresses"]
    ),
)
class AddressViewSet(viewsets.ModelViewSet):
    """ViewSet for addresses - Full CRUD"""

    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return AddressListSerializer
        return AddressSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Address added successfully",
                "data": AddressSerializer(address).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        address = serializer.save()

        return Response(
            {
                "success": True,
                "message": "Address updated successfully",
                "data": AddressSerializer(address).data,
            }
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        was_current = instance.is_current
        instance.delete()

        if was_current:
            next_address = Address.objects.filter(user=request.user).first()
            if next_address:
                next_address.is_current = True
                next_address.save()

        return Response(
            {"success": True, "message": "Address deleted successfully"},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Get Current Address",
        description="Get the current active address for orders",
        tags=["Addresses"],
        responses={
            200: OpenApiResponse(description="Current address"),
            404: OpenApiResponse(description="No current address"),
        },
    )
    @action(detail=False, methods=["get"])
    def current(self, request):
        address = Address.objects.filter(user=request.user, is_current=True).first()

        if not address:
            return Response(
                {"success": False, "message": "No current address"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"success": True, "data": AddressSerializer(address).data})

    @extend_schema(
        summary="Set as Current",
        description="Set address as current for orders",
        tags=["Addresses"],
        responses={200: OpenApiResponse(description="Address set as current")},
    )
    @action(detail=True, methods=["post"])
    def set_current(self, request, pk=None):
        address = self.get_object()
        address.is_current = True
        address.save()

        return Response(
            {
                "success": True,
                "message": "Address set as current",
                "data": AddressSerializer(address).data,
            }
        )


@extend_schema(
    summary="List Governorates",
    description="Get all governorates with their areas",
    tags=["Locations"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def list_governorates(request):
    governorates = Governorate.objects.prefetch_related("areas").all()
    serializer = GovernorateSerializer(governorates, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="List Areas",
    description="Get areas, optionally filtered by governorate",
    tags=["Locations"],
    parameters=[
        OpenApiParameter(
            name="governorate",
            description="Governorate ID",
            required=False,
            type=int,
        )
    ],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def list_areas(request):
    queryset = Area.objects.select_related("governorate")

    governorate_id = request.query_params.get("governorate")
    if governorate_id:
        queryset = queryset.filter(governorate_id=governorate_id)

    serializer = AreaSerializer(queryset, many=True)
    return Response(serializer.data)

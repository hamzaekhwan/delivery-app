"""
Restaurant API Views - ViewSets and Search
"""

from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, BooleanField, Case, When, Value, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from ..models import Restaurant, RestaurantCategory
from ..serializers import (
    RestaurantListSerializer,
    RestaurantDetailSerializer,
    RestaurantCategorySerializer,
)
from core.utils import calculate_distance, build_arabic_search_pattern
from .helpers import (
    LOCATION_PARAMS,
    get_user_coordinates,
    get_max_delivery_radius,
    filter_restaurants_by_distance,
    serialize_restaurants_with_distance,
    build_arabic_search_q,
)


# =============================================
# Category ViewSet
# =============================================


@extend_schema_view(
    list=extend_schema(
        summary="قائمة تصنيفات المطاعم",
        description="الحصول على جميع تصنيفات المطاعم النشطة",
        tags=["Restaurants"],
    ),
    retrieve=extend_schema(
        summary="تفاصيل تصنيف",
        description="الحصول على تفاصيل تصنيف معين",
        tags=["Restaurants"],
    ),
)
class RestaurantCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RestaurantCategory.objects.filter(is_active=True)
    serializer_class = RestaurantCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    @extend_schema(
        summary="مطاعم التصنيف",
        description="الحصول على جميع المطاعم ضمن تصنيف معين (مع فلترة بالموقع)",
        tags=["Restaurants"],
        parameters=LOCATION_PARAMS,
    )
    @action(detail=True, methods=["get"])
    def restaurants(self, request, slug=None):
        category = self.get_object()
        restaurants_qs = (
            Restaurant.objects.filter(categories=category, is_active=True)
            .select_related()
            .prefetch_related("categories")
        )

        user_lat, user_lng = get_user_coordinates(request)

        if user_lat is not None:
            items = filter_restaurants_by_distance(restaurants_qs, user_lat, user_lng)
            return Response(serialize_restaurants_with_distance(items, request))

        serializer = RestaurantListSerializer(
            restaurants_qs, many=True, context={"request": request}
        )
        return Response(serializer.data)


# =============================================
# Restaurant ViewSet
# =============================================


@extend_schema_view(
    list=extend_schema(
        summary="قائمة المطاعم",
        description="الحصول على جميع المطاعم مع إمكانية الفلترة والبحث والفلترة بالموقع",
        tags=["Restaurants"],
        parameters=LOCATION_PARAMS
        + [
            OpenApiParameter(
                name="type",
                description="نوع المتجر (food, grocery, pharmacy)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="category", description="معرف التصنيف", required=False, type=int
            ),
            OpenApiParameter(
                name="is_open",
                description="المطاعم المفتوحة فقط (حسب حقل is_open)",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="is_currently_open",
                description="المطاعم المفتوحة فعلياً الآن (is_open + ضمن ساعات العمل)",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="has_discount",
                description="المطاعم التي لديها خصم",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="search",
                description="البحث في اسم المطعم",
                required=False,
                type=str,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="تفاصيل مطعم",
        description="الحصول على تفاصيل مطعم معين",
        tags=["Restaurants"],
    ),
)
class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "restaurant_type",
        "categories",
        "is_open",
        "has_discount",
        "is_featured",
    ]
    ordering_fields = [
        "name",
        "average_rating",
        "total_orders",
        "delivery_fee",
        "created_at",
    ]
    ordering = ["-is_open", "-is_featured", "-has_discount", "-average_rating"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RestaurantDetailSerializer
        return RestaurantListSerializer

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related("categories")

        restaurant_type = self.request.query_params.get("type")
        if restaurant_type:
            queryset = queryset.filter(restaurant_type=restaurant_type)

        is_open = self.request.query_params.get("is_open")
        if is_open and is_open.lower() == "true":
            queryset = queryset.filter(is_open=True)

        # ---- فلترة المطاعم الجديدة (آخر 30 يوم) ----
        is_new = self.request.query_params.get("is_new")
        if is_new and is_new.lower() == "true":
            from datetime import timedelta

            thirty_days_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(created_at__gte=thirty_days_ago).order_by(
                "-created_at"
            )

        # ---- بحث عربي محسّن باستخدام regex ----
        search = self.request.query_params.get("search", "").strip()
        if search:
            q = build_arabic_search_q(
                search,
                [
                    "name",
                    "name_en",
                    "description",
                    "menu_categories__name",
                    "menu_categories__name_en",
                    "products__name",
                    "products__name_en",
                ],
            )
            queryset = queryset.filter(q).distinct()

        # ---- فلترة is_currently_open: مفتوح + ضمن ساعات العمل ----
        is_currently_open = self.request.query_params.get("is_currently_open")
        if is_currently_open and is_currently_open.lower() == "true":
            now = timezone.localtime().strftime("%H:%M")
            queryset = (
                queryset.filter(is_open=True)
                .annotate(
                    _is_currently_open=Case(
                        # حالة عادية: opening < closing (مثل 08:00 - 23:00)
                        When(
                            opening_time__lt=F("closing_time"),
                            opening_time__lte=now,
                            closing_time__gte=now,
                            then=Value(True),
                        ),
                        # حالة عبور منتصف الليل: opening >= closing (مثل 18:00 - 02:00)
                        When(
                            opening_time__gte=F("closing_time"),
                            then=Case(
                                When(opening_time__lte=now, then=Value(True)),
                                When(closing_time__gte=now, then=Value(True)),
                                default=Value(False),
                                output_field=BooleanField(),
                            ),
                        ),
                        default=Value(False),
                        output_field=BooleanField(),
                    )
                )
                .filter(_is_currently_open=True)
            )

        return queryset

    def list(self, request, *args, **kwargs):
        """Override list to support location-based filtering"""
        queryset = self.filter_queryset(self.get_queryset())
        user_lat, user_lng = get_user_coordinates(request)

        if user_lat is not None:
            items = filter_restaurants_by_distance(queryset, user_lat, user_lng)

            # Paginate manually
            page_size = 20
            page = int(request.query_params.get("page", 1))
            start = (page - 1) * page_size
            end = start + page_size
            paginated = items[start:end]

            return Response(
                {
                    "count": len(items),
                    "results": serialize_restaurants_with_distance(paginated, request),
                }
            )

        # Default behavior (no location)
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="المطاعم القريبة",
        description="المطاعم التي تغطي موقع المستخدم بالتوصيل",
        tags=["Restaurants"],
        parameters=[
            OpenApiParameter(
                name="lat", description="خط العرض", required=True, type=float
            ),
            OpenApiParameter(
                name="lng", description="خط الطول", required=True, type=float
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def nearby(self, request):
        """Get restaurants that can deliver to user's location"""
        user_lat, user_lng = get_user_coordinates(request)

        if user_lat is None:
            return Response(
                {"error": "lat and lng parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        restaurants_qs = (
            self.get_queryset()
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
        )

        items = filter_restaurants_by_distance(restaurants_qs, user_lat, user_lng)[:20]
        return Response(serialize_restaurants_with_distance(items, request))

    @extend_schema(
        summary="قائمة الطعام",
        description="الحصول على قائمة طعام المطعم",
        tags=["Restaurants"],
    )
    @action(detail=True, methods=["get"])
    def menu(self, request, slug=None):
        restaurant = self.get_object()

        from menu.models import MenuCategory
        from menu.serializers import MenuCategoryWithProductsSerializer

        categories = MenuCategory.objects.filter(
            restaurant=restaurant, is_active=True
        ).prefetch_related("products")

        serializer = MenuCategoryWithProductsSerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="تقييمات المطعم",
        description="الحصول على تقييمات المطعم",
        tags=["Restaurants"],
    )
    @action(detail=True, methods=["get"])
    def reviews(self, request, slug=None):
        restaurant = self.get_object()

        from reviews.models import RestaurantReview
        from reviews.serializers import RestaurantReviewSerializer

        reviews = RestaurantReview.objects.filter(restaurant=restaurant).select_related(
            "user", "order"
        )[:20]

        serializer = RestaurantReviewSerializer(reviews, many=True)
        return Response(
            {
                "average_rating": restaurant.average_rating,
                "total_reviews": restaurant.total_reviews,
                "reviews": serializer.data,
            }
        )


# =============================================
# Search View
# =============================================


@extend_schema(
    summary="البحث في المطاعم",
    description="البحث في المطاعم والمنتجات مع فلترة بالموقع",
    tags=["Restaurants"],
    parameters=LOCATION_PARAMS
    + [
        OpenApiParameter(name="q", description="كلمة البحث", required=True, type=str),
    ],
)
class RestaurantSearchView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = RestaurantListSerializer

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Restaurant.objects.none()

        pattern = build_arabic_search_pattern(query)

        return (
            Restaurant.objects.filter(
                Q(name__iregex=pattern)
                | Q(name_en__icontains=query)
                | Q(description__iregex=pattern),
                is_active=True,
            )
            .prefetch_related("categories")
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        pattern = build_arabic_search_pattern(query)
        user_lat, user_lng = get_user_coordinates(request)
        has_location = user_lat is not None

        # --- Restaurants ---
        restaurants_qs = self.get_queryset()

        if has_location:
            restaurant_items = filter_restaurants_by_distance(
                restaurants_qs, user_lat, user_lng
            )[:20]
            restaurants_data = serialize_restaurants_with_distance(
                restaurant_items, request
            )
        else:
            restaurants_data = RestaurantListSerializer(
                restaurants_qs[:20], many=True, context={"request": request}
            ).data

        # --- Products (filter by nearby restaurants) ---
        from menu.models import Product
        from menu.serializers import ProductListSerializer

        products_qs = Product.objects.filter(
            Q(name__iregex=pattern)
            | Q(name_en__icontains=query)
            | Q(description__iregex=pattern),
            is_available=True,
            restaurant__is_active=True,
        ).select_related("restaurant")

        if has_location:
            max_radius = get_max_delivery_radius()
            filtered_products = []
            for product in products_qs[:50]:
                r = product.restaurant
                if not r.latitude or not r.longitude:
                    continue
                distance = calculate_distance(
                    user_lat, user_lng, float(r.latitude), float(r.longitude)
                )
                if distance is not None and distance <= max_radius:
                    filtered_products.append(product)
                if len(filtered_products) >= 20:
                    break
            products_data = ProductListSerializer(filtered_products, many=True).data
        else:
            products_data = ProductListSerializer(products_qs[:20], many=True).data

        return Response(
            {
                "restaurants": restaurants_data,
                "products": products_data,
            }
        )


class RestaurantChoicesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from restaurants.models import Restaurant

        restaurants = Restaurant.objects.filter(is_active=True).values(
            "id", "name", "name_en"
        )
        return Response(list(restaurants))

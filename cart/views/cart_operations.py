"""
Cart Views - CRUD operations for cart and cart items
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Cart, CartItem, CartItemAddon, CART_MAX_PER_USER
from ..serializers import (
    CartSerializer,
    CartListSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
)


# ═══════════════════════════════════════════════════════════
#                    Helper Mixin
# ═══════════════════════════════════════════════════════════
class CartCleanupMixin:
    """
    Mixin to perform lazy cleanup before cart operations
    """

    def perform_cleanup(self, user):
        """Clean expired and empty carts"""
        Cart.objects.cleanup_expired(user)


# ═══════════════════════════════════════════════════════════
#                    List All Carts
# ═══════════════════════════════════════════════════════════
class CartListView(CartCleanupMixin, APIView):
    """
    Get all active carts for user
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="جلب جميع السلات",
        description="الحصول على جميع سلات المستخدم النشطة",
        tags=["Cart"],
        responses={200: CartListSerializer(many=True)},
    )
    def get(self, request):
        # Lazy cleanup first
        self.perform_cleanup(request.user)

        # Get all active carts
        carts = (
            Cart.objects.for_user(request.user)
            .select_related("restaurant", "coupon")
            .prefetch_related(
                "items__product", "items__variation", "items__cart_item_addons__addon"
            )
        )

        serializer = CartListSerializer(carts, many=True)
        return Response(
            {
                "carts": serializer.data,
                "count": carts.count(),
                "max_allowed": CART_MAX_PER_USER,
            }
        )


# ═══════════════════════════════════════════════════════════
#                    Single Cart View
# ═══════════════════════════════════════════════════════════
class CartView(CartCleanupMixin, APIView):
    """
    Get single cart by ID or by restaurant
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="الحصول على السلة",
        description="الحصول على سلة معينة بالمعرف أو بمعرف المطعم",
        tags=["Cart"],
        parameters=[
            OpenApiParameter(
                name="cart_id", description="معرف السلة", required=False, type=int
            ),
            OpenApiParameter(
                name="restaurant_id",
                description="معرف المطعم",
                required=False,
                type=int,
            ),
        ],
        responses={200: CartSerializer},
    )
    def get(self, request):
        # Lazy cleanup first
        self.perform_cleanup(request.user)

        cart_id = request.query_params.get("cart_id")
        restaurant_id = request.query_params.get("restaurant_id")

        if not cart_id and not restaurant_id:
            return Response(
                {"error": "يجب تحديد cart_id أو restaurant_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if cart_id:
                cart = Cart.objects.for_user(request.user).get(id=cart_id)
            else:
                cart = (
                    Cart.objects.for_user(request.user)
                    .filter(restaurant_id=restaurant_id)
                    .first()
                )

                if not cart:
                    return Response(
                        {"error": "لا توجد سلة لهذا المطعم"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CartSerializer(cart)
        return Response(serializer.data)


# ═══════════════════════════════════════════════════════════
#                    Add to Cart
# ═══════════════════════════════════════════════════════════
class AddToCartView(CartCleanupMixin, APIView):
    """
    Add item to cart (creates new cart if needed)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="إضافة للسلة",
        description="إضافة منتج إلى السلة (ينشئ سلة جديدة إذا لزم الأمر)",
        tags=["Cart"],
        request=AddToCartSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request):
        # Lazy cleanup first
        self.perform_cleanup(request.user)

        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        restaurant_id = data["restaurant_id"]
        product_id = data["product_id"]
        quantity = data["quantity"]
        variation_id = data.get("variation_id")
        addons = data.get("addons", [])
        special_instructions = data.get("special_instructions", "")

        # Get restaurant
        from restaurants.models import Restaurant

        restaurant = Restaurant.objects.get(id=restaurant_id)

        # Check if user has existing cart for this restaurant
        existing_cart = (
            Cart.objects.for_user(request.user).filter(restaurant=restaurant).first()
        )

        if existing_cart:
            cart = existing_cart
        else:
            # Check if user can create new cart
            if not Cart.can_create_cart(request.user):
                return Response(
                    {
                        "error": f"وصلت للحد الأقصى من السلات ({CART_MAX_PER_USER})",
                        "hint": "قم بإفراغ أو حذف سلة أخرى أولاً",
                        "max_carts": CART_MAX_PER_USER,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create new cart
            cart = Cart.objects.create(user=request.user, restaurant=restaurant)

        # Get product
        from menu.models import Product, ProductVariation, ProductAddon

        product = Product.objects.get(id=product_id)

        # Get variation if specified
        variation = None
        if variation_id:
            variation = ProductVariation.objects.get(id=variation_id)

        # Build addon set for comparison
        addon_set = frozenset(
            (addon_data.get("addon_id"), addon_data.get("quantity", 1))
            for addon_data in addons
        )

        # Check if same item already exists (same product + variation + addons)
        existing_item = None
        for item in cart.items.filter(product=product, variation=variation):
            item_addon_set = frozenset(
                (cia.addon_id, cia.quantity) for cia in item.cart_item_addons.all()
            )
            if item_addon_set == addon_set:
                existing_item = item
                break

        if existing_item:
            # Update quantity only
            existing_item.quantity += quantity
            existing_item.save(update_fields=["quantity"])
            cart_item = existing_item
        else:
            # Create new cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                variation=variation,
                quantity=quantity,
                special_instructions=special_instructions,
                price_snapshot=product.current_price
                + (variation.price_adjustment if variation else 0),
            )

            # Add addons
            for addon_data in addons:
                addon_id = addon_data.get("addon_id")
                addon_quantity = addon_data.get("quantity", 1)
                addon = ProductAddon.objects.get(id=addon_id)

                CartItemAddon.objects.create(
                    cart_item=cart_item, addon=addon, quantity=addon_quantity
                )

        # Refresh cart
        cart.refresh_from_db()
        return Response(CartSerializer(cart).data)


# ═══════════════════════════════════════════════════════════
#                    Update Cart Item
# ═══════════════════════════════════════════════════════════
class UpdateCartItemView(CartCleanupMixin, APIView):
    """
    Update cart item quantity
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="تحديث عنصر السلة",
        description="تحديث كمية عنصر في السلة",
        tags=["Cart"],
        request=UpdateCartItemSerializer,
        responses={200: CartSerializer},
    )
    def patch(self, request, item_id):
        self.perform_cleanup(request.user)

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cart_item = CartItem.objects.select_related("cart").get(
                id=item_id, cart__user=request.user, cart__expires_at__gt=timezone.now()
            )
        except CartItem.DoesNotExist:
            return Response(
                {"error": "العنصر غير موجود"}, status=status.HTTP_404_NOT_FOUND
            )

        quantity = serializer.validated_data["quantity"]

        if quantity == 0:
            cart = cart_item.cart
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            if "special_instructions" in serializer.validated_data:
                cart_item.special_instructions = serializer.validated_data[
                    "special_instructions"
                ]
            cart_item.save()
            cart = cart_item.cart

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data)

    @extend_schema(
        summary="حذف عنصر من السلة",
        description="حذف عنصر من السلة",
        tags=["Cart"],
        responses={200: CartSerializer},
    )
    def delete(self, request, item_id):
        self.perform_cleanup(request.user)

        try:
            cart_item = CartItem.objects.select_related("cart").get(
                id=item_id, cart__user=request.user, cart__expires_at__gt=timezone.now()
            )
        except CartItem.DoesNotExist:
            return Response(
                {"error": "العنصر غير موجود"}, status=status.HTTP_404_NOT_FOUND
            )

        cart = cart_item.cart
        cart_item.delete()

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data)


# ═══════════════════════════════════════════════════════════
#                    Clear/Delete Cart
# ═══════════════════════════════════════════════════════════
class ClearCartView(CartCleanupMixin, APIView):
    """
    Clear all items from cart or delete cart entirely
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="إفراغ السلة",
        description="حذف جميع العناصر من السلة",
        tags=["Cart"],
        parameters=[
            OpenApiParameter(
                name="cart_id", description="معرف السلة", required=True, type=int
            ),
        ],
    )
    def delete(self, request):
        self.perform_cleanup(request.user)

        cart_id = request.query_params.get("cart_id")

        if not cart_id:
            return Response(
                {"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart = Cart.objects.get(id=cart_id, user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND
            )

        # Delete the cart entirely
        cart.delete()
        return Response({"message": "تم حذف السلة"})


class ClearCartItemsView(CartCleanupMixin, APIView):
    """
    Clear all items but keep the cart
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="إفراغ محتوى السلة",
        description="حذف جميع العناصر مع الإبقاء على السلة",
        tags=["Cart"],
    )
    def delete(self, request, cart_id):
        self.perform_cleanup(request.user)

        try:
            cart = Cart.objects.get(id=cart_id, user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND
            )

        cart.clear()
        return Response({"message": "تم إفراغ السلة"})

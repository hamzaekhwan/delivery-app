"""
Menu Models - Menu categories, subcategories, products, and variations
"""

from django.db import models
from django.utils.text import slugify
from decimal import Decimal
from core.models import BaseModel
from core.constants import DiscountType
from core.utils import is_discount_active, calculate_discount


class MenuCategory(BaseModel):
    """
    Menu category within a restaurant (e.g., Burgers, Pizzas, Drinks)
    """

    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        related_name="menu_categories",
        verbose_name="المطعم",
    )
    name = models.CharField(max_length=100, verbose_name="الاسم")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(verbose_name="المعرف")
    description = models.TextField(blank=True, verbose_name="الوصف")
    description_en = models.TextField(blank=True, verbose_name="الوصف (إنجليزي)")
    image = models.ImageField(
        upload_to="menu/categories/", blank=True, null=True, verbose_name="الصورة"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "تصنيف قائمة"
        verbose_name_plural = "تصنيفات القائمة"
        ordering = ["order", "name"]
        unique_together = ["restaurant", "slug"]

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name_en or self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while (
                MenuCategory.objects.filter(restaurant=self.restaurant, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class MenuSubCategory(BaseModel):
    """
    Sub-category within a menu category
    """

    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name="subcategories",
        verbose_name="التصنيف",
    )
    name = models.CharField(max_length=100, verbose_name="الاسم")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(verbose_name="المعرف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "تصنيف فرعي"
        verbose_name_plural = "التصنيفات الفرعية"
        ordering = ["order", "name"]
        unique_together = ["category", "slug"]

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name_en or self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while (
                MenuSubCategory.objects.filter(category=self.category, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Product(BaseModel):
    """
    Product/Menu item
    """

    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="المطعم",
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="التصنيف",
    )
    subcategory = models.ForeignKey(
        MenuSubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="التصنيف الفرعي",
    )

    name = models.CharField(max_length=200, verbose_name="الاسم")
    name_en = models.CharField(
        max_length=200, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(verbose_name="المعرف")
    description = models.TextField(blank=True, verbose_name="الوصف")
    description_en = models.TextField(blank=True, verbose_name="الوصف (إنجليزي)")

    # Images
    image = models.ImageField(
        upload_to="menu/products/",
        verbose_name="الصورة",
        blank=True,
        null=True,
    )

    # Pricing
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="السعر الأساسي"
    )

    # Availability
    is_available = models.BooleanField(default=True, verbose_name="متوفر")

    # Discount
    has_discount = models.BooleanField(default=False, verbose_name="يوجد خصم")
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
        verbose_name="نوع الخصم",
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="قيمة الخصم"
    )
    discount_start = models.DateTimeField(
        null=True, blank=True, verbose_name="بداية الخصم"
    )
    discount_end = models.DateTimeField(
        null=True, blank=True, verbose_name="نهاية الخصم"
    )

    # Metadata
    calories = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="السعرات الحرارية"
    )
    preparation_time = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="وقت التحضير (دقيقة)"
    )

    # Ordering
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    is_featured = models.BooleanField(default=False, verbose_name="مميز")
    is_popular = models.BooleanField(default=False, verbose_name="شائع")

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"
        ordering = ["order", "-is_featured", "name"]
        unique_together = ["restaurant", "slug"]
        indexes = [
            models.Index(fields=["restaurant", "is_available"]),
            models.Index(fields=["category", "is_available"]),
            models.Index(fields=["is_featured"]),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name_en or self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while (
                Product.objects.filter(restaurant=self.restaurant, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_discount_active(self):
        """Check if product's own discount is currently active"""
        if not self.has_discount:
            return False
        return is_discount_active(self.discount_start, self.discount_end)

    @property
    def has_any_discount(self):
        """Check if any discount applies (product-level OR restaurant-level)"""
        if self.is_discount_active:
            return True
        return bool(self.restaurant.current_discount)

    @property
    def current_price(self):
        """
        Get current price after discount.
        Priority: product discount > restaurant discount > base price
        """
        # أولوية 1: خصم المنتج المباشر
        if self.is_discount_active:
            return calculate_discount(
                self.base_price, self.discount_type, self.discount_value
            )

        # أولوية 2: خصم المطعم (نسبة مئوية على كل المنتجات)
        restaurant_discount = self.restaurant.current_discount
        if restaurant_discount:
            from core.constants import DiscountType

            return calculate_discount(
                self.base_price, DiscountType.PERCENTAGE, restaurant_discount
            )

        return self.base_price

    @property
    def discount_amount(self):
        """Get discount amount from any source"""
        if self.has_any_discount:
            return self.base_price - self.current_price
        return Decimal("0")

    @property
    def effective_discount_source(self):
        """Return the source of the active discount (for display purposes)"""
        if self.is_discount_active:
            return "product"
        if self.restaurant.current_discount:
            return "restaurant"
        return None


class ProductVariation(BaseModel):
    """
    Product variation (e.g., size: Small, Medium, Large)
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variations",
        verbose_name="المنتج",
    )
    name = models.CharField(
        max_length=100, verbose_name="الاسم", help_text="مثال: صغير، وسط، كبير"
    )
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="تعديل السعر",
        help_text="يضاف إلى السعر الأساسي",
    )
    is_available = models.BooleanField(default=True, verbose_name="متوفر")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "تنويع منتج"
        verbose_name_plural = "تنويعات المنتج"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def total_price(self):
        """Get total price for this variation"""
        return self.product.current_price + self.price_adjustment


class ProductAddon(BaseModel):
    """
    Product addons (e.g., extra cheese, sauce)
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="addons", verbose_name="المنتج"
    )
    name = models.CharField(max_length=100, verbose_name="الاسم")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="السعر"
    )
    is_available = models.BooleanField(default=True, verbose_name="متوفر")
    max_quantity = models.PositiveIntegerField(default=5, verbose_name="الحد الأقصى")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "إضافة منتج"
        verbose_name_plural = "إضافات المنتج"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductImage(BaseModel):
    """
    Additional product images
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="المنتج"
    )
    image = models.ImageField(upload_to="menu/products/gallery/", verbose_name="الصورة")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "صورة منتج"
        verbose_name_plural = "صور المنتج"
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

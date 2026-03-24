# Cart Module - Multiple Carts Support

## 📋 ملخص التغييرات

### ما تم تعديله:
| الملف | التغيير |
|-------|---------|
| `models.py` | إزالة `unique_together`، إضافة `expires_at`، `CartManager` |
| `views.py` | Lazy Cleanup، endpoints جديدة، دعم سلات متعددة |
| `serializers.py` | `CartListSerializer`، حقول الصلاحية |
| `urls.py` | endpoints جديدة منظمة |
| `admin.py` | عرض حالة الصلاحية، actions جديدة |
| `migrations/` | migration للتغييرات |

---

## ⚙️ الإعدادات

أضف هذه الإعدادات في `settings.py`:

```python
# Cart Settings
CART_MAX_PER_USER = 5      # الحد الأقصى للسلات لكل مستخدم
CART_EXPIRY_HOURS = 48     # ساعات صلاحية السلة
```

---

## 🔗 API Endpoints

### 1. جلب جميع السلات
```http
GET /api/cart/all/
```

**Response:**
```json
{
    "carts": [
        {
            "id": 1,
            "restaurant_id": 10,
            "restaurant_name": "مطعم الشام",
            "restaurant_logo": "/media/restaurants/logo.jpg",
            "items_count": 3,
            "total": "45.00",
            "items_preview": [
                {"id": 1, "product_name": "شاورما", "quantity": 2, "total_price": "30.00"}
            ],
            "expires_at": "2024-01-17T15:30:00Z",
            "time_remaining_seconds": 86400
        }
    ],
    "count": 1,
    "max_allowed": 5
}
```

---

### 2. جلب سلة واحدة
```http
GET /api/cart/?cart_id=1
# أو
GET /api/cart/?restaurant_id=10
```

---

### 3. إضافة للسلة
```http
POST /api/cart/add/
Content-Type: application/json

{
    "restaurant_id": 10,
    "product_id": 5,
    "quantity": 2,
    "variation_id": null,
    "addons": [
        {"addon_id": 3, "quantity": 1}
    ],
    "special_instructions": "بدون بصل"
}
```

**Errors:**
```json
// إذا وصل للحد الأقصى
{
    "error": "وصلت للحد الأقصى من السلات (5)",
    "hint": "قم بإفراغ أو حذف سلة أخرى أولاً",
    "max_carts": 5
}
```

---

### 4. تحديث عنصر
```http
PATCH /api/cart/item/1/
Content-Type: application/json

{
    "quantity": 3,
    "special_instructions": "تعليمات جديدة"
}
```

---

### 5. حذف عنصر
```http
DELETE /api/cart/item/1/
```

---

### 6. حذف السلة بالكامل
```http
DELETE /api/cart/delete/?cart_id=1
```

---

### 7. إفراغ السلة (بدون حذفها)
```http
DELETE /api/cart/1/clear/
```

---

### 8. تطبيق كوبون
```http
POST /api/cart/1/coupon/
Content-Type: application/json

{
    "code": "SAVE20"
}
```

---

### 9. إزالة كوبون
```http
DELETE /api/cart/1/coupon/
```

---

### 10. التحقق من السلة
```http
GET /api/cart/validate/?cart_id=1
```

**Response:**
```json
{
    "valid": true,
    "errors": [],
    "cart": { ... }
}
```

---

### 11. اختيار سلة للدفع
```http
POST /api/cart/1/select/
```

**Response:**
```json
{
    "cart": { ... },
    "valid_for_checkout": true,
    "validation_errors": [],
    "price_breakdown": {
        "subtotal": "40.00",
        "delivery_fee": "5.00",
        "discount_amount": "0.00",
        "total": "45.00"
    }
}
```

---

## 🔄 Lazy Cleanup Flow

```
┌─────────────────────────────────────────────┐
│         أي Request على السلة                │
└──────────────────┬──────────────────────────┘
                   ▼
        ┌──────────────────────┐
        │   perform_cleanup()  │
        └──────────┬───────────┘
                   ▼
    ┌──────────────────────────────┐
    │  1. حذف السلات المنتهية      │
    │     expires_at < now()       │
    │                              │
    │  2. حذف السلات الفارغة       │
    │     items_count = 0          │
    └──────────────┬───────────────┘
                   ▼
        ┌──────────────────────┐
        │  تنفيذ العملية الأصلية │
        └──────────────────────┘
```

---

## 📱 Mobile App Integration

### سيناريو عرض السلات للمستخدم

```
1. المستخدم يفتح التطبيق
2. استدعاء GET /api/cart/all/
3. عرض قائمة السلات مع:
   - اسم المطعم + اللوجو
   - عدد العناصر
   - المجموع
   - الوقت المتبقي (countdown)
4. المستخدم يختار سلة
5. استدعاء POST /api/cart/{id}/select/
6. الانتقال لصفحة الدفع
```

### التعامل مع انتهاء الصلاحية

```javascript
// Frontend handling
if (cart.time_remaining_seconds < 3600) {
    showWarning("السلة ستنتهي خلال أقل من ساعة!");
}

if (cart.time_remaining_seconds <= 0 || cart.is_expired) {
    removeCartFromList(cart.id);
    showMessage("انتهت صلاحية السلة");
}
```

---

## ⚠️ ملاحظات مهمة

1. **الصلاحية تتجدد تلقائياً** عند أي نشاط على السلة (إضافة، تعديل، حذف عنصر)

2. **السلات الفارغة** تُحذف تلقائياً عند الـ cleanup

3. **الحد الأقصى 5 سلات** - يمكن تغييره من الإعدادات

4. **لا يُسمح بسلتين لنفس المطعم** - إذا كانت السلة موجودة، يُضاف للسلة الموجودة

5. **مقارنة العناصر** تشمل:
   - المنتج
   - التنويع (variation)
   - الإضافات (addons) وكمياتها

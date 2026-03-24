"""
Restaurant Import/Export Views - Admin Excel import and export
"""

import re
import urllib.parse
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import render

try:
    import openpyxl
except ImportError:
    raise ImportError("openpyxl is required. Run: pip install openpyxl")


# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------


def clean_price_str(raw) -> str:
    return str(raw).replace(",", "").replace("SYP", "").replace("syp", "").strip()


def is_price_range(raw) -> bool:
    if raw is None:
        return False
    s = clean_price_str(raw)
    parts = s.split("-")
    if len(parts) == 2:
        try:
            Decimal(parts[0].strip())
            Decimal(parts[1].strip())
            return True
        except InvalidOperation:
            pass
    return False


def parse_price(raw) -> Decimal:
    if raw is None:
        return Decimal("0")
    try:
        return Decimal(clean_price_str(raw))
    except InvalidOperation:
        return Decimal("0")


def split_price_range(raw):
    s = clean_price_str(raw)
    parts = s.split("-")
    return Decimal(parts[0].strip()), Decimal(parts[1].strip())


def read_excel_from_upload(uploaded_file):
    """Read uploaded Excel file and return list of dicts."""
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    raw_headers = rows[0]
    seen = {}
    headers = []
    for h in raw_headers:
        key = str(h).strip() if h is not None else "UNKNOWN"
        count = seen.get(key, 0)
        seen[key] = count + 1
        headers.append(f"{key}_{count}" if count > 0 else key)

    result = []
    for row in rows[1:]:
        if all(v is None for v in row):
            continue
        result.append(dict(zip(headers, row)))
    return result


# -----------------------------------------------------------------
# Views
# -----------------------------------------------------------------


@staff_member_required
def export_products_view(request):
    from restaurants.models import Restaurant
    from menu.models import Product
    import pandas as pd

    restaurant_id = request.GET.get("restaurant_id")

    if not restaurant_id:
        return HttpResponse("لم يتم اختيار مطعم", status=400)

    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return HttpResponse("المطعم غير موجود", status=404)

    products = (
        Product.objects.filter(restaurant=restaurant)
        .select_related("category", "subcategory")
        .order_by("category__name", "subcategory__name", "name")
    )

    rows = []
    for p in products:
        rows.append(
            {
                "id": p.id,
                "name-ar": p.name,
                "name-en": p.name_en or "",
                "price": p.base_price,
                "description-ar": p.description or "",
                "description-en": p.description_en or "",
                "sub category - ar": p.subcategory.name if p.subcategory else "",
                "sub category-en": p.subcategory.name_en if p.subcategory else "",
            }
        )

    df = pd.DataFrame(rows)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # اسم الملف بالعربي مع encoding صحيح
    safe_name = restaurant.name.strip()
    encoded_name = urllib.parse.quote(f"{safe_name}_products.xlsx")
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_name}"

    df.to_excel(response, index=False)
    return response


@staff_member_required
def import_products_view(request):
    from restaurants.models import Restaurant
    from menu.models import MenuCategory, MenuSubCategory, Product

    if request.method == "GET":
        restaurants = Restaurant.objects.all().order_by("name")
        return render(
            request,
            "admin/import_products.html",
            {
                "restaurants": restaurants,
            },
        )

    # POST - handle import
    try:
        uploaded_file = request.FILES.get("file")
        update_existing = request.POST.get("update_existing") == "on"
        dry_run = request.POST.get("dry_run") == "on"

        if not uploaded_file:
            return JsonResponse({"success": False, "error": "لم يتم رفع ملف"})

        if not uploaded_file.name.endswith((".xlsx", ".xls")):
            return JsonResponse(
                {"success": False, "error": "يجب أن يكون الملف بصيغة xlsx"}
            )

        # استخراج اسم المطعم من اسم الملف
        filename = uploaded_file.name
        restaurant_name = re.sub(r"_products\.(xlsx|xls)$", "", filename).strip()

        if not restaurant_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "اسم الملف غير صحيح، يجب أن يكون بصيغة: اسم_المطعم_products.xlsx",
                }
            )

        try:
            restaurant = Restaurant.objects.get(name__iexact=restaurant_name)
        except Restaurant.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"ما لقينا مطعم باسم '{restaurant_name}' — تأكد إن اسم الملف لم يتغير بعد التصدير",
                }
            )
        except Restaurant.MultipleObjectsReturned:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"في أكثر من مطعم باسم '{restaurant_name}'، تواصل مع المطور",
                }
            )

        # Read Excel
        items_rows = read_excel_from_upload(uploaded_file)
        if not items_rows:
            return JsonResponse(
                {"success": False, "error": "الملف فارغ أو لا يحتوي على بيانات"}
            )

        stats = {
            "products_created": 0,
            "products_updated": 0,
            "products_skipped": 0,
            "categories_created": 0,
            "subcategories_created": 0,
            "price_ranges_split": 0,
        }
        errors = []

        with transaction.atomic():
            menu_cat_cache = {}
            subcategory_cache = {}

            for row_num, item in enumerate(items_rows, start=2):
                name_item_en = str(item.get("name-en", "") or "").strip()
                name_item_ar = str(item.get("name-ar", "") or "").strip()
                price_raw = item.get("price")
                desc_en = str(item.get("description-en", "") or "").strip()
                desc_ar = str(item.get("description-ar", "") or "").strip()
                subcat_en = str(item.get("sub category-en", "") or "").strip()
                subcat_ar = str(item.get("sub category - ar", "") or "").strip()

                if not name_item_en and not name_item_ar:
                    stats["products_skipped"] += 1
                    continue

                product_name_ar = name_item_ar or name_item_en
                product_name_en = name_item_en

                # -- Price variants --
                if is_price_range(price_raw):
                    try:
                        price_small, price_large = split_price_range(price_raw)
                        price_variants = [
                            (
                                f"{product_name_ar} - صغير",
                                f"{product_name_en} - Small",
                                price_small,
                            ),
                            (
                                f"{product_name_ar} - كبير",
                                f"{product_name_en} - Large",
                                price_large,
                            ),
                        ]
                        stats["price_ranges_split"] += 1
                    except Exception:
                        errors.append(
                            f"سطر {row_num}: خطأ في تحليل السعر '{price_raw}'"
                        )
                        price_variants = [
                            (product_name_ar, product_name_en, Decimal("0")),
                        ]
                else:
                    price_variants = [
                        (product_name_ar, product_name_en, parse_price(price_raw)),
                    ]

                # -- Subcategory key --
                subcat_key = (subcat_en.lower() if subcat_en else "", subcat_ar)

                if dry_run:
                    if subcat_key not in menu_cat_cache:
                        menu_cat_cache[subcat_key] = True
                        stats["categories_created"] += 1
                    if (subcat_en or subcat_ar) and subcat_key not in subcategory_cache:
                        subcategory_cache[subcat_key] = True
                        stats["subcategories_created"] += 1
                    for p_name_ar, p_name_en, p_price in price_variants:
                        product_id = item.get("id")
                        exists = False
                        if product_id:
                            try:
                                exists = Product.objects.filter(
                                    id=int(product_id), restaurant=restaurant
                                ).exists()
                            except (ValueError, TypeError):
                                exists = False
                        if exists:
                            if update_existing:
                                stats["products_updated"] += 1
                            else:
                                stats["products_skipped"] += 1
                        else:
                            stats["products_created"] += 1
                    continue

                # -- MenuCategory --
                if subcat_key not in menu_cat_cache:
                    mc_name = subcat_ar or subcat_en or restaurant.name
                    mc_name_en = subcat_en or getattr(restaurant, "name_en", "")
                    menu_cat, mc_created = MenuCategory.objects.get_or_create(
                        restaurant=restaurant,
                        name=mc_name,
                        defaults={"name_en": mc_name_en},
                    )
                    if mc_created:
                        stats["categories_created"] += 1
                    menu_cat_cache[subcat_key] = menu_cat
                menu_cat = menu_cat_cache[subcat_key]

                # -- MenuSubCategory --
                subcategory = None
                if subcat_en or subcat_ar:
                    if subcat_key not in subcategory_cache:
                        subcat_obj, sc_created = MenuSubCategory.objects.get_or_create(
                            category=menu_cat,
                            name=subcat_ar or subcat_en,
                            defaults={"name_en": subcat_en},
                        )
                        if sc_created:
                            stats["subcategories_created"] += 1
                        subcategory_cache[subcat_key] = subcat_obj
                    subcategory = subcategory_cache[subcat_key]

                # -- Products --
                for p_name_ar, p_name_en, p_price in price_variants:
                    product_id = item.get("id")
                    existing = None

                    if product_id:
                        try:
                            existing = Product.objects.filter(
                                id=int(product_id), restaurant=restaurant
                            ).first()
                        except (ValueError, TypeError):
                            existing = None

                    if existing:
                        if update_existing:
                            existing.name = p_name_ar
                            existing.name_en = p_name_en
                            existing.base_price = p_price
                            existing.description = desc_ar
                            existing.description_en = desc_en
                            existing.category = menu_cat
                            existing.subcategory = subcategory
                            existing.save()
                            stats["products_updated"] += 1
                        else:
                            stats["products_skipped"] += 1
                    else:
                        # ID ما لقاه أو ما في ID → ينشئ جديد
                        Product.objects.create(
                            restaurant=restaurant,
                            category=menu_cat,
                            subcategory=subcategory,
                            name=p_name_ar,
                            name_en=p_name_en,
                            description=desc_ar,
                            description_en=desc_en,
                            base_price=p_price,
                        )
                        stats["products_created"] += 1

            if dry_run:
                transaction.set_rollback(True)

        return JsonResponse(
            {
                "success": True,
                "dry_run": dry_run,
                "stats": stats,
                "errors": errors,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

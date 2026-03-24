"""
Management command to import restaurants and menu items from Excel files.

Usage:
    python manage.py import_restaurants \
        --categories path/to/Categories.xlsx \
        --items-dir path/to/restaurant_items/

Optional flags:
    --clear     Delete existing restaurants before importing (default: False)
    --dry-run   Preview what will be imported without saving (default: False)

Price range logic:
    If price is "38000 - 61500", two products are created:
        - "اسم المنتج - صغير"  ->  38000
        - "اسم المنتج - كبير"  ->  61500

SubCategory logic:
    Each unique (sub category-en / sub category-ar) becomes both a MenuCategory
    and a MenuSubCategory under it. Products are linked to the correct subcategory.
"""

import os
import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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


def normalize_filename(name: str) -> str:
    return re.sub(r"[^0-9]", "", os.path.splitext(name)[0])


def read_excel(path: str):
    wb = openpyxl.load_workbook(path, data_only=True)
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
# Command
# -----------------------------------------------------------------


class Command(BaseCommand):
    help = "Import restaurants and menu items from Excel files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--categories", required=True, help="Path to Categories.xlsx"
        )
        parser.add_argument(
            "--items-dir",
            required=True,
            dest="items_dir",
            help="Directory containing per-restaurant xlsx files",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="Delete all existing restaurants before importing",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            dest="dry_run",
            help="Preview import without saving to database",
        )

    def handle(self, *args, **options):
        from restaurants.models import Restaurant, RestaurantCategory
        from menu.models import MenuCategory, MenuSubCategory, Product

        categories_path = options["categories"]
        items_dir = options["items_dir"]
        dry_run = options["dry_run"]
        do_clear = options["clear"]

        if not os.path.isfile(categories_path):
            raise CommandError(f"Categories file not found: {categories_path}")
        if not os.path.isdir(items_dir):
            raise CommandError(f"Items directory not found: {items_dir}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n  Reading Categories.xlsx..."))
        categories_rows = read_excel(categories_path)
        self.stdout.write(f"   Found {len(categories_rows)} restaurant entries\n")

        if do_clear and not dry_run:
            count, _ = Restaurant.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"   Deleted {count} existing restaurants\n")
            )

        stats = {
            "restaurants_created": 0,
            "restaurants_skipped": 0,
            "rest_categories_created": 0,
            "menu_categories_created": 0,
            "subcategories_created": 0,
            "products_created": 0,
            "products_skipped": 0,
            "price_ranges_split": 0,
            "files_missing": [],
        }

        with transaction.atomic():
            for row in categories_rows:
                restaurant_file = str(row.get("restaurant_number", "") or "").strip()
                name_en = str(row.get("name_en", "") or "").strip()
                name_ar = str(row.get("name_ar", "") or "").strip()
                category_en = str(row.get("category_en", "") or "").strip()
                category_ar = str(row.get("category_ar", "") or "").strip()
                opening_time = str(row.get("opening_time", "") or "").strip() or "08:00"
                closing_time = str(row.get("closing_time", "") or "").strip() or "23:00"
                delivery_duration = (
                    str(row.get("delivery_duration", "") or "").strip() or "30-45"
                )

                if not name_en and not name_ar:
                    continue

                self.stdout.write(
                    self.style.MIGRATE_HEADING(f"\n  Restaurant: {name_ar} ({name_en})")
                )

                # -- RestaurantCategory ------------------------------------------
                rest_category = None
                if category_en or category_ar:
                    cat_name = category_ar or category_en
                    cat_name_en = category_en.strip()
                    if not dry_run:
                        rest_category, cat_created = (
                            RestaurantCategory.objects.get_or_create(
                                name=cat_name,
                                defaults={"name_en": cat_name_en},
                            )
                        )
                        if cat_created:
                            stats["rest_categories_created"] += 1
                            self.stdout.write(f"   [+] RestaurantCategory: {cat_name}")
                        else:
                            self.stdout.write(
                                f"   [=] RestaurantCategory exists: {cat_name}"
                            )
                    else:
                        stats["rest_categories_created"] += 1
                        self.stdout.write(f"   [DRY] RestaurantCategory: {cat_name}")

                # -- Restaurant --------------------------------------------------
                restaurant = None
                if not dry_run:
                    restaurant, created = Restaurant.objects.get_or_create(
                        name=name_ar or name_en,
                        defaults={
                            "name_en": name_en,
                            "opening_time": opening_time,
                            "closing_time": closing_time,
                            "delivery_time_estimate": delivery_duration,
                            "address": "",
                        },
                    )
                    if created:
                        if rest_category:
                            restaurant.categories.add(rest_category)
                        stats["restaurants_created"] += 1
                        self.stdout.write(f"   [+] Restaurant created: {name_ar}")
                    else:
                        stats["restaurants_skipped"] += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"   [=] Restaurant already exists: {name_ar}"
                            )
                        )
                else:
                    stats["restaurants_created"] += 1
                    self.stdout.write(
                        f"   [DRY] Restaurant: {name_ar} | file: {restaurant_file}"
                    )

                # -- Find items file ---------------------------------------------
                file_num = normalize_filename(restaurant_file)
                items_file = None
                for fname in os.listdir(items_dir):
                    if normalize_filename(fname) == file_num:
                        items_file = os.path.join(items_dir, fname)
                        break

                if not items_file:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   [!] No items file found for {restaurant_file}"
                        )
                    )
                    stats["files_missing"].append(restaurant_file)
                    continue

                self.stdout.write(f"   [file] {os.path.basename(items_file)}")
                items_rows = read_excel(items_file)
                self.stdout.write(f"   [rows] {len(items_rows)} items")

                # Per-restaurant caches to avoid redundant DB queries
                menu_cat_cache = {}  # subcat_key -> MenuCategory
                subcategory_cache = {}  # subcat_key -> MenuSubCategory

                for item in items_rows:
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

                    # -- Prices: single or range ----------------------------------
                    if is_price_range(price_raw):
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
                    else:
                        price_variants = [
                            (product_name_ar, product_name_en, parse_price(price_raw)),
                        ]

                    # -- Subcategory key (unique identifier per subcat) -----------
                    subcat_key = (subcat_en.lower() if subcat_en else "", subcat_ar)

                    # -- DRY RUN -------------------------------------------------
                    if dry_run:
                        if subcat_key not in menu_cat_cache:
                            menu_cat_cache[subcat_key] = True
                            stats["menu_categories_created"] += 1
                        if (
                            subcat_en or subcat_ar
                        ) and subcat_key not in subcategory_cache:
                            subcategory_cache[subcat_key] = True
                            stats["subcategories_created"] += 1
                        for p_name_ar, p_name_en, p_price in price_variants:
                            self.stdout.write(
                                f"      [DRY] {p_name_ar} | {p_price} | cat: {subcat_ar or subcat_en}"
                            )
                            stats["products_created"] += 1
                        continue

                    # -- MenuCategory: one per unique subcategory -----------------
                    if subcat_key not in menu_cat_cache:
                        mc_name = subcat_ar or subcat_en or (name_ar or name_en)
                        mc_name_en = subcat_en or name_en
                        menu_cat, mc_created = MenuCategory.objects.get_or_create(
                            restaurant=restaurant,
                            name=mc_name,
                            defaults={"name_en": mc_name_en},
                        )
                        if mc_created:
                            stats["menu_categories_created"] += 1
                        menu_cat_cache[subcat_key] = menu_cat
                    menu_cat = menu_cat_cache[subcat_key]

                    # -- MenuSubCategory: one per unique subcategory ---------------
                    subcategory = None
                    if subcat_en or subcat_ar:
                        if subcat_key not in subcategory_cache:
                            subcat_obj, sc_created = (
                                MenuSubCategory.objects.get_or_create(
                                    category=menu_cat,
                                    name=subcat_ar or subcat_en,
                                    defaults={"name_en": subcat_en},
                                )
                            )
                            if sc_created:
                                stats["subcategories_created"] += 1
                            subcategory_cache[subcat_key] = subcat_obj
                        subcategory = subcategory_cache[subcat_key]

                    # -- Products (1 or 2 per row) ---------------------------------
                    for p_name_ar, p_name_en, p_price in price_variants:
                        if not Product.objects.filter(
                            restaurant=restaurant, name=p_name_ar
                        ).exists():
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
                        else:
                            stats["products_skipped"] += 1

            if dry_run:
                self.stdout.write(
                    self.style.WARNING("\n  DRY RUN - no changes saved to database.\n")
                )
                transaction.set_rollback(True)

        # -- Summary ---------------------------------------------------------
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 52))
        self.stdout.write(self.style.SUCCESS("  Import complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 52))
        self.stdout.write(
            f"  Restaurants created       : {stats['restaurants_created']}"
        )
        self.stdout.write(
            f"  Restaurants skipped       : {stats['restaurants_skipped']}"
        )
        self.stdout.write(
            f"  RestaurantCategories      : {stats['rest_categories_created']}"
        )
        self.stdout.write(
            f"  MenuCategories created    : {stats['menu_categories_created']}"
        )
        self.stdout.write(
            f"  SubCategories created     : {stats['subcategories_created']}"
        )
        self.stdout.write(f"  Products created          : {stats['products_created']}")
        self.stdout.write(f"  Products skipped          : {stats['products_skipped']}")
        self.stdout.write(
            f"  Price ranges split (x2)   : {stats['price_ranges_split']}"
        )
        if stats["files_missing"]:
            self.stdout.write(
                self.style.WARNING(
                    f"  Missing files             : {', '.join(stats['files_missing'])}"
                )
            )
        self.stdout.write("=" * 52 + "\n")

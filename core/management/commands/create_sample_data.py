"""
Management command to create sample data for testing the delivery app.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates sample data for testing the delivery app'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Import models
        from addresses.models import Governorate, Area
        from restaurants.models import RestaurantCategory, Restaurant, RestaurantWorkingHours
        from menu.models import MenuCategory, Product, ProductVariation, ProductAddon
        from core.models import Banner, AppConfiguration
        from coupons.models import Coupon
        
        # Create Governorates
        self.stdout.write('Creating governorates and areas...')
        governorates_data = [
            ('Cairo', ['Nasr City', 'Maadi', 'Heliopolis', 'New Cairo', 'Downtown']),
            ('Giza', ['Dokki', 'Mohandessin', '6th of October', 'Sheikh Zayed', 'Haram']),
            ('Alexandria', ['Smouha', 'Miami', 'Montazah', 'Stanley', 'Sidi Gaber']),
        ]
        
        governorates = {}
        for gov_name, areas in governorates_data:
            gov, _ = Governorate.objects.get_or_create(
                slug=slugify(gov_name),
                defaults={'name': gov_name}
            )
            governorates[gov_name] = gov
            for area_name in areas:
                Area.objects.get_or_create(
                    slug=slugify(area_name),
                    governorate=gov,
                    defaults={'name': area_name}
                )
        
        # Create Restaurant Categories
        self.stdout.write('Creating restaurant categories...')
        categories_data = [
            ('Fast Food', 'fastfood', 1),
            ('Oriental', 'oriental', 2),
            ('Seafood', 'seafood', 3),
            ('Italian', 'italian', 4),
            ('Asian', 'asian', 5),
            ('Healthy', 'healthy', 6),
            ('Desserts', 'desserts', 7),
            ('Coffee', 'coffee', 8),
        ]
        
        categories = {}
        for name, slug, order in categories_data:
            cat, _ = RestaurantCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'name_en': name,
                    'is_active': True,
                    'order': order
                }
            )
            categories[slug] = cat
        
        # Create test users
        self.stdout.write('Creating test users...')
        customer, _ = User.objects.get_or_create(
            phone_number='+201111111111',
            defaults={
                'first_name': 'Test',
                'last_name': 'Customer',
                'role': 'customer',
                'is_active': True,
                'governorate': 'cairo'  # Using string value from Governorate choices
            }
        )
        customer.set_password('test123')
        customer.save()
        
        driver, _ = User.objects.get_or_create(
            phone_number='+201222222222',
            defaults={
                'first_name': 'Test',
                'last_name': 'Driver',
                'role': 'driver',
                'is_active': True,
                'governorate': 'cairo'  # Using string value from Governorate choices
            }
        )
        driver.set_password('test123')
        driver.save()
        
        # Create Restaurants
        self.stdout.write('Creating restaurants...')
        restaurants_data = [
            ('Burger King', 'fastfood', 30.0456, 31.2357),
            ('Pizza Hut', 'fastfood', 30.0489, 31.2390),
            ('Zooba', 'oriental', 30.0523, 31.2412),
            ('Felfela', 'oriental', 30.0445, 31.2378),
            ('Fish Market', 'seafood', 30.0512, 31.2401),
            ('Il Mulino', 'italian', 30.0478, 31.2356),
            ('Noodles House', 'asian', 30.0534, 31.2423),
            ('Salad Bar', 'healthy', 30.0501, 31.2389),
            ('Sweet Spot', 'desserts', 30.0567, 31.2445),
            ('Coffee Corner', 'coffee', 30.0489, 31.2367),
        ]
        
        restaurants = {}
        for name, cat_slug, lat, lng in restaurants_data:
            rest, created = Restaurant.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'name': name,
                    'name_en': name,
                    'category': categories[cat_slug],
                    'description': f'Best {cat_slug} in town!',
                    'address': f'123 Main Street, Cairo',
                    'latitude': Decimal(str(lat)),
                    'longitude': Decimal(str(lng)),
                    'phone': f'+20100{random.randint(1000000, 9999999)}',
                    'minimum_order_amount': Decimal(random.choice(['50.00', '75.00', '100.00'])),
                    'delivery_fee': Decimal(random.choice(['10.00', '15.00', '20.00'])),
                    'delivery_time_estimate': f'{random.randint(20, 30)}-{random.randint(35, 50)}',
                    'is_active': True,
                    'is_open': True,
                    'is_featured': random.choice([True, False]),
                    'average_rating': Decimal(str(round(random.uniform(3.5, 5.0), 1))),
                    'total_reviews': random.randint(50, 500),
                    'total_orders': random.randint(100, 1000),
                    'opening_time': '09:00',
                    'closing_time': '23:00',
                    'logo': '',  # No image for now
                }
            )
            restaurants[name] = rest
            
            # Create working hours
            if created:
                for day in range(7):
                    RestaurantWorkingHours.objects.get_or_create(
                        restaurant=rest,
                        day=day,
                        defaults={
                            'opening_time': '09:00',
                            'closing_time': '23:00',
                            'is_closed': False
                        }
                    )
        
        # Create Menu Items for each restaurant
        self.stdout.write('Creating menu items...')
        menu_items = {
            'fastfood': [
                ('Burgers', [
                    ('Classic Burger', 65.00, 'Beef patty with lettuce, tomato, and special sauce'),
                    ('Cheese Burger', 75.00, 'Classic burger with melted cheddar'),
                    ('Double Burger', 95.00, 'Two beef patties with all toppings'),
                ]),
                ('Sides', [
                    ('French Fries', 25.00, 'Crispy golden fries'),
                    ('Onion Rings', 30.00, 'Battered onion rings'),
                    ('Chicken Wings', 55.00, '6 pieces buffalo wings'),
                ]),
            ],
            'oriental': [
                ('Main Dishes', [
                    ('Koshary', 35.00, 'Egyptian classic with rice, pasta, and lentils'),
                    ('Fattah', 85.00, 'Rice with meat and crispy bread'),
                    ('Molokhia', 65.00, 'Green soup with rice and chicken'),
                ]),
                ('Sandwiches', [
                    ('Falafel Sandwich', 20.00, 'Fresh falafel in pita bread'),
                    ('Shawarma', 40.00, 'Grilled meat with garlic sauce'),
                ]),
            ],
            'italian': [
                ('Pasta', [
                    ('Spaghetti Bolognese', 75.00, 'Classic meat sauce pasta'),
                    ('Fettuccine Alfredo', 85.00, 'Creamy parmesan sauce'),
                    ('Penne Arrabiata', 65.00, 'Spicy tomato sauce'),
                ]),
                ('Pizza', [
                    ('Margherita', 95.00, 'Tomato, mozzarella, and basil'),
                    ('Pepperoni', 115.00, 'Loaded with pepperoni slices'),
                    ('Four Cheese', 125.00, 'Mozzarella, gorgonzola, parmesan, ricotta'),
                ]),
            ],
        }
        
        for rest_name, rest in restaurants.items():
            cat_slug = rest.category.slug if rest.category else None
            if cat_slug in menu_items:
                for cat_name, products in menu_items[cat_slug]:
                    menu_cat, _ = MenuCategory.objects.get_or_create(
                        restaurant=rest,
                        name=cat_name,
                        defaults={'name_en': cat_name, 'is_active': True}
                    )
                    for prod_name, price, desc in products:
                        product, _ = Product.objects.get_or_create(
                            restaurant=rest,
                            name=prod_name,
                            defaults={
                                'name_en': prod_name,
                                'category': menu_cat,
                                'description': desc,
                                'base_price': Decimal(str(price)),
                                'is_available': True,
                                'is_featured': random.choice([True, False]),
                                'preparation_time': random.randint(10, 30),
                            }
                        )
                        
                        # Add variations for some products
                        if 'Burger' in prod_name or 'Pizza' in prod_name:
                            for size, multiplier in [('Small', 0.8), ('Medium', 1.0), ('Large', 1.3)]:
                                ProductVariation.objects.get_or_create(
                                    product=product,
                                    name=size,
                                    defaults={
                                        'name_en': size,
                                        'price_adjustment': Decimal(str(round(price * multiplier - price, 2)))
                                    }
                                )
                        
                        # Add addons
                        if 'Burger' in prod_name:
                            for addon_name, addon_price in [('Extra Cheese', 10), ('Bacon', 15), ('Jalapeños', 5)]:
                                ProductAddon.objects.get_or_create(
                                    product=product,
                                    name=addon_name,
                                    defaults={
                                        'name_en': addon_name,
                                        'price': Decimal(str(addon_price))
                                    }
                                )
        
        # Create Banners
        self.stdout.write('Creating banners...')
        Banner.objects.get_or_create(
            title='Welcome Offer',
            defaults={
                'subtitle': 'Get 20% off your first order!',
                'is_active': True,
                'order': 1
            }
        )
        Banner.objects.get_or_create(
            title='Free Delivery',
            defaults={
                'subtitle': 'Free delivery on orders above 200 EGP',
                'is_active': True,
                'order': 2
            }
        )
        
        # Create Coupons
        self.stdout.write('Creating coupons...')
        from django.utils import timezone
        from datetime import timedelta
        
        Coupon.objects.get_or_create(
            code='WELCOME20',
            defaults={
                'discount_type': 'percentage',
                'discount_value': Decimal('20.00'),
                'minimum_order_amount': Decimal('100.00'),
                'max_discount': Decimal('50.00'),
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30),
                'usage_limit': 1000,
                'usage_limit_per_user': 1,
                'is_active': True,
                'first_order_only': True,
            }
        )
        Coupon.objects.get_or_create(
            code='SAVE10',
            defaults={
                'discount_type': 'fixed',
                'discount_value': Decimal('10.00'),
                'minimum_order_amount': Decimal('50.00'),
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=60),
                'usage_limit': 500,
                'is_active': True,
            }
        )
        
        # Create App Configuration (singleton)
        self.stdout.write('Creating app configuration...')
        config, created = AppConfiguration.objects.get_or_create(
            pk=1,
            defaults={
                'base_delivery_fee': Decimal('15.00'),
                'free_delivery_threshold': Decimal('200.00'),
                'min_order_amount': Decimal('50.00'),
                'driver_search_radius_km': Decimal('10.00'),
                'driver_accept_timeout_seconds': 60,
                'app_version': '1.0.0',
                'maintenance_mode': False,
            }
        )
        if created:
            self.stdout.write('  App configuration created')
        else:
            self.stdout.write('  App configuration already exists')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Test accounts:')
        self.stdout.write(f'  Admin: +201234567890 / admin123')
        self.stdout.write(f'  Customer: +201111111111 / test123')
        self.stdout.write(f'  Driver: +201222222222 / test123')

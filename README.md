# Delivery App

A production-ready food delivery platform API built with Django REST Framework. Supports multi-role authentication, real-time order tracking, driver logistics, push notifications, and containerized deployment.

## Tech Stack

- **Backend:** Django 5.2, Django REST Framework
- **Database:** PostgreSQL 17
- **Cache & Broker:** Redis 7
- **Task Queue:** Celery + Celery Beat
- **Auth:** JWT (SimpleJWT) + Phone OTP
- **Notifications:** Firebase Cloud Messaging (FCM)
- **OTP Delivery:** WhatsApp (Green API) / SMS (Aman Gate)
- **Admin Dashboard:** Django Jazzmin (modern Bootstrap admin theme)
- **API Docs:** OpenAPI 3.0 (Swagger UI & ReDoc)
- **Deployment:** Docker Compose, Gunicorn, Caddy (auto-HTTPS)

## Features

### Authentication & Users
- Phone number signup with OTP verification
- Role-based access control (User, Driver, Admin)
- JWT authentication with token refresh & blacklisting
- Password reset via OTP
- Multi-language support (Arabic / English)

### Restaurants & Menu
- Multi-type stores: Food, Grocery, Pharmacy, Sweets, Bakery, Coffee
- Menu categories, sub-categories, products with variations & add-ons
- Product discount system (percentage / fixed)
- Restaurant availability & working hours

### Shopping Cart
- Multiple carts per user (one per restaurant)
- Auto-expiry with lazy cleanup
- Coupon application & validation

### Orders
- Full lifecycle: Placed > Confirmed > Preparing > Picked Up > Delivered
- Manual order creation by admin (phone/chat orders)
- Price snapshots at order time
- Price-pending mode (driver sets final price on pickup)
- Order cancellation & reorder
- Delivery reports with image uploads

### Driver System
- Online/offline status with session tracking
- Daily, weekly, monthly work statistics
- Order request accept/reject flow
- Delivery report submission

### Payments
- Multiple methods: Cash, Card, Wallet
- Payment status tracking & retry
- Wallet with top-up & transaction history

### Coupons
- Percentage, fixed amount, and free delivery types
- Per-user & total usage limits
- Date range validity & minimum order requirements

### Admin Dashboard (Jazzmin)
- Modern, responsive admin panel with Bootstrap UI
- Custom dashboard for managing orders, restaurants, users & drivers
- Role-based admin views and filters

### Reviews
- Restaurant & driver ratings (1-5 stars)
- Review moderation & restaurant responses

### Notifications
- Firebase FCM push notifications (Android, iOS, Web)
- In-app notification center
- Admin broadcast messages
- Device token management

## Project Structure

```
delivery_app/
├── config/                     # Project configuration
│   ├── django/                 # Base, production & test settings
│   ├── settings/               # Modular settings (DB, JWT, CORS, Firebase, etc.)
│   ├── celery.py
│   └── urls.py
├── accounts/                   # Auth, users, drivers, OTP
├── addresses/                  # Delivery addresses & locations
├── restaurants/                # Restaurant catalog & categories
├── menu/                       # Menu categories, products, variations, add-ons
├── cart/                       # Shopping cart management
├── orders/                     # Order lifecycle & driver assignment
├── payments/                   # Payment processing & wallet
├── coupons/                    # Discount coupons
├── reviews/                    # Restaurant & driver reviews
├── notifications/              # Push & in-app notifications
├── home/                       # Homepage data & search
├── core/                       # Base models, constants, utilities
├── deploy/                     # Docker, Caddy, Redis configs
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── caddy/
│   └── redis/
└── requirements.txt
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup/` | Register new user |
| POST | `/api/auth/verify-otp/` | Verify OTP code |
| POST | `/api/auth/login/` | Login with phone & password |
| POST | `/api/auth/logout/` | Blacklist refresh token |
| POST | `/api/auth/forgot-password/` | Request password reset OTP |
| POST | `/api/auth/reset-password/` | Reset password with OTP |
| GET/PUT | `/api/auth/profile/` | View / update profile |

### Restaurants & Menu
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/restaurants/` | List restaurants (filtered) |
| GET | `/api/restaurants/{id}/` | Restaurant detail with menu |
| GET | `/api/menu/categories/` | Menu categories |
| GET | `/api/menu/products/` | Products (filtered) |
| GET | `/api/menu/products/{id}/` | Product with variations & add-ons |

### Cart
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cart/all/` | List all user carts |
| POST | `/api/cart/add/` | Add item to cart |
| PATCH | `/api/cart/item/{id}/` | Update item quantity |
| DELETE | `/api/cart/item/{id}/` | Remove item |
| POST | `/api/cart/{id}/coupon/` | Apply coupon |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orders/create/` | Create order |
| POST | `/api/orders/{id}/place/` | Place order |
| POST | `/api/orders/{id}/cancel/` | Cancel order |
| POST | `/api/orders/{id}/reorder/` | Reorder previous order |
| GET | `/api/orders/` | List user orders |

### Driver Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/driver/pending/` | Pending order requests |
| POST | `/api/orders/driver/request/{id}/accept/` | Accept order |
| PATCH | `/api/orders/driver/{id}/status/` | Update order status |
| POST | `/api/orders/driver/{id}/delivery-report/` | Submit delivery report |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | List notifications |
| POST | `/api/notifications/{id}/read/` | Mark as read |
| POST | `/api/notifications/devices/register/` | Register FCM token |

### API Documentation
| Endpoint | Description |
|----------|-------------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI 3.0 schema |

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 17
- Redis 7

### Local Development

```bash
# Clone & setup
git clone https://github.com/hamzaekhwan/delivery-app.git
cd delivery-app
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Run migrations & create admin
python manage.py migrate
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

### Docker Deployment

```bash
# Configure environment
cp .env.example .env

# Start all services
docker compose -f deploy/docker-compose.yml up -d

# Create admin user
docker compose -f deploy/docker-compose.yml exec web python manage.py createsuperuser
```

**Services:** PostgreSQL, Redis, Django/Gunicorn, Celery Worker, Celery Beat, Caddy (reverse proxy with auto-HTTPS)

## Architecture

- **Modular settings** — split into `db.py`, `jwt.py`, `cors.py`, `firebase.py`, etc.
- **Service layer** — business logic separated from views (`services.py`, `selectors.py`)
- **Async tasks** — notifications and background jobs via Celery
- **Signal-driven** — automatic actions on order status changes
- **Snapshot pattern** — orders store restaurant/address/item data at creation time

## License

MIT

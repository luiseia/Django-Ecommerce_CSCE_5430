# ShopProject — Django Online Commercial Shopping Website

A full-featured e-commerce platform built with Django 5.2 LTS featuring a **custom User model with email-based authentication** and **three roles** (Shopper, Merchant, Administrator).

## Features

### Custom User Model (`accounts.User`)
- **Email login** — `USERNAME_FIELD = "email"` with a custom `EmailBackend`
- **Three roles** via `TextChoices`: Shopper, Merchant, Administrator
- **Profile fields**: first/last name, phone number, date of birth, avatar
- **Order history** accessible via `user.get_order_history()` (reverse FK from `Order`)
- **Proxy models** (`Shopper`, `Merchant`, `Administrator`) for role-specific admin views and querysets
- **Role-based decorators** (`@shopper_required`, `@merchant_required`, `@administrator_required`)
- **Template tag** `{% if user|has_role:'MERCHANT' %}` for conditional rendering

### Apps
| App | Purpose |
|------|---------|
| `accounts` | Custom User, registration, login, profile, merchant dashboard |
| `products` | Product catalog with categories, search, and merchant ownership |
| `orders` | Order placement, order items (price snapshots), status tracking |
| `cart` | Session cart with add/remove/checkout flow |

### Additional
- Bootstrap 5 responsive templates with role-aware navigation
- Django admin configured for all models (proxy model admin for each role)
- Cart item count in every page via context processor

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py makemigrations accounts products orders cart
python manage.py migrate

# 4. Create a superuser (Administrator role)
python manage.py createsuperuser

# 5. Run the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the storefront and `http://127.0.0.1:8000/admin/` for the admin panel.

## Project Structure

```
shop_project/
├── config/              # Project settings, root URLs, WSGI/ASGI
├── accounts/            # Custom User model, auth, profiles
│   ├── models.py        # User + Shopper/Merchant/Administrator proxies
│   ├── backends.py      # EmailBackend
│   ├── decorators.py    # @role_required, @merchant_required, etc.
│   ├── forms.py         # Registration, login, profile forms
│   ├── views.py         # Register, login, profile, merchant dashboard
│   └── templatetags/    # account_tags (has_role filter)
├── products/            # Product & Category models, views
├── orders/              # Order & OrderItem models, history views
├── cart/                # Cart model, add/remove/checkout
├── templates/           # All HTML templates (Bootstrap 5)
├── static/              # CSS, JS, images
├── requirements.txt
└── manage.py
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
python manage.py runserver                      # start dev server
python manage.py makemigrations <app>           # generate migrations (per app — no global makemigrations in README)
python manage.py migrate
python manage.py createsuperuser                # creates an ADMINISTRATOR role user
python manage.py seed_products                  # populate demo categories/products
python manage.py test                           # run all tests
python manage.py test orders.test_return_review_report   # run one test module
python manage.py test products.tests_validation.ProductValidationTests.test_name_required  # single test
```

Note: test modules do NOT all follow the default `tests.py` convention. `orders/test_return_review_report.py` and `products/tests_validation.py` use custom names and must be targeted explicitly (or discovered via `python manage.py test <app>`).

Dependencies: `Django>=5.2,<5.3`, `django-crispy-forms`, `crispy-bootstrap5`, `Pillow`. SQLite is the default DB (`db.sqlite3`).

## Architecture

### Apps and responsibilities
| App | Purpose |
|---|---|
| `config/` | settings, root URL conf (all apps are mounted here), WSGI/ASGI |
| `accounts/` | custom `User`, email auth, face login, profiles, merchant dashboard |
| `products/` | `Product`, `Category`, `Inventory` (separate OneToOne model), `Review` |
| `orders/` | `Order`, `OrderItem` (price snapshots), `ReturnRequest` |
| `cart/` | `Cart`, `CartItem` (DB-backed, one cart per user) |
| `bookmarks/` | `Bookmark` (user ↔ product favorites) |
| `recommendations/` | view-tracking + scoring service with popular-product fallback |
| `reports/` | `MerchantReport` (user-submitted complaints against merchants) |

### Custom auth — critical to understand
- `AUTH_USER_MODEL = "accounts.User"` with `USERNAME_FIELD = "email"`.
- Authentication goes through `accounts.backends.EmailBackend` (not Django's default).
- Roles live on a single `role` CharField on `User` with three `TextChoices`: `SHOPPER`, `MERCHANT`, `ADMIN`. Helper properties `is_shopper` / `is_merchant` / `is_administrator`.
- Proxy models `Shopper`, `Merchant`, `Administrator` exist mainly for role-scoped admin views; their `save()` forces the role, so saving through a proxy rewrites `role`.
- Role gating uses `accounts.decorators` — `@shopper_required`, `@merchant_required`, `@administrator_required`. These raise `PermissionDenied`, they do NOT redirect; stack `@login_required` above them.
- Template filter `{% if user|has_role:'MERCHANT' %}` (from `accounts.templatetags.account_tags`).
- Two login modes at `/accounts/login/`: password+captcha, and face login (email + face descriptor stored on `accounts.FaceCredential`). Face login requires pre-enrollment at `/accounts/face-enroll/` and face-api.js model files under `static/faceapi/models/`. Threshold controlled by `FACE_LOGIN_DISTANCE_THRESHOLD` (default 0.60).

### Product / order data model notes
- `Product.merchant` is limited to users with `role="MERCHANT"` (`limit_choices_to`).
- Stock lives on a separate `Inventory` OneToOne model, not on `Product`. Use `inventory.decrease()` / `increase()` rather than mutating `quantity` directly — they update `last_restocked` and handle the "not enough stock" ValueError. `Product.in_stock` / `stock_quantity` read through this relation and tolerate a missing `Inventory`.
- `OrderItem` stores `product_name` and `product_price` as snapshots so historical orders survive price changes and product deletion (`product` is `SET_NULL`).
- `Order.calculate_totals()` recomputes `subtotal` + `total` from items; call it after adding/removing items.
- `ReturnRequest` is OneToOne per `OrderItem` and has its own status machine (`REQUESTED → APPROVED/REJECTED → REFUNDED`), independent from `Order.Status`.
- Reviews are unique per `(product, user)` via a DB constraint; `Product.average_rating` and `review_count` aggregate lazily.

### Recommendations
- Gated by `ENABLE_AI_RECOMMENDATIONS` setting (env var, default on). When off, every entry point returns `get_popular_recommendations` as fallback.
- `recommendations.service` is the public API — `track_product_view`, `get_home_recommendations`, `get_product_recommendations`, `get_cart_recommendations`. Views should import from `service`, not `algorithms` or `fallback` directly.
- All service functions wrap scoring in try/except and log+fallback to popular on any exception, so scoring bugs never break page rendering.
- View events are recorded in `ProductViewEvent` (recommendation-only table) via `track_product_view`; only fires for authenticated users.

### URL layout
Root URLs in `config/urls.py` mount apps at: `/accounts/`, `/products/`, `/orders/`, `/cart/`, `/bookmarks/`, `/reports/`, `/api/recommend/`, `/admin/`. `/` redirects to `products:home`. Each app uses an `app_name` namespace — always reverse with the `namespace:name` form (e.g. `accounts:login`, `products:product_detail`).

### Templates & static
- All templates live in the top-level `templates/` dir (added to `TEMPLATES["DIRS"]`), not per-app `templates/<app>/`.
- Bootstrap 5 via crispy-forms (`CRISPY_TEMPLATE_PACK = "bootstrap5"`).
- `cart.context_processors.cart_item_count` injects the cart badge count into every template.
- Media uploads (avatars, product images) go to `MEDIA_ROOT = BASE_DIR/media`; served in DEBUG only.

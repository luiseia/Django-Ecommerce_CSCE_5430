"""
Management command: seed_products

Populates the database with sample health-supplement products (vitamins &
mineral supplements), the categories they belong to, a demo Merchant user
to own them, and Inventory records so they show as in-stock.

Usage:
    python manage.py seed_products          # create all sample data
    python manage.py seed_products --clear  # wipe previous seed data first
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from accounts.models import User
from products.models import Category, Inventory, Product


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
MERCHANT_EMAIL = "healthstore@example.com"
MERCHANT_PASSWORD = "merchant1234"
MERCHANT_STORE = "VitaWell Health Supplements"

CATEGORIES = [
    {
        "name": "Vitamins",
        "description": "Essential vitamins to support your daily nutritional needs.",
    },
    {
        "name": "Mineral Supplements",
        "description": "Key minerals for bone health, immunity, and overall wellness.",
    },
    {
        "name": "Multivitamins",
        "description": "Comprehensive blends combining vitamins and minerals in one serving.",
    },
    {
        "name": "Omega & Fish Oil",
        "description": "Heart-healthy omega fatty acids sourced from premium fish oil.",
    },
    {
        "name": "Herbal & Specialty",
        "description": "Plant-based and specialty supplements for targeted health support.",
    },
]

PRODUCTS = [
    # ── Vitamins ──────────────────────────────────────────────────────────
    {
        "category": "Vitamins",
        "name": "Vitamin C 1000 mg — Immune Support",
        "description": (
            "High-potency Vitamin C tablets with rose hips for enhanced absorption. "
            "Supports immune function, collagen production, and acts as a powerful "
            "antioxidant. 120 tablets per bottle — a 4-month supply."
        ),
        "price": Decimal("14.99"),
        "discount_price": Decimal("11.99"),
        "stock": 250,
    },
    {
        "category": "Vitamins",
        "name": "Vitamin D3 5000 IU — Sunshine Vitamin",
        "description": (
            "Cholecalciferol soft-gels for optimal calcium absorption and bone health. "
            "Ideal for individuals with limited sun exposure. 180 soft-gels per bottle."
        ),
        "price": Decimal("18.49"),
        "stock": 180,
    },
    {
        "category": "Vitamins",
        "name": "Vitamin B12 1000 mcg — Energy & Focus",
        "description": (
            "Methylcobalamin sublingual tablets for rapid absorption. Supports red "
            "blood cell formation, neurological function, and sustained energy levels. "
            "90 dissolvable tablets."
        ),
        "price": Decimal("12.99"),
        "stock": 200,
    },
    {
        "category": "Vitamins",
        "name": "Vitamin A 10 000 IU — Vision Support",
        "description": (
            "Retinyl palmitate soft-gels supporting healthy vision, skin, and immune "
            "response. 100 soft-gels per bottle."
        ),
        "price": Decimal("9.99"),
        "stock": 150,
    },
    {
        "category": "Vitamins",
        "name": "Vitamin E 400 IU — Antioxidant Shield",
        "description": (
            "Natural d-alpha tocopherol soft-gels. Protects cells from oxidative "
            "stress and supports skin health. 120 soft-gels."
        ),
        "price": Decimal("13.49"),
        "discount_price": Decimal("10.99"),
        "stock": 170,
    },
    {
        "category": "Vitamins",
        "name": "Vitamin K2 MK-7 100 mcg",
        "description": (
            "Supports calcium metabolism and cardiovascular health. Works "
            "synergistically with Vitamin D3. 60 vegetarian capsules."
        ),
        "price": Decimal("19.99"),
        "stock": 100,
    },
    # ── Mineral Supplements ───────────────────────────────────────────────
    {
        "category": "Mineral Supplements",
        "name": "Calcium + Magnesium + Zinc Complex",
        "description": (
            "Triple-mineral formula for bone density, muscle function, and immune "
            "support. 240 coated tablets — 2-month supply at 4 tablets per day."
        ),
        "price": Decimal("16.99"),
        "stock": 190,
    },
    {
        "category": "Mineral Supplements",
        "name": "Magnesium Glycinate 400 mg — Calm & Relax",
        "description": (
            "Chelated magnesium for superior absorption. Promotes muscle relaxation, "
            "quality sleep, and nervous system support. 120 vegetarian capsules."
        ),
        "price": Decimal("22.99"),
        "discount_price": Decimal("18.99"),
        "stock": 160,
    },
    {
        "category": "Mineral Supplements",
        "name": "Zinc Picolinate 50 mg — Immune Defense",
        "description": (
            "Highly bioavailable zinc picolinate supporting immune function, skin "
            "health, and wound healing. 120 vegetarian capsules."
        ),
        "price": Decimal("11.49"),
        "stock": 220,
    },
    {
        "category": "Mineral Supplements",
        "name": "Iron Bisglycinate 25 mg — Gentle Formula",
        "description": (
            "Non-constipating chelated iron with Vitamin C for enhanced absorption. "
            "Ideal for individuals with increased iron needs. 90 capsules."
        ),
        "price": Decimal("14.49"),
        "stock": 140,
    },
    {
        "category": "Mineral Supplements",
        "name": "Selenium 200 mcg — Thyroid Support",
        "description": (
            "Essential trace mineral supporting thyroid hormone metabolism and "
            "antioxidant defense. 100 vegetarian capsules."
        ),
        "price": Decimal("8.99"),
        "stock": 130,
    },
    {
        "category": "Mineral Supplements",
        "name": "Potassium Gluconate 99 mg",
        "description": (
            "Supports healthy blood pressure, nerve transmission, and fluid balance. "
            "250 tablets per bottle."
        ),
        "price": Decimal("10.49"),
        "stock": 175,
    },
    # ── Multivitamins ─────────────────────────────────────────────────────
    {
        "category": "Multivitamins",
        "name": "Complete Daily Multivitamin — Men's Formula",
        "description": (
            "Comprehensive blend of 23 vitamins and minerals tailored for men's "
            "health. Includes B-complex for energy, zinc for immune support, and "
            "lycopene for prostate health. 90 tablets — 3-month supply."
        ),
        "price": Decimal("24.99"),
        "discount_price": Decimal("19.99"),
        "stock": 200,
    },
    {
        "category": "Multivitamins",
        "name": "Complete Daily Multivitamin — Women's Formula",
        "description": (
            "Specially formulated with iron, folic acid, calcium, and biotin to "
            "support women's unique nutritional needs. 90 tablets — 3-month supply."
        ),
        "price": Decimal("24.99"),
        "discount_price": Decimal("19.99"),
        "stock": 210,
    },
    {
        "category": "Multivitamins",
        "name": "Kids Chewable Multivitamin — Berry Blast",
        "description": (
            "Fun, great-tasting chewable tablets with essential vitamins A, C, D, "
            "and E plus calcium and iron. No artificial colors or sweeteners. "
            "120 chewable tablets."
        ),
        "price": Decimal("15.99"),
        "stock": 180,
    },
    # ── Omega & Fish Oil ──────────────────────────────────────────────────
    {
        "category": "Omega & Fish Oil",
        "name": "Omega-3 Fish Oil 1200 mg — Triple Strength",
        "description": (
            "Molecularly distilled fish oil providing 900 mg combined EPA and DHA "
            "per soft-gel. Supports heart, brain, and joint health. Enteric-coated "
            "to reduce fishy aftertaste. 90 soft-gels."
        ),
        "price": Decimal("27.99"),
        "discount_price": Decimal("22.49"),
        "stock": 150,
    },
    {
        "category": "Omega & Fish Oil",
        "name": "Algal Omega-3 DHA — Vegan Formula",
        "description": (
            "Plant-based DHA derived from sustainably grown microalgae. "
            "500 mg DHA per capsule. 60 vegetarian soft-gels."
        ),
        "price": Decimal("29.99"),
        "stock": 90,
    },
    {
        "category": "Omega & Fish Oil",
        "name": "Cod Liver Oil 1000 mg — Classic",
        "description": (
            "Traditional cod liver oil rich in Vitamins A and D plus omega-3 fatty "
            "acids. Lemon-flavored soft-gels for easy swallowing. 150 soft-gels."
        ),
        "price": Decimal("17.99"),
        "stock": 120,
    },
    # ── Herbal & Specialty ────────────────────────────────────────────────
    {
        "category": "Herbal & Specialty",
        "name": "Turmeric Curcumin 1500 mg — BioPerine Enhanced",
        "description": (
            "Standardized to 95 % curcuminoids with BioPerine black pepper extract "
            "for 2000 % improved absorption. Supports joint comfort and a healthy "
            "inflammatory response. 120 vegetarian capsules."
        ),
        "price": Decimal("21.99"),
        "discount_price": Decimal("17.49"),
        "stock": 195,
    },
    {
        "category": "Herbal & Specialty",
        "name": "Ashwagandha KSM-66 600 mg — Stress Relief",
        "description": (
            "Clinically studied full-spectrum root extract. Promotes calm, supports "
            "cognitive function, and helps the body adapt to stress. 90 vegetarian "
            "capsules."
        ),
        "price": Decimal("23.49"),
        "stock": 160,
    },
    {
        "category": "Herbal & Specialty",
        "name": "Elderberry Extract 1200 mg — Immune Boost",
        "description": (
            "Concentrated Sambucus nigra berry extract with Vitamin C and zinc. "
            "Supports upper-respiratory health and seasonal wellness. 60 chewable "
            "gummies."
        ),
        "price": Decimal("16.99"),
        "discount_price": Decimal("13.99"),
        "stock": 230,
    },
    {
        "category": "Herbal & Specialty",
        "name": "Probiotics 50 Billion CFU — Gut Health",
        "description": (
            "16-strain probiotic blend with delayed-release capsules for targeted "
            "intestinal delivery. Supports digestive balance and immune function. "
            "30 capsules — 1-month supply."
        ),
        "price": Decimal("32.99"),
        "stock": 110,
    },
]


class Command(BaseCommand):
    help = "Seed the database with sample health-supplement products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously seeded products, categories, and the demo merchant before re-seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()

        merchant = self._get_or_create_merchant()
        categories = self._create_categories()
        self._create_products(merchant, categories)

        self.stdout.write(self.style.SUCCESS("✓ Seed data loaded successfully."))

    # ------------------------------------------------------------------
    def _clear(self):
        deleted_products, _ = Product.objects.filter(
            merchant__email=MERCHANT_EMAIL
        ).delete()
        deleted_cats, _ = Category.objects.filter(
            name__in=[c["name"] for c in CATEGORIES]
        ).delete()
        User.objects.filter(email=MERCHANT_EMAIL).delete()
        self.stdout.write(
            f"  Cleared {deleted_products} products, {deleted_cats} categories, "
            f"and the demo merchant."
        )

    # ------------------------------------------------------------------
    def _get_or_create_merchant(self):
        merchant, created = User.objects.get_or_create(
            email=MERCHANT_EMAIL,
            defaults={
                "role": User.Role.MERCHANT,
                "first_name": "VitaWell",
                "last_name": "Health",
                "store_name": MERCHANT_STORE,
                "phone_number": "+15551234567",
                "is_active": True,
            },
        )
        if created:
            merchant.set_password(MERCHANT_PASSWORD)
            merchant.save()
            self.stdout.write(
                f"  Created merchant: {MERCHANT_EMAIL} / {MERCHANT_PASSWORD}"
            )
        else:
            self.stdout.write(f"  Merchant already exists: {MERCHANT_EMAIL}")
        return merchant

    # ------------------------------------------------------------------
    def _create_categories(self):
        cat_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "slug": slugify(cat_data["name"]),
                    "description": cat_data["description"],
                },
            )
            cat_map[cat.name] = cat
            status = "created" if created else "exists"
            self.stdout.write(f"  Category '{cat.name}' — {status}")
        return cat_map

    # ------------------------------------------------------------------
    def _create_products(self, merchant, categories):
        created_count = 0
        skipped_count = 0

        for prod_data in PRODUCTS:
            slug = slugify(prod_data["name"])
            if Product.objects.filter(slug=slug).exists():
                skipped_count += 1
                continue

            product = Product.objects.create(
                merchant=merchant,
                category=categories[prod_data["category"]],
                name=prod_data["name"],
                slug=slug,
                description=prod_data["description"],
                price=prod_data["price"],
                discount_price=prod_data.get("discount_price"),
                is_active=True,
            )

            Inventory.objects.create(
                product=product,
                quantity=prod_data["stock"],
                low_stock_threshold=10,
            )

            created_count += 1

        self.stdout.write(
            f"  Products: {created_count} created, {skipped_count} skipped (already exist)"
        )

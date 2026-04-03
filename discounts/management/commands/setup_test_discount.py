from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from discounts.models import DiscountCode
from products.models import Product, Category, Inventory
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup complete test environment with merchant, products, and discounts'

    def handle(self, *args, **options):
        # Get or create a merchant user
        merchant, created = User.objects.get_or_create(
            email='merchant@example.com',
            defaults={
                'role': 'MERCHANT',
                'first_name': 'Test',
                'last_name': 'Merchant',
                'is_staff': False,
            }
        )
        
        if created:
            merchant.set_password('password123')
            merchant.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created merchant: {merchant.email}'))
        
        # Create a category
        category, _ = Category.objects.get_or_create(
            name='Electronics',
            defaults={'description': 'Electronic devices and accessories'}
        )
        
        # Create sample products for this merchant
        products_data = [
            {
                'name': 'Premium Laptop',
                'price': Decimal('1200.00'),
                'description': 'High-performance laptop for professionals',
            },
            {
                'name': 'Wireless Monitor',
                'price': Decimal('350.00'),
                'description': 'Premium 4K wireless monitor',
            },
            {
                'name': 'Mechanical Keyboard',
                'price': Decimal('150.00'),
                'description': 'RGB mechanical gaming keyboard',
            },
        ]
        
        created_products = []
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                slug=prod_data['name'].lower().replace(' ', '-'),
                defaults={
                    'merchant': merchant,
                    'category': category,
                    'name': prod_data['name'],
                    'price': prod_data['price'],
                    'description': prod_data['description'],
                    'is_active': True,
                }
            )
            
            if created:
                # Create inventory for the product
                Inventory.objects.get_or_create(
                    product=product,
                    defaults={'quantity': 50, 'low_stock_threshold': 5}
                )
                created_products.append(product)
                self.stdout.write(f'  ✓ Created product: {product.name} (${product.price})')
        
        # Ensure SAVE20 discount exists and update it with products
        discount, created = DiscountCode.objects.get_or_create(
            code='SAVE20',
            merchant=merchant,
            defaults={
                'description': 'Save $20 on purchases of $100 or more. All electronics eligible!',
                'discount_type': 'FIXED',
                'discount_value': Decimal('20.00'),
                'min_purchase_amount': Decimal('100.00'),
                'min_product_price': Decimal('100.00'),
                'max_uses': None,  # Unlimited
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timezone.timedelta(days=365),
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('\n✓ Created discount code: SAVE20'))
        
        # Add all merchant's active products to the discount
        all_products = merchant.products.filter(is_active=True)
        discount.products.set(all_products)
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Updated SAVE20 discount with {all_products.count()} products'))
        
        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('TEST DISCOUNT SETUP COMPLETE')
        self.stdout.write('='*50)
        self.stdout.write(f'Merchant: {merchant.email}')
        self.stdout.write(f'Password: password123')
        self.stdout.write(f'\nDiscount Code: SAVE20')
        self.stdout.write(f'  - Discount: $20 off')
        self.stdout.write(f'  - Min Purchase: $100')
        self.stdout.write(f'  - Applicable Products: {all_products.count()}')
        self.stdout.write(f'  - Valid Until: {discount.valid_until.strftime("%Y-%m-%d")}')
        self.stdout.write(f'\nTest Scenario:')
        self.stdout.write(f'1. Login as merchant: {merchant.email}')
        self.stdout.write(f'2. Go to Manage Discounts')
        self.stdout.write(f'3. See SAVE20 discount with all details')
        self.stdout.write(f'4. Customers can use "SAVE20" code for $20 off when spending $100+')

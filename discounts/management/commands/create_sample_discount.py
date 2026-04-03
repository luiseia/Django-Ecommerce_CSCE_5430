from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from discounts.models import DiscountCode
from products.models import Product

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample discount code SAVE20 for testing'

    def handle(self, *args, **options):
        # Get or create a merchant user for testing
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
            self.stdout.write(self.style.SUCCESS(f'Created merchant user: {merchant.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'Using existing merchant: {merchant.email}'))
        
        # Create SAVE20 discount
        discount, created = DiscountCode.objects.get_or_create(
            code='SAVE20',
            merchant=merchant,
            defaults={
                'description': 'Save $20 on purchases of $100 or more',
                'discount_type': 'FIXED',
                'discount_value': 20,
                'min_purchase_amount': 100,
                'min_product_price': 100,
                'max_uses': None,  # Unlimited
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timezone.timedelta(days=365),
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created discount code: SAVE20'))
            print(f"  - Type: Fixed Amount")
            print(f"  - Value: $20 off")
            print(f"  - Minimum Purchase: $100")
            print(f"  - Minimum Product Price: $100")
            print(f"  - Valid Until: {discount.valid_until.strftime('%Y-%m-%d')}")
            
            # Get all products from this merchant and add them to the discount
            products = merchant.products.filter(is_active=True)
            if products.exists():
                discount.products.set(products)
                self.stdout.write(self.style.SUCCESS(f'Added {products.count()} products to the discount'))
            else:
                self.stdout.write(self.style.WARNING('No active products found for this merchant'))
        else:
            self.stdout.write(self.style.WARNING('SAVE20 discount already exists'))

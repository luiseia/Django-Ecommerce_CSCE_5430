from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class DiscountCode(models.Model):
    """折扣代码主模型 - 由商家（Merchant）创建和管理"""
    
    DISCOUNT_TYPE_CHOICES = (
        ('PERCENTAGE', 'Percentage (%)'),
        ('FIXED', 'Fixed Amount ($)'),
    )
    
    # 商家关联
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discount_codes',
        limit_choices_to={'role': 'MERCHANT'},
        null=True,
        blank=True,
    )
    
    code = models.CharField(max_length=50)  # 代码本身（如 "SAVE20"）
    description = models.TextField(blank=True)
    
    # 折扣类型和值
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    # 指定可用的商品
    products = models.ManyToManyField(
        'products.Product',
        related_name='discount_codes',
        blank=True,
        help_text='Leave empty for all products, or select specific products'
    )
    
    # 限额
    max_uses = models.IntegerField(null=True, blank=True)  # None=无限制
    current_uses = models.IntegerField(default=0)  # 已使用次数
    
    min_purchase_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )  # 最小购买金额才能用（针对整个订单）
    
    min_product_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Minimum price per product to apply discount (e.g., 100 for "Buy 100+ get 20 off")'
    )
    
    # 时间限制
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('merchant', 'code')  # 同一商家内代码唯一
    
    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()}) - {self.merchant.email}"
    
    def is_valid(self):
        """检查代码是否有效"""
        now = timezone.now()
        
        if not self.is_active:
            return False, "This code is no longer active"
        
        if now < self.valid_from:
            return False, "This code is not yet valid"
        
        if self.valid_until and now > self.valid_until:
            return False, "This code has expired"
        
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "This code has reached its usage limit"
        
        return True, ""
    
    def is_applicable_to_products(self, products_list):
        """
        检查折扣是否适用于给定的商品列表
        products_list: Product 实例列表
        返回: (是否适用, 消息, 符合条件的商品总金额)
        """
        # 如果没有指定商品，对所有商品有效
        if not self.products.exists():
            return True, "", sum(p.effective_price for p in products_list)
        
        # 检查是否有任何商品在允许列表中
        applicable_products = [p for p in products_list if p in self.products.all()]
        if not applicable_products:
            return False, f"This code is not applicable to the products in your cart", 0
        
        applicable_total = sum(p.effective_price for p in applicable_products)
        return True, "", applicable_total
    
    def calculate_discount(self, amount):
        """
        计算折扣金额
        返回: (折扣金额, 折扣后金额)
        """
        if self.discount_type == 'PERCENTAGE':
            discount = amount * (self.discount_value / 100)
            # 确保不超过原金额
            discount = min(discount, amount)
        else:  # FIXED
            discount = min(self.discount_value, amount)
        
        final_amount = amount - discount
        return discount, final_amount


class OrderDiscount(models.Model):
    """记录订单上应用的折扣"""
    
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='discount'
    )
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.PROTECT)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    applied_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order {self.order.order_number} - {self.discount_code.code}"

from django import forms
from .models import DiscountCode


class ApplyDiscountForm(forms.Form):
    """用户输入折扣代码的表单"""
    
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter discount code',
            'autocomplete': 'off',
        }),
        label='Discount Code'
    )
    
    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        try:
            DiscountCode.objects.get(code=code)
        except DiscountCode.DoesNotExist:
            raise forms.ValidationError("This discount code does not exist.")
        return code


class MerchantDiscountForm(forms.ModelForm):
    """商家创建和编辑折扣的表单"""
    
    class Meta:
        model = DiscountCode
        fields = ['code', 'description', 'discount_type', 'discount_value', 
                  'min_purchase_amount', 'min_product_price', 'max_uses',
                  'valid_from', 'valid_until', 'is_active', 'products']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SAVE20, WELCOME10',
                'maxlength': '50'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Discount description (visible to customers)'
            }),
            'discount_type': forms.RadioSelect(choices=DiscountCode.DISCOUNT_TYPE_CHOICES),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '20',
                'step': '0.01',
                'min': '0'
            }),
            'min_purchase_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'step': '0.01',
                'min': '0'
            }),
            'min_product_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '100 (for 100+ discount)',
                'step': '0.01',
                'min': '0'
            }),
            'max_uses': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave empty for unlimited',
                'min': '1'
            }),
            'valid_from': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'valid_until': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'products': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, merchant=None, **kwargs):
        super().__init__(*args, **kwargs)
        # 商家只能为自己的商品设置折扣
        if merchant:
            self.fields['products'].queryset = merchant.products.filter(is_active=True)
        self.fields['products'].label = 'Applicable Products (leave empty for all)'


from django.db import models
from django.utils import timezone
from authentication.models import Shop
from rewards.models import Customer

class Voucher(models.Model):
    VOUCHER_TYPE_CHOICES = (
        ('discount', 'Discount'),
        ('tier_based', 'Tier Based'),
    )
    DISCOUNT_TYPE_CHOICES = (
        ('percent', 'Percentage'),
        ('fixed', 'Fixed'),
    )

    code = models.CharField(max_length=50, unique=True)
    voucher_type = models.CharField(max_length=20, default='discount')
    tier = models.CharField(max_length=50, null=True, blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shops = models.ManyToManyField(Shop, related_name='vouchers')
    customers = models.ManyToManyField(Customer, related_name='vouchers', blank=True)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    threshold_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit_per_user = models.PositiveIntegerField(default=1)
    usage_limit_total = models.PositiveIntegerField(default=1)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.voucher_type})"

    def calculate_discount(self, cart_amount):
        if cart_amount < self.min_purchase_amount:
            return 0
        if not self.is_applicable():
            return 0
        if self.voucher_type == 'tier_based' and not self.tier:
            return 0

        if self.discount_type == 'percent':
            percent_discount = (self.discount_value / 100) * cart_amount
            if cart_amount >= (self.threshold_amount or 0):
                return min(percent_discount, self.max_discount_amount or percent_discount)
            return percent_discount
        elif self.discount_type == 'fixed':
            return self.discount_value or 0
        return 0

    def is_applicable(self):
        now = timezone.now()
        return (
            self.is_active and
            self.usage_count < self.usage_limit_total and
            self.valid_from <= now <= self.valid_until
        )

    def can_apply_for_customer(self, cust_id):
        if not self.customers.exists():
            # Check usage limit per user for unrestricted vouchers
            usage_count = VoucherUsage.objects.filter(voucher=self, cust_id=cust_id).count()
            return usage_count < self.usage_limit_per_user
        # For restricted vouchers, check if cust_id is allowed and within limit
        if not self.customers.filter(customer_id=cust_id).exists():
            return False
        usage_count = VoucherUsage.objects.filter(voucher=self, cust_id=cust_id).count()
        return usage_count < self.usage_limit_per_user

class VoucherUsage(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='usages')
    cust_id = models.CharField(max_length=50)  # Store cust_id directly
    used_at = models.DateTimeField(auto_now_add=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)  # Track shop used at

    class Meta:
        unique_together = ('voucher', 'cust_id', 'used_at')  # Prevent duplicate entries

    def __str__(self):
        return f"{self.voucher.code} used by {self.cust_id} at {self.used_at}"
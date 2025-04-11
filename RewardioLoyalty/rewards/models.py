from django.contrib.auth.models import User
from authentication.models import Shop
import uuid
from django.db import models
from authentication.models import Shop
from django.db import models
from authentication.models import Shop
from django.utils.timezone import now, timezone


class PurchaseRule(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='purchase_rules')
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    points = models.IntegerField()
    redeemable = models.BooleanField(default=False)
    redeemable_shops = models.ManyToManyField(Shop, related_name='rules_redeemable_in', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiration_days = models.IntegerField(null=True, blank=True, help_text="Days until points expire, null for no expiration")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentage discount for redeemable codes (0-100)")

    def __str__(self):
        return f"{self.points} points for {self.min_purchase_amount}-{self.max_purchase_amount} in {self.shop}"
    
    
class CurrencyConversion(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='currency_conversions')
    currency = models.CharField(max_length=10)
    points_per_currency = models.IntegerField() 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  
        return f"{self.currency}: {self.points_per_currency} points"

class Customer(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customers')
    customer_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('shop', 'customer_id')
    def __str__(self):
        return self.customer_id
   

class RewardCondition(models.Model):
    name = models.CharField(max_length=255, unique=True)  # e.g., "Birthday Reward", "Monthly Bonus"
    max_usage_per_user = models.IntegerField(default=1)  # How many times a user can use it
    duration_days = models.IntegerField(null=True, blank=True)  # Expiry duration (e.g., 30 days)
    recurring_type = models.CharField(
        max_length=50,
        choices=[("none", "None"), ("monthly", "Monthly"), ("yearly", "Yearly") ,("daily", "Daily"), ("weekly", "Weekly"), ("quarterly", "Quarterly"),
        ("bi_annual", "Bi-Annual"),],
        default="none"
    )
    def __str__(self):
        return self.name
    
    
class RewardType(models.Model):
    reward_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reward_name = models.CharField(max_length=255)
    description = models.TextField()
    condition = models.ForeignKey(RewardCondition, on_delete=models.CASCADE, related_name="reward_types")
    has_expiring_points = models.BooleanField(default=False)  


    def __str__(self):
        return self.reward_name


class DirectReward(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    points = models.IntegerField()
    expiry_date = models.DateField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.expiry_date and timezone.now().date() > self.expiry_date

    def __str__(self):
        return f"{self.customer} - {self.reward_type} - {self.points}"
    
    
class Wallet(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wallets')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='wallets')
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer', 'shop')  # One wallet per customer-shop pair

    def __str__(self):
        return f"Wallet for {self.customer.customer_id} at {self.shop.name}: {self.points} points"
    
class ShopRewardLimit(models.Model):
    shop = models.OneToOneField(Shop, on_delete=models.CASCADE)
    max_points = models.PositiveIntegerField(default=0)  
    used_points = models.PositiveIntegerField(default=0)  
    total_points_used = models.PositiveIntegerField(default=0)  # NEW: Track total lifetime points used
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Direct Reward: {self.reward_type.reward_name} for {self.shop.shop_name} with {self.points} points for customer {self.customer.customer_id}"


# ___________________________________________________ rewards wallet section ________________________________________


class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    points = models.IntegerField()
    redeemable = models.BooleanField(default=False)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_redeemed = models.BooleanField(default=False)
    redeemed_at_shop = models.ForeignKey(Shop, on_delete=models.SET_NULL, null=True, blank=True, related_name='redeemed_transactions')
    description = models.CharField(max_length=255, default="Purchase processed via API")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True) 
    

    def __str__(self):
        return f"{self.points} points for {self.amount} - {self.description}"

class Tier(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='tiers')
    name = models.CharField(max_length=50, help_text="e.g., Bronze, Silver, Gold")
    min_points = models.IntegerField(help_text="Minimum points to qualify for this tier")
    max_points = models.IntegerField(help_text="Maximum points for this tier, inclusive")
    description = models.TextField(blank=True, null=True, help_text="Description of tier benefits")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('shop', 'name') 
        ordering = ['min_points']

    def __str__(self):
        return f"{self.name} ({self.min_points}-{self.max_points} points) - {self.shop.name}"
class CustomerTier(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tiers')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customer_tiers')
    tier = models.ForeignKey(Tier, on_delete=models.SET_NULL, null=True, related_name='customers')
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(auto_now_add=True)  # When the tier was assigned
    expires_at = models.DateTimeField(null=True, blank=True)  # Tier expiration date
    grace_period_expires_at = models.DateTimeField(null=True, blank=True)  # Grace period expiration
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('customer', 'shop') 

    def __str__(self):
        return f"{self.customer.customer_id} - {self.tier.name if self.tier else 'No Tier'} at {self.shop.name}"

    def is_in_grace_period(self):
        now = timezone.now()
        return self.grace_period_expires_at and now <= self.grace_period_expires_at
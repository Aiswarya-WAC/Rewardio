from django.db import models
from django.db import models
from django.contrib.auth.models import User
from authentication.models import Shop
import uuid


class PurchaseRule(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='purchase_rules')  # Shop-specific rule
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['min_purchase_amount']

    def __str__(self):
        return f"Rule for {self.shop.shop_name}: {self.min_purchase_amount}-{self.max_purchase_amount} => {self.points} points"

class CurrencyConversion(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='currency_conversions')
    currency = models.CharField(max_length=10)
    points_per_currency = models.IntegerField()  # Points per unit of currency (like 1 INR = 10 points)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency}: {self.points_per_currency} points"

class Customer(models.Model):
    customer_id = models.CharField(max_length=36, unique=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customer {self.customer_id}"
    

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
    reward_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Auto-generated UUID
    reward_name = models.CharField(max_length=255)
    description = models.TextField()
    condition = models.ForeignKey(RewardCondition, on_delete=models.CASCADE, related_name="reward_types")

    def __str__(self):
        return self.reward_name
    
from django.utils.timezone import now

class DirectReward(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    points = models.IntegerField()
    redeemed_at = models.DateTimeField(auto_now_add=True)  # Existing field
    created_at = models.DateTimeField(auto_now_add=True)

class Wallet(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wallet')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='wallets')
    points = models.IntegerField(default=0)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.customer.customer_id} at {self.shop.shop_name}: {self.points} points"
    
class ShopRewardLimit(models.Model):
    shop = models.OneToOneField(Shop, on_delete=models.CASCADE)
    max_points = models.PositiveIntegerField(default=0)  
    used_points = models.PositiveIntegerField(default=0)  
    total_points_used = models.PositiveIntegerField(default=0)  # NEW: Track total lifetime points used
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

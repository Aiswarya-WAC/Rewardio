from django.db import models
from django.db import models
from django.contrib.auth.models import User
import uuid

class vendor(models.Model):
    User = models.OneToOneField(User,on_delete=models.CASCADE,related_name='vendor_profile')
    owner_name  = models.CharField(max_length=100)
    
    
class Shop(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=255)
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    secret_key = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

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

class RewardType(models.Model):
    reward_name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.reward_name
    
class DirectReward(models.Model):
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to RewardType
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to Shop
    points = models.IntegerField()  # Points assigned for this direct reward
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Direct Reward: {self.reward_type.reward_name} for {self.shop.shop_name} with {self.points} points"


class DirectReward(models.Model):
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to RewardType
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to Shop
    points = models.IntegerField()  # Points assigned for this direct reward
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Direct Reward: {self.reward_type.reward_name} for {self.shop.shop_name} with {self.points} points"

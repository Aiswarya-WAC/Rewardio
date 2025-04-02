from django.db import models
from django.db import models
from django.contrib.auth.models import User
import uuid
from authentication.models import Shop
from django.db import models
from authentication.models import Shop


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

class Customer(models.Model):
    customer_id = models.CharField(max_length=36, unique=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customer {self.customer_id}"
    
class DirectReward(models.Model):
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to RewardType
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to Shop
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='direct_rewards')  # Link to Customer
    points = models.IntegerField()  # Points assigned for this direct reward
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Direct Reward: {self.reward_type.reward_name} for {self.shop.shop_name} with {self.points} points for customer {self.customer.customer_id}"


# ___________________________________________________ rewards wallet section ________________________________________

# models.py
# models.py
from django.db import models
from authentication.models import Shop

class Customer(models.Model):
    customer_id = models.CharField(max_length=36, unique=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customer {self.customer_id}"

class Wallet(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wallet')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='wallets')
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.customer.customer_id} at {self.shop.shop_name}: {self.points} points"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    points = models.IntegerField()  # Positive for credit
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.points} points - {self.description}"
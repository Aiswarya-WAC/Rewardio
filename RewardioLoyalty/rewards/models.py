from django.db import models
from django.db import models
from django.contrib.auth.models import User
import uuid
from authentication.models import Shop
from django.db import models
from authentication.models import Shop
from django.db import models
from authentication.models import Shop


class PurchaseRule(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='purchase_rules')
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2)
    points = models.IntegerField()
    redeemable = models.BooleanField(default=False)
    redeemable_shops = models.ManyToManyField(Shop, related_name='rules_redeemable_in', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.points} points for {self.min_purchase_amount}-{self.max_purchase_amount} in {self.shop}"
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
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='customers')
    customer_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.customer_id
    
class DirectReward(models.Model):
    reward_type = models.ForeignKey(RewardType, on_delete=models.CASCADE, related_name='direct_rewards')  
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='direct_rewards')  
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='direct_rewards')  
    points = models.IntegerField()  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Direct Reward: {self.reward_type.reward_name} for {self.shop.shop_name} with {self.points} points for customer {self.customer.customer_id}"


# ___________________________________________________ rewards wallet section ________________________________________




class Wallet(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wallets')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='wallets')
    purchase_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer', 'shop')

    def __str__(self):
        return f"Wallet for {self.customer.customer_id} at {self.shop.name}"

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
    

    def __str__(self):
        return f"{self.points} points for {self.amount} - {self.description}"
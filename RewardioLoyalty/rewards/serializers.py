from rest_framework import serializers
from .models import PurchaseRule, CurrencyConversion, RewardType, Shop

class PurchaseRuleSerializer(serializers.ModelSerializer):
    shop_id = serializers.PrimaryKeyRelatedField(source='shop', read_only=True)

    class Meta:
        model = PurchaseRule
        fields = ['id', 'shop_id', 'min_purchase_amount', 'max_purchase_amount', 'points']

class CurrencyConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyConversion
        fields = ['id', 'shop', 'currency', 'points_per_currency', 'created_at', 'updated_at']

class RewardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardType
        fields = ['id', 'reward_name', 'description']

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'vendor', 'shop_name', 'api_key', 'created_at']

from .models import DirectReward, RewardType, Shop
from rest_framework import serializers
from .models import DirectReward, RewardType, Shop, Customer

class DirectRewardSerializer(serializers.ModelSerializer):
    reward_type = serializers.StringRelatedField()  # Show reward type name
    shop = serializers.StringRelatedField()  # Show shop name
    customer = serializers.StringRelatedField()  # Show customer id

    class Meta:
        model = DirectReward
        fields = ['id', 'reward_type', 'shop', 'customer', 'points', 'created_at', 'updated_at']


# ___________________________________________________ rewards wallet section ________________________________________

# serializers.py (add to existing file)
# serializers.py (add to existing file)
from rest_framework import serializers
from .models import Wallet, WalletTransaction

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'amount', 'points', 'description', 'created_at']

class WalletSerializer(serializers.ModelSerializer):
    customer = serializers.StringRelatedField()
    shop = serializers.StringRelatedField()
    transactions = WalletTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'customer', 'shop', 'points', 'created_at', 'updated_at', 'transactions']
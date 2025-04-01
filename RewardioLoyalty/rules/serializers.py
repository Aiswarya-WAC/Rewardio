from rest_framework import serializers
from .models import PurchaseRule, CurrencyConversion, RewardType, Shop

class PurchaseRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseRule
        fields = ['id', 'shop', 'min_purchase_amount', 'max_purchase_amount', 'points', 'created_at', 'updated_at']

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

class DirectRewardSerializer(serializers.ModelSerializer):
    reward_type = serializers.StringRelatedField()  # Show reward type name
    shop = serializers.StringRelatedField()  # Show shop name

    class Meta:
        model = DirectReward
        fields = ['id', 'reward_type', 'shop', 'points', 'created_at', 'updated_at']

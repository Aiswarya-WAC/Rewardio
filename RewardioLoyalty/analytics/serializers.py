# vendor_dashboard/serializers.py
from rest_framework import serializers
from rewards.models import Shop, WalletTransaction, DirectReward, PurchaseRule, CurrencyConversion, ShopRewardLimit

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'api_key']

class PurchaseRuleSerializer(serializers.ModelSerializer):
    redeemable_shops = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = PurchaseRule
        fields = [
            'id', 'min_purchase_amount', 'max_purchase_amount', 'points', 
            'redeemable', 'expiration_days', 'discount_percentage', 'redeemable_shops'
        ]

class CurrencyConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyConversion
        fields = ['id', 'currency', 'points_per_currency']

class ShopRewardLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopRewardLimit
        fields = ['max_points']

class WalletTransactionSerializer(serializers.ModelSerializer):
    redeemed_at_shop_name = serializers.CharField(source='redeemed_at_shop.name', read_only=True, allow_null=True)

    class Meta:
        model = WalletTransaction
        fields = ['id', 'amount', 'points', 'redeemable', 'code', 'is_redeemed', 'redeemed_at_shop_name', 'description', 'created_at']

class DirectRewardSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    reward_type_name = serializers.CharField(source='reward_type.reward_name', read_only=True)

    class Meta:
        model = DirectReward
        fields = ['id', 'points', 'shop_name', 'reward_type_name', 'created_at', 'redeemed_at']
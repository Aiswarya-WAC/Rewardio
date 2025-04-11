from rest_framework import serializers
from .models import PurchaseRule, CurrencyConversion, RewardType, Shop
from .models import Wallet, WalletTransaction
from .models import Tier, CustomerTier
from .models import DirectReward, RewardType, Shop
from .models import RewardCondition

class PurchaseRuleSerializer(serializers.ModelSerializer):
    shop_id = serializers.PrimaryKeyRelatedField(source='shop', queryset=Shop.objects.all())
    redeemable_shops = serializers.PrimaryKeyRelatedField(many=True, queryset=Shop.objects.all(), required=False)
    

    class Meta:
        model = PurchaseRule
        fields = ['id', 'shop_id', 'min_purchase_amount', 'max_purchase_amount', 'points', 'redeemable', 'redeemable_shops', 'expiration_days', 'discount_percentage']
        

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



class DirectRewardSerializer(serializers.ModelSerializer):
    reward_type = RewardTypeSerializer(read_only=True)
    reward_type_id = serializers.PrimaryKeyRelatedField(
        queryset=RewardType.objects.all(),
        source="reward_type",
        write_only=True
    )

    class Meta:
        model = DirectReward
        fields = ["id", "shop_id", "reward_type", "reward_type_id", "customer_id", "points"]




class RewardConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardCondition
        fields = ["id", "name", "max_usage_per_user", "duration_days", "recurring_type"]


class RewardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardType
      

class RewardTypeSerializer(serializers.ModelSerializer):
    reward_uuid = serializers.UUIDField(read_only=True)  # UUID is auto-generated

    condition = RewardConditionSerializer(read_only=True)  # Nested display
    condition_id = serializers.PrimaryKeyRelatedField(
        queryset=RewardCondition.objects.all(),
        source="condition",
        write_only=True
    )

    class Meta:
        model = RewardType
        fields = ["id", "reward_uuid", "reward_name", "description", "condition", "condition_id","has_expiring_points"]


class DirectRewardSerializer(serializers.ModelSerializer):
    reward_type = serializers.StringRelatedField()  
    shop = serializers.StringRelatedField() 
    customer = serializers.StringRelatedField()  

    class Meta:
        model = DirectReward
        fields = ['id', 'reward_type', 'shop', 'customer', 'points', 'created_at', 'expiry_date']


# _______________________________________________________________ rewards wallet section _________________________________________________________________________________


class WalletTransactionSerializer(serializers.ModelSerializer):
    redeemed_at_shop_name = serializers.CharField(source='redeemed_at_shop.name', read_only=True, allow_null=True)

    class Meta:
        model = WalletTransaction
        fields = ['id', 'amount', 'points', 'redeemable', 'code', 'is_redeemed', 'redeemed_at_shop_name', 'description', 'created_at', 'expiration_days', 'customer_id','points  ']
        

class WalletSerializer(serializers.ModelSerializer):
    customer_id = serializers.CharField(source='customer.customer_id')
    shop_name = serializers.CharField(source='shop.name')


    class Meta:
        model = Wallet
        fields = ['id', 'customer_id','shop_name' ,'points']
        
        
class WalletTransactionSerializer(serializers.ModelSerializer):
    redeemed_at_shop_name = serializers.CharField(source='redeemed_at_shop.name', read_only=True, allow_null=True)

    class Meta:
        model = WalletTransaction
        fields = ['id', 'amount', 'points', 'redeemable', 'code', 'is_redeemed', 'redeemed_at_shop_name', 'description', 'created_at',]
        
        

class TierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tier
        fields = ['id', 'name', 'description']
        read_only_fields = ['shop', 'created_at', 'updated_at']

class CustomerTierSerializer(serializers.ModelSerializer):
    tier = TierSerializer(read_only=True)
    points = serializers.SerializerMethodField()

    class Meta:
        model = CustomerTier
        fields = ['id', 'customer', 'shop', 'tier', 'points', 'assigned_at', 'expires_at']
        read_only_fields = ['assigned_at', 'expires_at', 'grace_period_expires_at', 'updated_at']

    def get_points(self, obj):
        wallet = Wallet.objects.filter(customer=obj.customer, shop=obj.shop).first()
        return wallet.points if wallet else 0
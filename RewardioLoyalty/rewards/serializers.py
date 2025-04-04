from rest_framework import serializers
from .models import PurchaseRule, CurrencyConversion, RewardType, Shop

class PurchaseRuleSerializer(serializers.ModelSerializer):
    shop = serializers.PrimaryKeyRelatedField(queryset=Shop.objects.all())

    class Meta:
        model = PurchaseRule
        fields = ['id', 'shop', 'min_purchase_amount', 'max_purchase_amount', 'points']

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
from .models import DirectReward

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


from rest_framework import serializers
from .models import RewardCondition

class RewardConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardCondition
        fields = ["id", "name", "max_usage_per_user", "duration_days", "recurring_type"]



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
        fields = ["id", "reward_uuid", "reward_name", "description", "condition", "condition_id"]
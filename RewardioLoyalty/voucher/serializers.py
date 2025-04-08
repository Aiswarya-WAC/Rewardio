from rest_framework import serializers
from .models import Voucher
from authentication.models import Shop
from rewards.models import Customer

class VoucherSerializer(serializers.ModelSerializer):
    shop_api_key = serializers.CharField(write_only=True, allow_null=False)
    cust_id = serializers.CharField(write_only=True, allow_null=True)
    min_purchase_amount = serializers.DecimalField(max_digits=10, decimal_places=2)  # Required

    class Meta:
        model = Voucher
        fields = [
            'code', 'voucher_type', 'tier', 'discount_type', 'discount_value', 'max_discount_amount',
            'shop_api_key', 'cust_id', 'min_purchase_amount', 'threshold_amount', 'valid_from', 'valid_until',
            'usage_limit_per_user', 'usage_limit_total'
        ]

    def validate(self, data):
        voucher_type = data.get('voucher_type')
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value')
        tier = data.get('tier')
        shop_api_key = data.get('shop_api_key')
        cust_id = data.get('cust_id')
        min_purchase_amount = data.get('min_purchase_amount')

        # Validate shop_api_key
        if not shop_api_key:
            raise serializers.ValidationError("At least one shop_api_key is required.")
        if isinstance(shop_api_key, str):
            shop_api_keys = [shop_api_key]
        elif isinstance(shop_api_key, list):
            shop_api_keys = shop_api_key
        else:
            raise serializers.ValidationError("shop_api_key must be a string or a list of strings.")
        shops = Shop.objects.filter(api_key__in=shop_api_keys)
        if len(shops) != len(shop_api_keys):
            raise serializers.ValidationError("One or more shop_api_key values are invalid.")
        data['shops'] = shops

        # Validate cust_id
        if cust_id is not None:
            if isinstance(cust_id, str):
                cust_ids = [cust_id]
            elif isinstance(cust_id, list):
                cust_ids = cust_id
            else:
                raise serializers.ValidationError("cust_id must be a string or a list of strings.")
            customers = Customer.objects.filter(customer_id__in=cust_ids)
            if len(customers) != len(cust_ids):
                raise serializers.ValidationError("One or more cust_id values are invalid.")
            data['customers'] = customers
        else:
            data['customers'] = []

        # Validate min_purchase_amount (already required by field definition)
        if min_purchase_amount < 0:
            raise serializers.ValidationError("min_purchase_amount cannot be negative.")

        # Existing validation
        if voucher_type == 'tier_based' and not tier:
            raise serializers.ValidationError("Tier is required for tier_based vouchers.")
        if discount_type in ['percent', 'fixed'] and discount_value is None:
            raise serializers.ValidationError(f"Discount value is required for {discount_type} discount type.")
        if discount_type == 'percent' and (discount_value < 0 or discount_value > 100):
            raise serializers.ValidationError("Percentage discount must be between 0 and 100.")
        if discount_type == 'fixed' and discount_value < 0:
            raise serializers.ValidationError("Fixed discount cannot be negative.")
        return data

    def create(self, validated_data):
        shops = validated_data.pop('shops')
        customers = validated_data.pop('customers', [])
        validated_data.pop('shop_api_key')
        validated_data.pop('cust_id')
        voucher = Voucher.objects.create(**validated_data)
        voucher.shops.set(shops)
        if customers:
            voucher.customers.set(customers)
        return voucher

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.voucher_type == 'tier_based':
            representation['tier_info'] = f"Tier: {instance.tier}"
        representation['shop_api_keys'] = [str(shop.api_key) for shop in instance.shops.all()]
        representation['cust_ids'] = [customer.customer_id for customer in instance.customers.all()]
        return representation


class ApplyVoucherSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    cart_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    shop_api_key = serializers.CharField(max_length=100)
    cust_id = serializers.CharField(max_length=50)

    def validate(self, data):
        code = data.get('code')
        shop_api_key = data.get('shop_api_key')
        cust_id = data.get('cust_id')
        cart_amount = data.get('cart_amount')

        try:
            voucher = Voucher.objects.get(code=code)
        except Voucher.DoesNotExist:
            raise serializers.ValidationError("Invalid voucher code.")

        if not voucher.shops.filter(api_key=shop_api_key).exists():
            raise serializers.ValidationError("Voucher is not valid for this shop.")
        if not voucher.is_applicable():
            raise serializers.ValidationError("Voucher is expired, inactive, or usage limit reached.")
        if not voucher.can_apply_for_customer(cust_id):
            raise serializers.ValidationError("Voucher is not applicable for this customer.")

        data['voucher'] = voucher
        return data
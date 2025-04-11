from datetime import datetime, timedelta
import random
import string
from django.db import transaction
import uuid
import requests
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.timezone import now
from django.db.models.query import QuerySet  # Correct import for QuerySet
from rest_framework import permissions, status
from rest_framework.views import APIView
from .models import Customer, Wallet, WalletTransaction, DirectReward
from .serializers import WalletTransactionSerializer, DirectRewardSerializer  # Assuming serializers are in serializers.py

from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from . import models 
from django.db.models.query import QuerySet
from authentication.models import Shop
from .models import (
    PurchaseRule, CurrencyConversion, RewardCondition, RewardType, 
    DirectReward, Customer, Wallet, WalletTransaction, ShopRewardLimit,Tier, CustomerTier
)
from .serializers import (
    PurchaseRuleSerializer, CurrencyConversionSerializer, 
    RewardConditionSerializer, RewardTypeSerializer, 
    DirectRewardSerializer, WalletTransactionSerializer, WalletSerializer ,TierSerializer, CustomerTierSerializer

)
# --------------------------------------------------------------purchase rule section ---------------------------------------------------------------------------------

class CreateAndUpdatePurchaseRuleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shop_id = request.data.get("shop_id")
        min_amount = request.data.get("min_purchase_amount")
        max_amount = request.data.get("max_purchase_amount")
        points = request.data.get("points")
        redeemable = request.data.get("redeemable", False)
        redeemable_shops_ids = request.data.get("redeemable_shops", [])
        expiration_days = request.data.get("expiration_days")
        discount_percentage = request.data.get("discount_percentage")

        required_fields = {
            "shop_id": shop_id,
            "min_purchase_amount": min_amount,
            "max_purchase_amount": max_amount,
            "points": points
        }
        missing_fields = [field for field, value in required_fields.items() if value is None]
        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            shop_id = int(shop_id)
            min_amount = float(min_amount)
            max_amount = float(max_amount)
            points = int(points)
        except (ValueError, TypeError):
            return Response(
                {"error": "shop_id, min_purchase_amount, max_purchase_amount, and points must be numeric"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if min_amount < 0 or max_amount < 0 or points < 0:
            return Response(
                {"error": "min_purchase_amount, max_purchase_amount, and points must be non-negative"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if min_amount >= max_amount:
            return Response(
                {"error": "min_purchase_amount must be less than max_purchase_amount"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if expiration_days is not None:
            try:
                expiration_days = int(expiration_days)
                if expiration_days <= 0:
                    return Response(
                        {"error": "expiration_days must be a positive integer"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {"error": "expiration_days must be an integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if redeemable:
            if discount_percentage is None:
                return Response(
                    {"error": "discount_percentage is required when redeemable is True"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                discount_percentage = float(discount_percentage)
                if not 0 <= discount_percentage <= 100:
                    return Response(
                        {"error": "discount_percentage must be between 0 and 100"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {"error": "discount_percentage must be a number"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            discount_percentage = None  # Ensure it's null if not redeemable

        # Step 3: Validate shop ownership
        try:
            shop = Shop.objects.get(id=shop_id)
            if shop.owner != request.user:
                return Response(
                    {"error": f"You do not own shop with ID {shop_id}"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Shop.DoesNotExist:
            return Response(
                {"error": f"Shop with ID {shop_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Step 4: Check for overlapping rules
        overlapping_rules = PurchaseRule.objects.filter(
            shop=shop,
            min_purchase_amount__lt=max_amount,
            max_purchase_amount__gt=min_amount
        )
        if overlapping_rules.exists():
            overlap_details = [
                {
                    "id": rule.id,
                    "min_purchase_amount": str(rule.min_purchase_amount),
                    "max_purchase_amount": str(rule.max_purchase_amount),
                    "points": rule.points
                }
                for rule in overlapping_rules
            ]
            return Response(
                {
                    "error": "Overlapping purchase rule exists",
                    "details": {
                        "attempted_rule": {
                            "min_purchase_amount": min_amount,
                            "max_purchase_amount": max_amount,
                            "points": points
                        },
                        "overlapping_rules": overlap_details
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 5: Validate redeemable shops if provided
        if redeemable and redeemable_shops_ids:
            try:
                redeemable_shops_ids = [int(shop_id) for shop_id in redeemable_shops_ids]
                redeemable_shops = Shop.objects.filter(id__in=redeemable_shops_ids, owner=shop.owner)
                if len(redeemable_shops) != len(redeemable_shops_ids):
                    invalid_ids = set(redeemable_shops_ids) - {s.id for s in redeemable_shops}
                    return Response(
                        {
                            "error": "One or more shop IDs are invalid or not owned by you",
                            "invalid_shop_ids": list(invalid_ids)
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {"error": "redeemable_shops must contain valid integer shop IDs"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Step 6: Create the purchase rule
        try:
            with transaction.atomic():
                purchase_rule = PurchaseRule.objects.create(
                    shop=shop,
                    min_purchase_amount=min_amount,
                    max_purchase_amount=max_amount,
                    points=points,
                    redeemable=redeemable,
                    expiration_days=expiration_days if expiration_days is not None else None,
                    discount_percentage=discount_percentage
                )

                if redeemable and redeemable_shops_ids:
                    purchase_rule.redeemable_shops.set(redeemable_shops)

                serializer = PurchaseRuleSerializer(purchase_rule)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Failed to create purchase rule: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --------------------------------------------------------------purchase rule section end  ---------------------------------------------------------------------------------

# --------------------------------------------------------------currency  section start  ---------------------------------------------------------------------------------

class CreateAndUpdateCurrencyConversionView(APIView):
    """API endpoints for managing currency conversion rules for points calculation."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retrieve all currency conversion rules for a specific shop."""
        shop_id = request.query_params.get("shop_id")
        if not shop_id:
            return Response({"error": "shop_id is required as a query parameter"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        conversions = CurrencyConversion.objects.filter(shop=shop)
        serializer = CurrencyConversionSerializer(conversions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new currency conversion rule for a shop."""
        shop_id = request.data.get("shop_id")
        currency = request.data.get("currency")

        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        if CurrencyConversion.objects.filter(shop=shop, currency=currency).exists():
            return Response(
                {"error": f"A currency conversion rule for '{currency}' already exists for this shop."},
                status=status.HTTP_400_BAD_REQUEST
            )

        currency_conversion = CurrencyConversion.objects.create(
            shop=shop,
            currency=currency,
            points_per_currency=request.data.get("points_per_currency")
        )
        return Response(CurrencyConversionSerializer(currency_conversion).data, status=status.HTTP_201_CREATED)

    def put(self, request, conversion_id):
        """Update an existing currency conversion rule."""
        try:
            currency_conversion = CurrencyConversion.objects.get(id=conversion_id)
        except CurrencyConversion.DoesNotExist:
            return Response({"error": "Currency Conversion not found"}, status=status.HTTP_400_BAD_REQUEST)

        currency_conversion.currency = request.data.get("currency", currency_conversion.currency)
        currency_conversion.points_per_currency = request.data.get("points_per_currency", currency_conversion.points_per_currency)
        currency_conversion.save()
        return Response(CurrencyConversionSerializer(currency_conversion).data, status=status.HTTP_200_OK)

    def delete(self, request, conversion_id):
        """Delete a specific currency conversion rule."""
        try:
            currency_conversion = CurrencyConversion.objects.get(id=conversion_id)
        except CurrencyConversion.DoesNotExist:
            return Response({"error": "Currency Conversion not found"}, status=status.HTTP_404_NOT_FOUND)

        currency_conversion.delete()
        return Response({"message": "Currency Conversion deleted successfully."}, status=status.HTTP_200_OK)


# --------------------------------------------------------------currency section end ---------------------------------------------------------------------------------

# --------------------------------------------------------------rewards section start  ---------------------------------------------------------------------------------


class RewardConditionView(APIView):
    """API endpoints for managing reward conditions that define constraints on rewards."""
    permission_classes = [IsAuthenticated]

    def get(self, request, condition_id=None):
        """List all reward conditions or retrieve a specific one."""
        if condition_id:
            try:
                condition = RewardCondition.objects.get(id=condition_id)
                serializer = RewardConditionSerializer(condition)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except RewardCondition.DoesNotExist:
                return Response({"error": "Condition not found"}, status=status.HTTP_404_NOT_FOUND)
        conditions = RewardCondition.objects.all()
        serializer = RewardConditionSerializer(conditions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new reward condition."""
        serializer = RewardConditionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, condition_id):
        """Update an existing reward condition."""
        try:
            condition = RewardCondition.objects.get(id=condition_id)
        except RewardCondition.DoesNotExist:
            return Response({"error": "Condition not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = RewardConditionSerializer(condition, data=request.data, partial=True)  # Allow partial updates
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, condition_id):
        """Delete a reward condition."""
        try:
            condition = RewardCondition.objects.get(id=condition_id)
            condition.delete()
            return Response({"message": "Condition deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except RewardCondition.DoesNotExist:
            return Response({"error": "Condition not found"}, status=status.HTTP_404_NOT_FOUND)


class RewardTypeView(APIView):
    """API endpoints for managing reward types."""
    permission_classes = [IsAuthenticated]

    def get(self, request, reward_id=None):
        """List all reward types or retrieve a specific one."""
        if reward_id:
            try:
                reward = RewardType.objects.get(id=reward_id)
                serializer = RewardTypeSerializer(reward)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except RewardType.DoesNotExist:
                return Response({"error": "Reward type not found"}, status=status.HTTP_404_NOT_FOUND)
        
        rewards = RewardType.objects.all()
        serializer = RewardTypeSerializer(rewards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new reward type with a unique UUID."""
        request.data["reward_uuid"] = str(uuid.uuid4())  
        serializer = RewardTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, reward_id):
        """Update an existing reward type."""
        try:
            reward = RewardType.objects.get(id=reward_id)
        except RewardType.DoesNotExist:
            return Response({"error": "Reward type not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = RewardTypeSerializer(reward, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, reward_id):
        """Delete a reward type."""
        try:
            reward = RewardType.objects.get(id=reward_id)
            reward.delete()
            return Response({"message": "Reward type deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except RewardType.DoesNotExist:
            return Response({"error": "Reward type not found"}, status=status.HTTP_404_NOT_FOUND)

def process_external_payload(payload):
    print(f"Processing external payload: {payload}")
    return {"status": "Payload processed internally", "received_data": payload}

class DirectRewardView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request):
        shop_api_key = request.data.get("shop_api_key")
        reward_uuid = request.data.get("reward_uuid")
        customer_id = request.data.get("customer_id")
        points = int(request.data.get("points", 0))
        expiry_date_str = request.data.get("expiry_date")  # Expecting 'YYYY-MM-DD'

        if not (shop_api_key and reward_uuid and customer_id and points > 0):
            return Response({"error": "Missing or invalid required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(api_key=shop_api_key)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid shop API key"}, status=status.HTTP_404_NOT_FOUND)

        shop_limit, _ = ShopRewardLimit.objects.get_or_create(shop=shop)

        if shop_limit.used_points + points > shop_limit.max_points:
            return Response({"error": "Shop has reached its total reward limit."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reward_type = RewardType.objects.get(reward_uuid=reward_uuid)
            reward_condition = reward_type.condition
        except RewardType.DoesNotExist:
            return Response({"error": "Invalid reward UUID"}, status=status.HTTP_404_NOT_FOUND)

        customer, _ = Customer.objects.get_or_create(customer_id=customer_id, shop=shop)
        now = timezone.now()
        previous_rewards = DirectReward.objects.filter(customer=customer, shop=shop, reward_type=reward_type)

        def get_recurring_filter(recurring_type):
            if recurring_type == "daily":
                return Q(created_at__date=now.date())
            elif recurring_type == "weekly":
                start = now - timedelta(days=now.weekday())
                end = start + timedelta(days=6)
                return Q(created_at__date__range=[start.date(), end.date()])
            elif recurring_type == "monthly":
                return Q(created_at__year=now.year, created_at__month=now.month)
            elif recurring_type == "quarterly":
                quarter = (now.month - 1) // 3 + 1
                start_month = 3 * (quarter - 1) + 1
                end_month = start_month + 2
                return Q(created_at__year=now.year, created_at__month__range=(start_month, end_month))
            elif recurring_type == "bi_annual":
                if now.month <= 6:
                    return Q(created_at__year=now.year, created_at__month__lte=6)
                else:
                    return Q(created_at__year=now.year, created_at__month__gte=7)
            elif recurring_type == "yearly":
                return Q(created_at__year=now.year)
            return Q()

        def get_next_recurring_eligible_date(recurring_type):
            if recurring_type == "daily":
                return (now + timedelta(days=1)).date()
            elif recurring_type == "weekly":
                start_of_next_week = now + timedelta(days=(7 - now.weekday()))
                return start_of_next_week.date()
            elif recurring_type == "monthly":
                next_month = now.replace(day=1) + timedelta(days=32)
                return next_month.replace(day=1).date()
            elif recurring_type == "quarterly":
                current_quarter = (now.month - 1) // 3 + 1
                next_quarter_start_month = 3 * current_quarter + 1
                year = now.year + (1 if next_quarter_start_month > 12 else 0)
                month = next_quarter_start_month if next_quarter_start_month <= 12 else next_quarter_start_month - 12
                return timezone.datetime(year, month, 1).date()
            elif recurring_type == "bi_annual":
                return timezone.datetime(now.year, 7, 1).date() if now.month <= 6 else timezone.datetime(now.year + 1, 1, 1).date()
            elif recurring_type == "yearly":
                return timezone.datetime(now.year + 1, 1, 1).date()
            return None

        # Recurring reward restriction
        recurring_filter = get_recurring_filter(reward_condition.recurring_type)
        recurring_count = previous_rewards.filter(recurring_filter).count()

        if reward_condition.recurring_type != "none" and recurring_count >= 1:
            next_eligible = get_next_recurring_eligible_date(reward_condition.recurring_type)
            return Response({
                "error": f"{reward_condition.recurring_type.title()} reward already used.",
                "next_eligible_date": str(next_eligible) if next_eligible else None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Max usage restriction
        if reward_condition.max_usage_per_user and previous_rewards.count() >= reward_condition.max_usage_per_user:
            return Response({"error": "Reward usage limit reached for this user."}, status=status.HTTP_400_BAD_REQUEST)

        # Duration restriction
        if reward_condition.duration_days:
            recent = previous_rewards.order_by("-created_at").first()
            if recent and (now - recent.created_at).days < reward_condition.duration_days:
                next_eligible = recent.created_at.date() + timedelta(days=reward_condition.duration_days)
                return Response({
                    "error": f"Reward can be used only once in {reward_condition.duration_days} days.",
                    "next_eligible_date": str(next_eligible)
                }, status=status.HTTP_400_BAD_REQUEST)

        # Handle expiry date based on reward_type.has_expiring_points
        expiry_date = None
        if reward_type.has_expiring_points:  # Assuming has_expiring_points is a boolean field in RewardType
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                    if expiry_date <= now.date():
                        return Response({"error": "Expiry date must be in the future."}, status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({"error": "Invalid expiry_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        elif expiry_date_str:
            # If has_expiring_points is False and vendor provided an expiry date, ignore it
            expiry_date = None  # Explicitly set to None to ignore provided expiry_date

        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(
                customer=customer,
                shop=shop,
                defaults={"points": 0}
            )
            wallet.points += points
            wallet.save()

            shop_limit.total_points_used += points
            shop_limit.used_points += points
            shop_limit.save()

            direct_reward = DirectReward.objects.create(
                shop=shop,
                reward_type=reward_type,
                customer=customer,
                points=points,
                expiry_date=expiry_date  # Will be None if has_expiring_points is False
            )

            # Update customer tier
            update_tier_data = {"customer_id": customer_id, "shop_id": shop.id}
            update_tier_view = UpdateCustomerTierView()
            update_response = update_tier_view.post(
                request=type('Request', (), {'data': update_tier_data, 'user': request.user})()
            )
            tier_data = update_response.data if update_response.status_code == 200 else {"error": "Tier update failed"}

            # Refresh wallet to reflect any external changes (optional, kept for consistency)
            wallet.refresh_from_db()

        serializer = DirectRewardSerializer(direct_reward)
        return Response({
            "reward": serializer.data,
            "wallet_balance": wallet.points,
            "shop_used_points": shop_limit.used_points,
            "total_points_used": shop_limit.total_points_used,
            "tier_info": tier_data
        }, status=status.HTTP_201_CREATED)
    
class SetShopRewardLimitView(APIView):
    """API for managing shop reward point limits."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Set or update the total reward point limit for a shop."""
        shop_api_key = request.data.get("shop_api_key")
        max_points = request.data.get("max_points")

        if not (shop_api_key and max_points):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(api_key=shop_api_key)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid shop API key"}, status=status.HTTP_404_NOT_FOUND)

        shop_limit, _ = ShopRewardLimit.objects.get_or_create(shop=shop)

        max_points = int(max_points)

        
        shop_limit.total_points_used += shop_limit.used_points 
        shop_limit.used_points = 0 
        shop_limit.max_points = max_points
        shop_limit.save()

        return Response({
            "shop_id": shop.id,
            "max_points": shop_limit.max_points,
            "used_points": shop_limit.used_points,
            "total_points_used": shop_limit.total_points_used 
        }, status=status.HTTP_200_OK)

    def put(self, request):
        """Update the total reward point limit for a shop."""
        shop_api_key = request.data.get("shop_api_key")
        new_limit = request.data.get("new_limit")

        if not (shop_api_key and new_limit):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(api_key=shop_api_key)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid shop API key"}, status=status.HTTP_404_NOT_FOUND)

        try:
            shop_limit = ShopRewardLimit.objects.get(shop=shop)
            new_limit = int(new_limit)

            shop_limit.total_points_used += shop_limit.used_points  
            shop_limit.used_points = 0 
            shop_limit.max_points = new_limit
            shop_limit.save()
        except ShopRewardLimit.DoesNotExist:
            return Response({"error": "Reward limit not set."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "shop_id": shop.id,
            "max_points": shop_limit.max_points,
            "total_points_used": shop_limit.total_points_used,
            "message": "Reward limit updated successfully."
        }, status=status.HTTP_200_OK)
    
class GetAllRulesView(APIView):
    """API endpoint for retrieving all reward-related configurations for a shop."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all reward rules and configurations for a shop."""
        shop_id = request.query_params.get("shop_id")
        if not shop_id:
            return Response({"error": "Shop ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        response_data = {
            "currency_configurations": CurrencyConversionSerializer(CurrencyConversion.objects.filter(shop=shop), many=True).data,
            "purchase_rules": PurchaseRuleSerializer(PurchaseRule.objects.filter(shop=shop), many=True).data,
            "direct_rewards": DirectRewardSerializer(DirectReward.objects.filter(shop=shop), many=True).data,
            "reward_types": RewardTypeSerializer(RewardType.objects.all(), many=True).data
        }
        return Response(response_data, status=status.HTTP_200_OK)

# --------------------------------------------------------------rewards section end   ---------------------------------------------------------------------------------

# --------------------------------------------------------------redeem  section start  ---------------------------------------------------------------------------------


class ProcessPurchaseWalletView(APIView):
    def generate_code(self, wallet_tx):
        if wallet_tx.code or not wallet_tx.redeemable:
            return None
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        wallet_tx.code = code
        wallet_tx.save()
        return code

    def post(self, request):
        customer_id = request.data.get("customer_id")
        api_key = request.data.get("api_key")
        amount = request.data.get("amount")

        if not all([customer_id, api_key, amount]):
            return Response({"error": "customer_id, api_key, and amount are required"}, status=400)

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        try:
            shop = Shop.objects.get(api_key=api_key)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid API key"}, status=401)

        with transaction.atomic():
            # Get or create a Customer instance specific to this shop-customer pair
            customer, created = Customer.objects.get_or_create(
                customer_id=customer_id,
                shop=shop,
                defaults={"shop": shop}  # Redundant but ensures clarity
            )

            # Get or create a Wallet for this customer-shop pair
            wallet, created = Wallet.objects.get_or_create(
                customer=customer,
                shop=shop,
                defaults={"points": 0}
            )

            # Fetch applicable purchase rule
            purchase_rule = PurchaseRule.objects.filter(
                shop=shop,
                min_purchase_amount__lte=amount,
                max_purchase_amount__gte=amount
            ).first()
            if not purchase_rule:
                print(f"No rule found for shop {shop.name} (id={shop.id}), amount {amount}")
            points = purchase_rule.points if purchase_rule else 0
            redeemable = purchase_rule.redeemable if purchase_rule else False
            expiration_days = purchase_rule.expiration_days if purchase_rule else None
            redeemable_shops = [shop.name for shop in purchase_rule.redeemable_shops.all()] if purchase_rule and redeemable else []

            # Update wallet points
            wallet.points += points
            wallet.save()

            # Set expiration date if applicable
            expires_at = None
            if expiration_days is not None:
                expires_at = timezone.now() + timedelta(days=expiration_days)

            # Create wallet transaction
            wallet_tx = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                points=points,
                redeemable=redeemable,
                description="Purchase processed via API",
                expires_at=expires_at
            )

            # Generate code if redeemable
            code = None
            if redeemable:
                code = self.generate_code(wallet_tx)
                if not code:
                    return Response({"error": "Failed to generate code"}, status=500)

    # Update customer tier
            update_tier_data = {"customer_id": customer_id, "shop_id": shop.id}
            update_tier_view = UpdateCustomerTierView()
            update_response = update_tier_view.post(
                request=type('Request', (), {'data': update_tier_data, 'user': request.user})()
            )
            tier_data = update_response.data if update_response.status_code == 200 else {"error": "Tier update failed"}

            return Response({
                "message": f"Purchase processed successfully for {shop.name}. {points} points allocated.",
                "customer_id": customer_id,
                "shop_id": shop.id,
                "code": code,
                "status": "not_redeemed" if code else None,
                "redeemable_shops": redeemable_shops,  
                "tier_info": tier_data
            }, status=200)
class ViewWalletTransactionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response({"error": "customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure customers is a queryset
        customers = Customer.objects.filter(customer_id=customer_id)
        if not isinstance(customers, QuerySet):  # Corrected to use QuerySet from django.db.models.query
            return Response({"error": "Internal error: customers is not a queryset"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not customers.exists():
            return Response({"error": "No customers found for this customer_id"}, status=status.HTTP_404_NOT_FOUND)

        # Debug: Print the customers queryset
        print(f"Customers: {list(customers)}")

        wallets = Wallet.objects.filter(customer__in=customers)
        direct_rewards = DirectReward.objects.filter(customer__in=customers)

        if not wallets.exists() and not direct_rewards.exists():
            return Response({"error": "No wallets or direct rewards found"}, status=status.HTTP_404_NOT_FOUND)

        wallet_transactions = WalletTransaction.objects.filter(wallet__in=wallets)
        wallet_serializer = WalletTransactionSerializer(wallet_transactions, many=True)

        direct_serializer = DirectRewardSerializer(direct_rewards, many=True)

        return Response({
            "customer_id": customer_id,
            "wallet_transactions": wallet_serializer.data,
            "direct_rewards": direct_serializer.data
        }, status=status.HTTP_200_OK)
            
            
# ___________________________________________________Multi shop section   ________________________________________


class GenerateCodeView(APIView):
    def post(self, request):
        transaction_id = request.data.get("transaction_id")
        if not transaction_id:
            return Response({"error": "transaction_id is required"}, status=400)

        try:
            with transaction.atomic(): 
                wallet_tx = WalletTransaction.objects.select_for_update().get(id=transaction_id) 
                if wallet_tx.code:
                    return Response({"error": "Code already generated for this transaction"}, status=400)
                if not wallet_tx.redeemable:
                    return Response({"error": "Transaction is not redeemable"}, status=400)

                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                wallet_tx.code = code
                wallet_tx.save()

                purchase_rule = PurchaseRule.objects.filter(
                    shop=wallet_tx.wallet.shop,
                    min_purchase_amount__lte=wallet_tx.amount,
                    max_purchase_amount__gte=wallet_tx.amount
                ).first()
                redeemable_shops = [shop.name for shop in purchase_rule.redeemable_shops.all()] if purchase_rule else []

                return Response({
                    "code": code,
                    "status": "not_redeemed" if not wallet_tx.is_redeemed else "redeemed",
                    "redeemable_shops": redeemable_shops
                }, status=200)
        except WalletTransaction.DoesNotExist:
            return Response({"error": "Transaction not found"}, status=404)
        
        
class RedeemCodeView(APIView):
    def post(self, request):
        code = request.data.get("code")
        target_api_key = request.data.get("target_api_key")
        total_amount = request.data.get("total_amount")
        customer_id = request.data.get("customer_id")

        if not all([code, target_api_key, total_amount, customer_id]):
            return Response(
                {"error": "code, target_api_key, total_amount, and customer_id are required"},
                status=400
            )

        try:
            total_amount = float(total_amount)
            if total_amount <= 0:
                return Response({"error": "total_amount must be positive"}, status=400)
        except (ValueError, TypeError):
            return Response({"error": "total_amount must be a number"}, status=400)

        try:
            wallet_tx = WalletTransaction.objects.get(code=code)
        except WalletTransaction.DoesNotExist:
            return Response({"error": "Invalid code"}, status=404)

        try:
            target_shop = Shop.objects.get(api_key=target_api_key)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid target API key"}, status=401)

        customer = wallet_tx.wallet.customer
        if customer.customer_id != customer_id:
            return Response({"error": "This code does not belong to the provided customer"}, status=403)

        if wallet_tx.is_redeemed:
            return Response({
                "message": f"Code {code} has already been redeemed at {wallet_tx.redeemed_at_shop.name}.",
                "status": "redeemed"
            }, status=400)

        purchase_rule = PurchaseRule.objects.filter(
            shop=wallet_tx.wallet.shop,
            min_purchase_amount__lte=wallet_tx.amount,
            max_purchase_amount__gte=wallet_tx.amount
        ).first()
        if not purchase_rule or not purchase_rule.redeemable:
            return Response({"error": "This transaction is not redeemable"}, status=400)

        redeemable_shops = purchase_rule.redeemable_shops.all()
        if target_shop not in redeemable_shops:
            return Response({
                "error": f"Code {code} cannot be redeemed at {target_shop.name}.",
                "redeemable_shops": [shop.name for shop in redeemable_shops]
            }, status=400)

        discount_percentage = purchase_rule.discount_percentage
        if discount_percentage is None:
            return Response({"error": "No discount percentage defined for this code"}, status=500)

        discount_amount = (float(discount_percentage) / 100) * total_amount
        new_amount = total_amount - discount_amount

        with transaction.atomic():
            target_wallet, _ = Wallet.objects.get_or_create(
                customer=customer,
                shop=target_shop,
                defaults={"points": 0}
            )
            target_wallet.points += wallet_tx.points
            target_wallet.save()

            wallet_tx.is_redeemed = True
            wallet_tx.redeemed_at_shop = target_shop
            wallet_tx.save()

            return Response({
                "message": f"Code {code} successfully redeemed at {target_shop.name}. {wallet_tx.points} points added.",
                "status": "redeemed",
                "original_amount": total_amount,
                "discount_amount": discount_amount,
                "new_amount": new_amount
            }, status=200)
            
# --------------------------------------------------------------redeem  section end   ---------------------------------------------------------------------------------

            
# -------------------------------------------------------------wallet section start----------------------------------------------------------------------------------


class CentralizedWalletView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response({"error": "customer_id is required"}, status=400)

        customers = Customer.objects.filter(customer_id=customer_id)
        if not customers.exists():
            return Response({"error": "Customer not found"}, status=404)

        total_transaction_points = 0
        total_direct_reward_points = 0
        wallet_details = []
        current_time = timezone.now()

        for customer in customers:
            wallets = Wallet.objects.filter(customer=customer)
            direct_rewards = DirectReward.objects.filter(customer=customer)

            for wallet in wallets:
                active_transactions = wallet.transactions.filter(
                    Q(expires_at__gt=current_time) | Q(expires_at__isnull=True),
                    is_redeemed=False
                )
                transaction_points = sum(tx.points for tx in active_transactions)
                direct_reward_points = sum(
                    dr.points for dr in direct_rewards.filter(shop=wallet.shop)
                )

                total_transaction_points += transaction_points
                total_direct_reward_points += direct_reward_points

                wallet_details.append({
                    "shop_id": wallet.shop.id,
                    "shop_name": wallet.shop.name,
                    "transaction_points": transaction_points,
                    "direct_reward_points": direct_reward_points,
                    "total_combined_points": transaction_points + direct_reward_points
                })

            wallet_shops = set(wallet.shop for wallet in wallets)
            direct_rewards_no_wallet = direct_rewards.exclude(shop__in=wallet_shops)
            for dr in direct_rewards_no_wallet:
                total_direct_reward_points += dr.points
                wallet_details.append({
                    "shop_id": dr.shop.id,
                    "shop_name": dr.shop.name,
                    "transaction_points": 0,
                    "direct_reward_points": dr.points,
                    "total_combined_points": dr.points
                })

        total_combined_points = total_transaction_points + total_direct_reward_points

        return Response({
            "customer_id": customer_id,
            "total_transaction_points": total_transaction_points,
            "total_direct_reward_points": total_direct_reward_points,
            "total_combined_points": total_combined_points,
            "wallet_breakdown": wallet_details
        }, status=200)
        
        
class ShopBasedWalletView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        customer_id = request.data.get("customer_id")
        api_key = request.data.get("api_key")

        if not customer_id or not api_key:
            return Response({"error": "customer_id and api_key are required"}, status=400)

        try:
            shop = Shop.objects.get(api_key=api_key)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid API key"}, status=404)

        try:
            customer = Customer.objects.get(customer_id=customer_id, shop=shop)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found for this shop"}, status=404)

        try:
            wallet = Wallet.objects.get(customer=customer, shop=shop)
            current_time = timezone.now()
            active_transactions = wallet.transactions.filter(
                Q(expires_at__gt=current_time) | Q(expires_at__isnull=True),
                is_redeemed=False
            )
            transaction_points = sum(tx.points for tx in active_transactions)
        except Wallet.DoesNotExist:
            transaction_points = 0

        direct_reward_points = sum(
            dr.points for dr in DirectReward.objects.filter(customer=customer, shop=shop)
        )

        total_combined_points = transaction_points + direct_reward_points

        return Response({
            "customer_id": customer_id,
            "shop_id": shop.id,
            "shop_name": shop.name,
            "transaction_points": transaction_points,
            "direct_reward_points": direct_reward_points,
            "total_combined_points": total_combined_points
        }, status=200)
        
# -------------------------------------------------------------wallet section end----------------------------------------------------------------------------------

# ------------------------------------------------------------- Tier section start----------------------------------------------------------------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from .models import Shop, Tier
from .serializers import TierSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from .models import Shop, Tier
from .serializers import TierSerializer

class SetTierView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shop_id = request.data.get("shop_id")
        tiers = request.data.get("tiers")

        if not shop_id:
            return Response({"error": "shop_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not tiers or not isinstance(tiers, list):
            return Response({"error": "tiers must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
            if shop.owner != request.user:
                return Response({"error": "You do not own this shop"}, status=status.HTTP_403_FORBIDDEN)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            Tier.objects.filter(shop=shop).delete()

            for tier_data in tiers:
                name = tier_data.get("name")
                min_points = tier_data.get("min_points")
                max_points = tier_data.get("max_points")
                description = tier_data.get("description", "")

                if not all([name, min_points is not None, max_points is not None]):
                    return Response(
                        {"error": "name, min_points, and max_points are required for each tier"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    min_points = int(min_points)
                    max_points = int(max_points)
                    if min_points < 0 or max_points < 0 or min_points >= max_points:
                        return Response({"error": "Invalid point range"}, status=status.HTTP_400_BAD_REQUEST)
                except (ValueError, TypeError):
                    return Response(
                        {"error": "min_points and max_points must be integers"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check for duplicate tier name (even though we delete, just to be safe)
                if Tier.objects.filter(shop=shop, name=name).exists():
                    return Response(
                        {"error": f"Tier with name '{name}' already exists for this shop"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                Tier.objects.create(
                    shop=shop,
                    name=name,
                    min_points=min_points,
                    max_points=max_points,
                    description=description
                )

            serializer = TierSerializer(Tier.objects.filter(shop=shop), many=True)
            return Response({"tiers": serializer.data}, status=status.HTTP_201_CREATED)

    def put(self, request):
        tier_id = request.data.get("tier_id")
        name = request.data.get("name")
        min_points = request.data.get("min_points")
        max_points = request.data.get("max_points")
        description = request.data.get("description", "")

        if not tier_id:
            return Response({"error": "tier_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not all([name, min_points is not None, max_points is not None]):
            return Response({"error": "name, min_points, and max_points are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            min_points = int(min_points)
            max_points = int(max_points)
            if min_points < 0 or max_points < 0 or min_points >= max_points:
                return Response({"error": "Invalid point range"}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({"error": "min_points and max_points must be integers"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tier = Tier.objects.get(id=tier_id)
            if tier.shop.owner != request.user:
                return Response({"error": "You do not own this shop"}, status=status.HTTP_403_FORBIDDEN)
        except Tier.DoesNotExist:
            return Response({"error": "Tier not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if another tier in the same shop has the same name
        if Tier.objects.filter(shop=tier.shop, name=name).exclude(id=tier_id).exists():
            return Response(
                {"error": f"Another tier with name '{name}' already exists in this shop"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for overlapping points range
        if Tier.objects.filter(
            shop=tier.shop,
            min_points__lt=max_points,
            max_points__gt=min_points
        ).exclude(id=tier_id).exists():
            return Response(
                {"error": "This point range overlaps with another tier"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tier.name = name
        tier.min_points = min_points
        tier.max_points = max_points
        tier.description = description
        tier.save()

        return Response({"message": "Tier updated successfully"}, status=status.HTTP_200_OK)

    def get(self, request):
        shop_id = request.query_params.get("shop_id")
        if not shop_id:
            return Response({"error": "shop_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
            if shop.owner != request.user:
                return Response({"error": "You do not own this shop"}, status=status.HTTP_403_FORBIDDEN)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        tiers = Tier.objects.filter(shop=shop)
        serializer = TierSerializer(tiers, many=True)
        return Response({"tiers": serializer.data}, status=status.HTTP_200_OK)

    def delete(self, request):
        tier_id = request.data.get("tier_id")
        if not tier_id:
            return Response({"error": "tier_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tier = Tier.objects.get(id=tier_id)
            if tier.shop.owner != request.user:
                return Response({"error": "You do not own this shop"}, status=status.HTTP_403_FORBIDDEN)
            tier.delete()
            return Response({"message": "Tier deleted successfully"}, status=status.HTTP_200_OK)
        except Tier.DoesNotExist:
            return Response({"error": "Tier not found"}, status=status.HTTP_404_NOT_FOUND)



class UpdateCustomerTierView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        customer_id = request.data.get("customer_id")
        shop_id = request.data.get("shop_id")

        if not all([customer_id, shop_id]):
            return Response({"error": "customer_id and shop_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
            customer, _ = Customer.objects.get_or_create(customer_id=customer_id, shop=shop)  # Ensure customer exists
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get or create customer's wallet
        wallet, _ = Wallet.objects.get_or_create(
            customer=customer,
            shop=shop,
            defaults={"points": 0}
        )
        
        points = wallet.points

        # Find the appropriate tier
        tier = Tier.objects.filter(
            shop=shop,
            min_points__lte=points,
            max_points__gte=points
        ).first()

        if not tier:
            return Response({"error": "No matching tier found for customer's points"}, status=status.HTTP_400_BAD_REQUEST)

        # Update or create customer tier
        with transaction.atomic():
            customer_tier, created = CustomerTier.objects.get_or_create(
                customer=customer,
                shop=shop,
                defaults={"tier": tier}
            )
       
            now = timezone.now()
            tier_duration = timedelta(days=30)
            grace_period = timedelta(days=10)

            if created or customer_tier.tier != tier:
                old_tier = customer_tier.tier
                customer_tier.tier = tier
                customer_tier.assigned_at = now
                customer_tier.expires_at = now + tier_duration
                customer_tier.grace_period_expires_at = None
                customer_tier.save()

                status_message = "Tier assigned" if created else "No change"
                if old_tier and old_tier != tier:
                    status_message = "Tier upgraded" if old_tier.min_points < tier.min_points else "Tier downgraded"
            else:
                status_message = "No change"

            serializer = CustomerTierSerializer(customer_tier)
            return Response({
                "customer_tier": serializer.data,
                "status": status_message
            }, status=status.HTTP_200_OK)


class GetCustomerTierView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        shop_id = request.query_params.get("shop_id")

        if not all([customer_id, shop_id]):
            return Response({"error": "customer_id and shop_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
            customer = Customer.objects.get(customer_id=customer_id, shop=shop)
            customer_tier = CustomerTier.objects.get(customer=customer, shop=shop)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found for this shop"}, status=status.HTTP_404_NOT_FOUND)
        except CustomerTier.DoesNotExist:
            return Response({"error": "Customer tier not set"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomerTierSerializer(customer_tier)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class GetShopCustomerTiersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        shop_id = request.query_params.get("shop_id")
        if not shop_id:
            return Response({"error": "shop_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
            # Optionally restrict to shop owner
            if shop.owner != request.user:
                return Response({"error": "You do not own this shop"}, status=status.HTTP_403_FORBIDDEN)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get all customer tiers for this shop
        customer_tiers = CustomerTier.objects.filter(shop=shop).select_related('customer', 'tier', 'shop')

        if not customer_tiers.exists():
            return Response({"message": "No customers have tiers assigned for this shop yet"}, status=status.HTTP_200_OK)

        # Prepare response data
        response_data = []
        for customer_tier in customer_tiers:
            wallet = Wallet.objects.filter(customer=customer_tier.customer, shop=shop).first()
            points = wallet.points if wallet else 0  # Fallback to 0 if no wallet exists

            tier_data = {
                "customer_id": customer_tier.customer.customer_id,
                "tier": TierSerializer(customer_tier.tier).data if customer_tier.tier else None,
                "points": points,
                "updated_at": customer_tier.updated_at
            }
            response_data.append(tier_data)

        return Response({
            "shop_id": shop.id,
            "shop_name": shop.name,
            "customer_tiers": response_data
        }, status=status.HTTP_200_OK)
# -------------------------------------------------------------Tier section End----------------------------------------------------------------------------------
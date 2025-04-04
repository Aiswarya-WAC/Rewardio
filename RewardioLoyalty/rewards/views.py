import uuid
from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.timezone import now
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    PurchaseRule, CurrencyConversion, RewardCondition, RewardType, DirectReward,
    Shop, Customer, Wallet, ShopRewardLimit
)
from .serializers import (
    PurchaseRuleSerializer, CurrencyConversionSerializer,
    RewardConditionSerializer, RewardTypeSerializer, DirectRewardSerializer
)


class CreateAndUpdatePurchaseRuleView(APIView):
    """API endpoints for creating and updating purchase rules in a loyalty program."""

    def post(self, request, *args, **kwargs):
        """Create a new purchase rule for a shop."""
        try:
            shop_id = request.data.get("shop_id")
            shop = Shop.objects.get(id=shop_id)

           
            purchase_rule = PurchaseRule.objects.create(
                shop=shop,
                min_purchase_amount=request.data.get("min_purchase_amount"),
                max_purchase_amount=request.data.get("max_purchase_amount"),
                points=request.data.get("points")
            )

            serializer = PurchaseRuleSerializer(purchase_rule)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, rule_id):
        """Update an existing purchase rule."""
        try:
           
            purchase_rule = PurchaseRule.objects.get(id=rule_id)
            purchase_rule.min_purchase_amount = request.data.get("min_purchase_amount", purchase_rule.min_purchase_amount)
            purchase_rule.max_purchase_amount = request.data.get("max_purchase_amount", purchase_rule.max_purchase_amount)
            purchase_rule.points = request.data.get("points", purchase_rule.points)

            purchase_rule.save()

            serializer = PurchaseRuleSerializer(purchase_rule)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except PurchaseRule.DoesNotExist:
            return Response({"error": "Purchase Rule not found"}, status=status.HTTP_404_NOT_FOUND)


class ShopPurchaseRulesView(APIView):
    """API endpoint to retrieve all purchase rules for a specific shop."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, shop_id):
        """Get all purchase rules for a shop."""
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        purchase_rules = PurchaseRule.objects.filter(shop=shop)
        data = [
            {"id": rule.id, "min_purchase_amount": rule.min_purchase_amount, "max_purchase_amount": rule.max_purchase_amount, "points": rule.points}
            for rule in purchase_rules
        ]

        return Response({"purchase_rules": data}, status=status.HTTP_200_OK)


class CreateAndUpdateCurrencyConversionView(APIView):
    """API endpoints for managing currency conversion rules for points calculation."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create a new currency conversion rule for a shop."""
        shop_id = request.data.get("shop_id")
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        currency_conversion = CurrencyConversion.objects.create(
            shop=shop, currency=request.data.get("currency"), points_per_currency=request.data.get("points_per_currency")
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


class DirectRewardView(APIView):
    """API for assigning direct rewards to customers with various constraints."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Assign a direct reward and update wallet points with constraints."""
        shop_api_key = request.data.get("shop_api_key")
        reward_uuid = request.data.get("reward_uuid")
        customer_id = request.data.get("customer_id")
        points = int(request.data.get("points", 0))

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

        previous_rewards = DirectReward.objects.filter(
            customer=customer,
            shop=shop,
            reward_type=reward_type
        )

        def get_recurring_filter(recurring_type):
            """Generate filter for recurring reward conditions based on time period."""
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
            """Calculate next eligible date for recurring rewards."""
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
                if now.month <= 6:
                    return timezone.datetime(now.year, 7, 1).date()
                else:
                    return timezone.datetime(now.year + 1, 1, 1).date()
            elif recurring_type == "yearly":
                return timezone.datetime(now.year + 1, 1, 1).date()
            return None

        recurring_filter = get_recurring_filter(reward_condition.recurring_type)
        recurring_count = previous_rewards.filter(recurring_filter).count()

        if reward_condition.recurring_type != "none" and recurring_count >= 1:
            next_eligible = get_next_recurring_eligible_date(reward_condition.recurring_type)
            return Response({
                "error": f"{reward_condition.recurring_type.title()} reward already used.",
                "next_eligible_date": str(next_eligible) if next_eligible else None
            }, status=status.HTTP_400_BAD_REQUEST)

        if reward_condition.max_usage_per_user:
            total_given = previous_rewards.count()
            if total_given >= reward_condition.max_usage_per_user:
                return Response({"error": "Reward usage limit reached for this user."}, status=status.HTTP_400_BAD_REQUEST)

        if reward_condition.duration_days:
            recent = previous_rewards.order_by("-created_at").first()
            if recent and (now - recent.created_at).days < reward_condition.duration_days:
                next_eligible = recent.created_at.date() + timedelta(days=reward_condition.duration_days)
                return Response({
                    "error": f"Reward can be used only once in {reward_condition.duration_days} days.",
                    "next_eligible_date": str(next_eligible)
                }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(customer=customer, shop=shop)
            wallet.points += points
            wallet.save()

            shop_limit.total_points_used += points
            shop_limit.used_points += points
            shop_limit.save()

            direct_reward = DirectReward.objects.create(
                shop=shop,
                reward_type=reward_type,
                customer=customer,
                points=points
            )

        serializer = DirectRewardSerializer(direct_reward)
        return Response({
            "reward": serializer.data,
            "wallet_balance": wallet.points,
            "shop_used_points": shop_limit.used_points,
            "total_points_used": shop_limit.total_points_used
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
    
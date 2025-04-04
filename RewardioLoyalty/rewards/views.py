from datetime import timedelta
import random
import string
import uuid
import requests
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.timezone import now

from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import Shop
from .models import (
    PurchaseRule, CurrencyConversion, RewardCondition, RewardType, 
    DirectReward, Customer, Wallet, WalletTransaction, ShopRewardLimit
)
from .serializers import (
    PurchaseRuleSerializer, CurrencyConversionSerializer, 
    RewardConditionSerializer, RewardTypeSerializer, 
    DirectRewardSerializer, WalletTransactionSerializer, WalletSerializer
)




class CreateAndUpdatePurchaseRuleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shop_id = request.data.get("shop_id")
        min_amount = request.data.get("min_purchase_amount")
        max_amount = request.data.get("max_purchase_amount")
        points = request.data.get("points")
        redeemable = request.data.get("redeemable", False)
        redeemable_shops_ids = request.data.get("redeemable_shops", [])

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

        try:
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

        try:
            with transaction.atomic():
                purchase_rule = PurchaseRule.objects.create(
                    shop=shop,
                    min_purchase_amount=min_amount,
                    max_purchase_amount=max_amount,
                    points=points,
                    redeemable=redeemable
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


# ___________________________________________________ rewards wallet section ________________________________________

# rewards/views.py
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
            customer, _ = Customer.objects.get_or_create(customer_id=customer_id)
            wallet, created = Wallet.objects.get_or_create(
                customer=customer,
                shop=shop,
                defaults={"purchase_points": 0}
            )
            purchase_rule = PurchaseRule.objects.filter(
                shop=shop,
                min_purchase_amount__lte=amount,
                max_purchase_amount__gte=amount
            ).first()
            if not purchase_rule:
                print(f"No rule found for shop {shop.name} (id={shop.id}), amount {amount}")
            points = purchase_rule.points if purchase_rule else 0
            redeemable = purchase_rule.redeemable if purchase_rule else False
            redeemable_shops = [shop.name for shop in purchase_rule.redeemable_shops.all()] if purchase_rule and redeemable else []

            wallet.purchase_points += points
            wallet.save()

            wallet_tx = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                points=points,
                redeemable=redeemable,
                description="Purchase processed via API"
            )

            code = None
            if redeemable:
                code = self.generate_code(wallet_tx)
                if not code:
                    return Response({"error": "Failed to generate code"}, status=500)

            return Response({
                "message": f"Purchase processed successfully for {shop.name}. {points} points allocated.",
                "code": code,
                "status": "not_redeemed" if code else None,
                "redeemable_shops": redeemable_shops
            }, status=200)
            
class ViewWalletDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]  

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response(
                {"error": "customer_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        wallets = Wallet.objects.filter(customer__customer_id=customer_id)
        if not wallets.exists():
            return Response(
                {"error": "No wallets found for this customer"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = WalletSerializer(wallets, many=True) 
        return Response(serializer.data, status=status.HTTP_200_OK)
            
class ViewWalletTransactionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response(
                {"error": "customer_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        wallets = Wallet.objects.filter(customer__customer_id=customer_id)
        if not wallets.exists():
            return Response(
                {"error": "No wallets found for this customer"},
                status=status.HTTP_404_NOT_FOUND
            )

        transactions = WalletTransaction.objects.filter(wallet__in=wallets)
        serializer = WalletTransactionSerializer(transactions, many=True)

        return Response({
            "customer_id": customer_id,
            "transactions": serializer.data
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

        if not all([code, target_api_key]):
            return Response({"error": "code and target_api_key are required"}, status=400)

        try:
            wallet_tx = WalletTransaction.objects.get(code=code)  # Renamed to avoid conflict
            target_shop = Shop.objects.get(api_key=target_api_key)
        except WalletTransaction.DoesNotExist:
            return Response({"error": "Invalid code"}, status=404)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid target API key"}, status=401)

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

        with transaction.atomic(): 
            customer = wallet_tx.wallet.customer
            target_wallet, _ = Wallet.objects.get_or_create(
                customer=customer,
                shop=target_shop,
                defaults={"purchase_points": 0}
            )
            target_wallet.purchase_points += wallet_tx.points
            target_wallet.save()

            wallet_tx.is_redeemed = True
            wallet_tx.redeemed_at_shop = target_shop
            wallet_tx.save()

            return Response({
                "message": f"Code {code} successfully redeemed at {target_shop.name}. {wallet_tx.points} points added.",
                "status": "redeemed"
            }, status=200)
            
class GetWalletView(APIView):
    def get(self, request):
        customer_id = request.data.get("customer_id")
        api_key = request.data.get("api_key")  
        if not customer_id or not api_key:
            return Response({"error": "customer_id and api_key are required"}, status=400)

        try:
            shop = Shop.objects.get(api_key=api_key)
            wallet = Wallet.objects.get(customer__customer_id=customer_id, shop=shop)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data, status=200)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid API key"}, status=404)
        except Wallet.DoesNotExist:
            return Response({"error": "Wallet not found"}, status=404)

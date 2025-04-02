from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from authentication.models import Shop
from .models import PurchaseRule, CurrencyConversion, RewardType, DirectReward,Customer
from .serializers import (
    PurchaseRuleSerializer, CurrencyConversionSerializer, 
    RewardTypeSerializer, DirectRewardSerializer
)
from .serializers import WalletSerializer
class CreateAndUpdatePurchaseRuleView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Assuming you want authentication

    def post(self, request, *args, **kwargs):
        shop_id = request.data.get("shop_id")
        min_amount = request.data.get("min_purchase_amount")
        max_amount = request.data.get("max_purchase_amount")
        points = request.data.get("points")

        # Validate required fields
        if not all([shop_id, min_amount, max_amount, points]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check for overlapping rules
        if PurchaseRule.objects.filter(
            shop=shop,
            min_purchase_amount__lt=max_amount,  # New rule's min is less than existing max
            max_purchase_amount__gt=min_amount    # New rule's max is greater than existing min
        ).exists():
            return Response({"error": "Overlapping purchase rule exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Create a new purchase rule for the shop
        purchase_rule = PurchaseRule.objects.create(
            shop=shop,
            min_purchase_amount=min_amount,
            max_purchase_amount=max_amount,
            points=points
        )

        serializer = PurchaseRuleSerializer(purchase_rule)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, rule_id):
        try:
            # Retrieve the existing purchase rule
            purchase_rule = PurchaseRule.objects.get(id=rule_id)

            # Get new values, defaulting to existing ones if not provided
            min_amount = request.data.get("min_purchase_amount", purchase_rule.min_purchase_amount)
            max_amount = request.data.get("max_purchase_amount", purchase_rule.max_purchase_amount)
            points = request.data.get("points", purchase_rule.points)

            # Check if the range is unchanged
            range_unchanged = (
                str(min_amount) == str(purchase_rule.min_purchase_amount) and
                str(max_amount) == str(purchase_rule.max_purchase_amount)
            )

            # Only check for overlap if the range is being modified
            if not range_unchanged and PurchaseRule.objects.filter(
                shop=purchase_rule.shop,
                min_purchase_amount__lt=max_amount,
                max_purchase_amount__gt=min_amount
            ).exclude(id=rule_id).exists():
                return Response({"error": "Overlapping purchase rule exists."}, status=status.HTTP_400_BAD_REQUEST)

            # Update the purchase rule with new data
            purchase_rule.min_purchase_amount = min_amount
            purchase_rule.max_purchase_amount = max_amount
            purchase_rule.points = points

            # Save the updated rule
            purchase_rule.save()

            # Serialize the updated rule
            serializer = PurchaseRuleSerializer(purchase_rule)
            
            # Customize the response to explicitly include shop_id
            response_data = serializer.data
            response_data['shop_id'] = purchase_rule.shop.id  # Add shop_id explicitly
            
            return Response(response_data, status=status.HTTP_200_OK)

        except PurchaseRule.DoesNotExist:
            return Response({"error": "Purchase Rule not found"}, status=status.HTTP_400_BAD_REQUEST)



class CreateAndUpdateCurrencyConversionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
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
        try:
            currency_conversion = CurrencyConversion.objects.get(id=conversion_id)
        except CurrencyConversion.DoesNotExist:
            return Response({"error": "Currency Conversion not found"}, status=status.HTTP_400_BAD_REQUEST)

        currency_conversion.currency = request.data.get("currency", currency_conversion.currency)
        currency_conversion.points_per_currency = request.data.get("points_per_currency", currency_conversion.points_per_currency)
        currency_conversion.save()
        return Response(CurrencyConversionSerializer(currency_conversion).data, status=status.HTTP_200_OK)


class CreateAndUpdateRewardTypeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reward_type = RewardType.objects.create(
            reward_name=request.data.get("reward_name"), description=request.data.get("description")
        )
        return Response(RewardTypeSerializer(reward_type).data, status=status.HTTP_201_CREATED)

    def put(self, request, reward_type_id):
        try:
            reward_type = RewardType.objects.get(id=reward_type_id)
        except RewardType.DoesNotExist:
            return Response({"error": "Reward Type not found"}, status=status.HTTP_400_BAD_REQUEST)

        reward_type.reward_name = request.data.get("reward_name", reward_type.reward_name)
        reward_type.description = request.data.get("description", reward_type.description)
        reward_type.save()
        return Response(RewardTypeSerializer(reward_type).data, status=status.HTTP_200_OK)


class CreateAndUpdateDirectRewardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shop_id = request.data.get("shop_id")
        reward_type_id = request.data.get("reward_type_id")
        customer_id = request.data.get("customer_id")  
        points = request.data.get("points")

        if not customer_id:  
            return Response({"error": "Customer ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            
            shop = Shop.objects.get(id=shop_id)
            reward_type = RewardType.objects.get(id=reward_type_id)

           
            customer, created = Customer.objects.get_or_create(
                customer_id=customer_id,
                defaults={"shop": shop}  
            )

        except (Shop.DoesNotExist, RewardType.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
        direct_reward = DirectReward.objects.create(
            shop=shop,
            reward_type=reward_type,
            customer=customer,
            points=points
        )

        return Response(DirectRewardSerializer(direct_reward).data, status=status.HTTP_201_CREATED)   
        
    def put(self, request, direct_reward_id):
        try:
            direct_reward = DirectReward.objects.get(id=direct_reward_id)
            direct_reward.shop = Shop.objects.get(id=request.data.get("shop_id", direct_reward.shop.id))
            direct_reward.reward_type = RewardType.objects.get(id=request.data.get("reward_type_id", direct_reward.reward_type.id))
            direct_reward.customer = Customer.objects.get(customer_id=request.data.get("customer_id", direct_reward.customer.customer_id))  # Updating the customer
            direct_reward.points = request.data.get("points", direct_reward.points)
            direct_reward.save()
        except (DirectReward.DoesNotExist, Shop.DoesNotExist, RewardType.DoesNotExist, Customer.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DirectRewardSerializer(direct_reward).data, status=status.HTTP_200_OK)


    
class GetAllRulesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
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
# views.py (add to existing file)
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from authentication.models import Shop
from .models import Customer, PurchaseRule, Wallet, WalletTransaction

class ProcessPurchaseWalletView(APIView):
    def post(self, request):
        # Extract the e-commerce developer's JSON payload
        customer_id = request.data.get("customer_id")
        api_key = request.data.get("api_key")
        amount = request.data.get("amount")

        # Validate required fields
        if not all([customer_id, api_key, amount]):
            return Response(
                {"error": "customer_id, api_key, and amount are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify shop using api_key
        try:
            shop = Shop.objects.get(api_key=api_key)
        except Shop.DoesNotExist:
            return Response(
                {"error": "Invalid API key"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Atomic transaction to ensure data consistency
        with transaction.atomic():
            # Get or create customer
            customer, _ = Customer.objects.get_or_create(
                customer_id=customer_id,
                defaults={"shop": shop}  # Assuming Customer has a shop field
            )

            # Get or create wallet
            wallet, created = Wallet.objects.get_or_create(
                customer=customer,
                shop=shop,
                defaults={"points": 0}
            )

            # Calculate points based on PurchaseRule
            purchase_rule = PurchaseRule.objects.filter(
                shop=shop,
                min_purchase_amount__lte=amount,
                max_purchase_amount__gte=amount
            ).first()

            points = purchase_rule.points if purchase_rule else 0

            # Update wallet with calculated points
            wallet.points += points
            wallet.save()

            # Store transaction with provided amount and calculated points
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                points=points,
                description="Purchase processed via API"
            )

            # Return only a success message
            return Response(
                {"message": f"Purchase processed successfully. {points} points allocated."},
                status=status.HTTP_200_OK
            )
            
class ViewWalletDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Only you can access this

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response(
                {"error": "customer_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            wallet = Wallet.objects.get(customer__customer_id=customer_id)
            serializer = WalletSerializer(wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found for this customer"},
                status=status.HTTP_404_NOT_FOUND
            )
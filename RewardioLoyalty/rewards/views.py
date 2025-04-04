from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from authentication.models import Shop
import random
import string
from django.db import transaction
from .models import (
    PurchaseRule, CurrencyConversion, RewardType, 
    DirectReward,Customer ,PurchaseRule, Wallet, WalletTransaction
)
from django.db import transaction
from .serializers import (
    PurchaseRuleSerializer, CurrencyConversionSerializer, 
    RewardTypeSerializer, DirectRewardSerializer,WalletTransactionSerializer
)
from .serializers import WalletSerializer



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
            discount_percentage = None  


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

        from django.utils import timezone
        from datetime import timedelta

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
            expiration_days = purchase_rule.expiration_days if purchase_rule else None
            redeemable_shops = [shop.name for shop in purchase_rule.redeemable_shops.all()] if purchase_rule and redeemable else []

            wallet.purchase_points += points
            wallet.save()

            expires_at = None
            if expiration_days is not None:
                expires_at = timezone.now() + timedelta(days=expiration_days)

            wallet_tx = WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                points=points,
                redeemable=redeemable,
                description="Purchase processed via API",
                expires_at=expires_at
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

        from django.utils import timezone

        wallets = Wallet.objects.filter(customer__customer_id=customer_id)
        if not wallets.exists():
            return Response(
                {"error": "No wallets found for this customer"},
                status=status.HTTP_404_NOT_FOUND
            )

        wallet_data = []
        total_points = 0
        for wallet in wallets:
            expired_points = sum(
                tx.points for tx in wallet.transactions.filter(expires_at__lt=timezone.now())
            )
            available_points = max(wallet.purchase_points - expired_points, 0)
            wallet_data.append({
                "id": wallet.id,
                "customer_id": wallet.customer.customer_id,
                "shop_name": wallet.shop.name,
                "purchase_points": available_points
            })
            total_points += available_points

        response_data = {
            "wallets": wallet_data,
            "total_points": total_points
        }
        return Response(response_data, status=status.HTTP_200_OK)
            
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
            target_shop = Shop.objects.get(api_key=target_api_key)
            customer = Customer.objects.get(customer_id=customer_id)
        except WalletTransaction.DoesNotExist:
            return Response({"error": "Invalid code"}, status=404)
        except Shop.DoesNotExist:
            return Response({"error": "Invalid target API key"}, status=401)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)


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


        if wallet_tx.wallet.customer != customer:
            return Response({"error": "This code does not belong to the provided customer"}, status=403)


        discount_percentage = purchase_rule.discount_percentage
        if discount_percentage is None: 
            return Response({"error": "No discount percentage defined for this code"}, status=500)


        discount_amount = (float(discount_percentage) / 100) * total_amount
        new_amount = total_amount - discount_amount


        with transaction.atomic():
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
                "status": "redeemed",
                "original_amount": total_amount,
                "discount_amount": discount_amount,
                "new_amount": new_amount
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
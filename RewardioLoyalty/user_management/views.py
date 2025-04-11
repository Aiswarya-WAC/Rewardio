from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime
from rewards.models import Customer, Shop, Wallet, WalletTransaction, DirectReward, CustomerTier
from rewards.serializers import WalletTransactionSerializer, DirectRewardSerializer, CustomerTierSerializer

class ShopCustomerAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Extract query parameters
        shop_id = request.query_params.get("shop_id")
        start_date = request.query_params.get("start_date")  # Format: YYYY-MM-DD
        end_date = request.query_params.get("end_date")  # Format: YYYY-MM-DD

        if not shop_id:
            return Response({"error": "shop_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate shop existence and ownership
        try:
            shop = Shop.objects.get(id=shop_id)
            if shop.owner != request.user:
                return Response({"error": "You do not own this shop"}, status=status.HTTP_403_FORBIDDEN)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        # Validate and parse date filters
        date_filter = {}
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                date_filter["created_at__date__gte"] = start_date
            except ValueError:
                return Response({"error": "Invalid start_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                date_filter["created_at__date__lte"] = end_date
            except ValueError:
                return Response({"error": "Invalid end_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if start_date and end_date and start_date > end_date:
            return Response({"error": "start_date cannot be after end_date"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch all customers for the shop
        customers = Customer.objects.filter(shop=shop)
        if not customers.exists():
            return Response({"message": "No customers found for this shop"}, status=status.HTTP_200_OK)

        # Initialize response data
        response_data = {
            "shop_id": shop.id,
            "shop_name": shop.name,
            "total_customers": customers.count(),
            "total_purchase_api_calls": 0,
            "total_direct_reward_api_calls": 0,
            "total_purchase_points": 0,
            "total_direct_reward_points": 0,
            "grand_total_points": 0,
            "customers": []
        }

        # Aggregate data for each customer
        current_time = timezone.now()
        for customer in customers:
            wallet = Wallet.objects.filter(customer=customer, shop=shop).first()
            customer_tier = CustomerTier.objects.filter(customer=customer, shop=shop).first()

            # Calculate points
            total_points = wallet.points if wallet else 0

            # Fetch transactions and rewards
            wallet_transactions = WalletTransaction.objects.filter(wallet__customer=customer, wallet__shop=shop)
            direct_rewards = DirectReward.objects.filter(customer=customer, shop=shop)

            # Apply date filters if provided
            if date_filter:
                wallet_transactions = wallet_transactions.filter(**date_filter)
                direct_rewards = direct_rewards.filter(**date_filter)

            # Transaction statistics
            purchase_api_calls = wallet_transactions.count()
            direct_reward_api_calls = direct_rewards.count()
            purchase_points = wallet_transactions.aggregate(total=Sum('points'))['total'] or 0
            direct_reward_points = direct_rewards.aggregate(total=Sum('points'))['total'] or 0

            # Update shop-wide totals
            response_data["total_purchase_api_calls"] += purchase_api_calls
            response_data["total_direct_reward_api_calls"] += direct_reward_api_calls
            response_data["total_purchase_points"] += purchase_points
            response_data["total_direct_reward_points"] += direct_reward_points

            # Purchase history
            daily_purchase_rewards = wallet_transactions.order_by('created_at')
            direct_rewards_history = direct_rewards.order_by('created_at')

            # Reward management: Redeemed transactions
            redeemed_transactions = wallet_transactions.filter(is_redeemed=True)

            # Customer data
            customer_data = {
                "customer_id": customer.customer_id,
                "tier": CustomerTierSerializer(customer_tier).data if customer_tier else None,
                "points": total_points,
                "purchase_api_calls": purchase_api_calls,
                "direct_reward_api_calls": direct_reward_api_calls,
                "total_purchase_points": purchase_points,
                "total_direct_reward_points": direct_reward_points,
                "grand_total_points": purchase_points + direct_reward_points,
                "reward_management": {
                    "total_redeemed_transactions": redeemed_transactions.count(),
                }
            }
            response_data["customers"].append(customer_data)

        # Calculate shop-wide grand total
        response_data["grand_total_points"] = (
            response_data["total_purchase_points"] + response_data["total_direct_reward_points"]
        )

        return Response(response_data, status=status.HTTP_200_OK)
    
class UserAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Extract query parameters
        customer_id = request.query_params.get("customer_id")
        shop_id = request.query_params.get("shop_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not customer_id:
            return Response({"error": "customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate and parse date filters
        date_filter = {}
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                date_filter["created_at__date__gte"] = start_date
            except ValueError:
                return Response({"error": "Invalid start_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if end_date:
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                date_filter["created_at__date__lte"] = end_date
            except ValueError:
                return Response({"error": "Invalid end_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        if start_date and end_date and start_date > end_date:
            return Response({"error": "start_date cannot be after end_date"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch customers based on customer_id and optional shop_id
        customers_query = Customer.objects.filter(customer_id=customer_id)
        if shop_id:
            try:
                shop = Shop.objects.get(id=shop_id)
                customers_query = customers_query.filter(shop=shop)
            except Shop.DoesNotExist:
                return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        if not customers_query.exists():
            return Response({"error": "No customers found for this customer_id"}, status=status.HTTP_404_NOT_FOUND)

        # Initialize response data
        response_data = {
            "customer_id": customer_id,
            "shops": [],
            
            "reward_points_activity_log": {
                "purchase_based_rewards": [],
                "direct_rewards": []
            },
            "redemption_activity_log": {
                "total_redeemed_transactions": 0,
                "redeemed_transactions": []
            }
        }

        # Aggregate data for each customer-shop pair
        current_time = timezone.now()
        for customer in customers_query:
            shop = customer.shop
            wallet = Wallet.objects.filter(customer=customer, shop=shop).first()
            customer_tier = CustomerTier.objects.filter(customer=customer, shop=shop).first()

            # Calculate points
            total_points = wallet.points if wallet else 0

            # Fetch transactions and rewards
            wallet_transactions = WalletTransaction.objects.filter(wallet__customer=customer, wallet__shop=shop)
            direct_rewards = DirectReward.objects.filter(customer=customer, shop=shop)

            # Apply date filters if provided
            if date_filter:
                wallet_transactions = wallet_transactions.filter(**date_filter)
                direct_rewards = direct_rewards.filter(**date_filter)

            # Transaction statistics
            purchase_api_calls = wallet_transactions.filter(points__gt=0, is_redeemed=False).count()
            direct_reward_api_calls = direct_rewards.count()
            purchase_points = wallet_transactions.filter(points__gt=0, is_redeemed=False).aggregate(total=Sum('points'))['total'] or 0
            direct_reward_points = direct_rewards.aggregate(total=Sum('points'))['total'] or 0
            redeemed_points = abs(wallet_transactions.filter(is_redeemed=True, points__lt=0).aggregate(total=Sum('points'))['total'] or 0)

            # # Update totals
            # response_data["total_purchase_api_calls"] += purchase_api_calls
            # response_data["total_direct_reward_api_calls"] += direct_reward_api_calls
            # response_data["total_purchase_points"] += purchase_points
            # response_data["total_direct_reward_points"] += direct_reward_points
            # response_data["total_redeemed_points"] += redeemed_points

            # Purchase history (only positive, non-redeemed transactions)
            daily_purchase_rewards = wallet_transactions.filter(points__gt=0, is_redeemed=False).order_by('created_at')
            direct_rewards_history = direct_rewards.order_by('created_at')

            # Serialize and add date field for daily_purchase_based_rewards
            daily_rewards_data = WalletTransactionSerializer(daily_purchase_rewards, many=True).data
            for item in daily_rewards_data:
                item["date"] = datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ").date().isoformat()
                item.move_to_end("date", last=False)  # Move "date" to the top

            # Serialize and add date field for direct_rewards
            direct_rewards_data = DirectRewardSerializer(direct_rewards_history, many=True).data
            for item in direct_rewards_data:
                item["date"] = datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ").date().isoformat()
                item.move_to_end("date", last=False)  # Move "date" to the top

            # Reward management: All redeemed transactions
            redeemed_transactions = wallet_transactions.filter(is_redeemed=True).order_by('created_at')
            response_data["redemption_activity_log"]["total_redeemed_transactions"] = redeemed_transactions.count()
            redeemed_tx_list = []
            for tx in redeemed_transactions:
                prior_transactions = wallet_transactions.filter(created_at__lte=tx.created_at)
                balance_points = prior_transactions.aggregate(total=Sum('points'))['total'] or 0
                tx_data = {
                    "date": tx.created_at.date().isoformat(),  # Date only, at the top
                    "transaction_id": tx.id,
                    "points": abs(tx.points) if tx.points < 0 else tx.points,
                    "redeemed_at_shop": tx.redeemed_at_shop.name if tx.redeemed_at_shop else shop.name,
                    "redeemed_at": tx.created_at,
                    "type": "deduction" if tx.points < 0 else "purchase_redemption",
                    "balance_points": balance_points
                }
                redeemed_tx_list.append(tx_data)
            response_data["redemption_activity_log"]["redeemed_transactions"] = redeemed_tx_list

            # Shop details
            shop_data = {
                "shop_id": shop.id,
                "shop_name": shop.name,
                "tier": CustomerTierSerializer(customer_tier).data if customer_tier else None,
                "purchase_api_calls": purchase_api_calls,
                "direct_reward_api_calls": direct_reward_api_calls,
                "purchase_points": purchase_points,
                "direct_reward_points": direct_reward_points,
                "net_earned_unredeemed_points": purchase_points + direct_reward_points,
                "redeemed_points": redeemed_points,
                "total_points": total_points,
                
            }
            response_data["shops"].append(shop_data)

            # Append to purchase history
            response_data["reward_points_activity_log"]["purchase_based_rewards"] = daily_rewards_data
            response_data["reward_points_activity_log"]["direct_rewards"] = direct_rewards_data

        return Response(response_data, status=status.HTTP_200_OK)
    
from django.shortcuts import render

def user_analytics_view(request):
    return render(request, 'user_analytics.html')

def shop_analytics_view(request):
    return render(request, 'shop_analytics.html')
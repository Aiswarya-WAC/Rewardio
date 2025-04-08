# vendor_dashboard/views.py
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rewards.models import Shop
from django.db.models import Max
from .analytics import (
    points_summary, points_expiration, retention_rate, top_customers,
    points_over_time, customer_activity_trends, purchase_rule_utilization, churn_risk , customer_segmentation
)
from django.db.models import Sum
from rewards.models import Shop, Wallet, WalletTransaction, DirectReward, PurchaseRule, CurrencyConversion, ShopRewardLimit
from .serializers import (
    ShopSerializer, PurchaseRuleSerializer, CurrencyConversionSerializer, 
    ShopRewardLimitSerializer, DirectRewardSerializer, WalletTransactionSerializer
)
class VendorAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, shop_id): 
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid shop_id"}, status=status.HTTP_400_BAD_REQUEST)

        if shop.owner != request.user:
            return Response({"error": "You do not have permission to view this shop's analytics"}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "shop_id": shop.id,
            "shop_name": shop.name,
            "customer_segment":customer_segmentation(shop),
            "points_based_analytics": points_summary(shop),
            "points_expiration_rate": points_expiration(shop),
            "customer_retention_rate": retention_rate(shop),
            "top_customers_by_points": top_customers(shop),
            "time_based_analytics": {
                "points_over_time": points_over_time(shop),
                "customer_activity_trends": customer_activity_trends(shop)
            },
            "purchase_rule_utilization": purchase_rule_utilization(shop),
            "predictive_analytics": {
                "churn_risk": churn_risk(shop)
            }
            
        }, status=status.HTTP_200_OK)
        

# -----------------------------------------------------------dashboard section ----------------------------------------------------------------------------------




class VendorDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, shop_id):
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid shop_id"}, status=status.HTTP_400_BAD_REQUEST)

        # Check permission
        if shop.owner != request.user:
            return Response({"error": "You do not have permission to view this shop's dashboard"}, status=status.HTTP_403_FORBIDDEN)

        # Shop Details
        shop_details = ShopSerializer(shop).data

        # Shop Maximum Points
        reward_limit = ShopRewardLimit.objects.filter(shop=shop).first()
        max_points = reward_limit.max_points if reward_limit else None

        # Used Points
        wallets = Wallet.objects.filter(shop=shop)
        total_points_issued = (
            (WalletTransaction.objects.filter(wallet__in=wallets).aggregate(Sum('points'))['points__sum'] or 0) +
            (DirectReward.objects.filter(shop=shop).aggregate(Sum('points'))['points__sum'] or 0)
        )
        total_points_redeemed = WalletTransaction.objects.filter(wallet__in=wallets, is_redeemed=True).aggregate(Sum('points'))['points__sum'] or 0

        # Currency Details
        currency_conversion = CurrencyConversion.objects.filter(shop=shop).first()
        currency_details = CurrencyConversionSerializer(currency_conversion).data if currency_conversion else None

        # Shop Purchase Rules
        purchase_rules = PurchaseRule.objects.filter(shop=shop)
        purchase_rules_data = PurchaseRuleSerializer(purchase_rules, many=True).data

        # Direct Rewards Assigned
        direct_rewards = DirectReward.objects.filter(shop=shop)
        direct_rewards_data = DirectRewardSerializer(direct_rewards, many=True).data
        total_direct_points = sum(dr.points for dr in direct_rewards)

        # Recent Transactions (optional bonus)
        recent_transactions = WalletTransaction.objects.filter(wallet__in=wallets).order_by('-created_at')[:5]

        return Response({
            "shop_details": shop_details,
            "maximum_points": max_points,
            "used_points": {
                "total_points_issued": total_points_issued,
                "total_points_redeemed": total_points_redeemed
            },
            "currency_details": currency_details,
            "shop_purchase_rules": purchase_rules_data,
            "direct_rewards": {
                "list": direct_rewards_data,
                "total_direct_points": total_direct_points
            },

        }, status=status.HTTP_200_OK)
from django.db.models import Sum, Count, Q, Max , Min 
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from rewards.models import Shop, Customer, Wallet, WalletTransaction, DirectReward, PurchaseRule


def points_summary(shop):
    wallets = Wallet.objects.filter(shop=shop)
    issued_wallet = WalletTransaction.objects.filter(wallet__in=wallets).aggregate(Sum('points'))['points__sum'] or 0
    issued_direct = DirectReward.objects.filter(shop=shop).aggregate(Sum('points'))['points__sum'] or 0
    redeemed = WalletTransaction.objects.filter(wallet__in=wallets, is_redeemed=True).aggregate(Sum('points'))['points__sum'] or 0
    return {
        "total_points_issued": issued_wallet + issued_direct,
        "total_points_redeemed": redeemed,
        "redemption_rate": round((redeemed / (issued_wallet + issued_direct) * 100), 2) if (issued_wallet + issued_direct) > 0 else 0
    }

def points_expiration(shop):
    wallets = Wallet.objects.filter(shop=shop)
    expired_points = WalletTransaction.objects.filter(
        wallet__in=wallets,
        expires_at__lt=timezone.now(),
        is_redeemed=False
    ).aggregate(Sum('points'))['points__sum'] or 0
    total_issued = WalletTransaction.objects.filter(wallet__in=wallets).aggregate(Sum('points'))['points__sum'] or 0
    return {
        "expired_points": expired_points,
        "expiration_rate": round((expired_points / total_issued * 100), 2) if total_issued > 0 else 0
    }

def retention_rate(shop):
    customers = Customer.objects.filter(shop=shop)
    returning_customers = customers.annotate(tx_count=Count('wallets__transactions')).filter(tx_count__gt=1).count()
    total_customers = customers.count()
    return {
        "total_customers": total_customers,
        "returning_customers": returning_customers,
        "retention_rate": round((returning_customers / total_customers * 100), 2) if total_customers > 0 else 0
    }

def top_customers(shop):
    customers = Customer.objects.filter(shop=shop).annotate(
        total_points=Sum('wallets__points') + Sum('directreward__points')
    ).order_by('-total_points')[:5]
    return [
        {"customer_id": c.customer_id, "total_points": c.total_points or 0}
        for c in customers
    ]

def points_over_time(shop):
    wallets = Wallet.objects.filter(shop=shop)
    wallet_data = WalletTransaction.objects.filter(wallet__in=wallets).annotate(
        period=TruncMonth('created_at')
    ).values('period').annotate(
        issued=Sum('points'),
        redeemed=Sum('points', filter=Q(is_redeemed=True))
    ).order_by('period')
    direct_data = DirectReward.objects.filter(shop=shop).annotate(
        period=TruncMonth('created_at')
    ).values('period').annotate(issued=Sum('points')).order_by('period')
    return {
        "wallet_points": [
            {"period": d['period'].strftime('%Y-%m'), "issued": d['issued'], "redeemed": d['redeemed'] or 0}
            for d in wallet_data
        ],
        "direct_points": [
            {"period": d['period'].strftime('%Y-%m'), "issued": d['issued']}
            for d in direct_data
        ]
    }

def customer_activity_trends(shop):
    wallets = Wallet.objects.filter(shop=shop)
    tx_counts = WalletTransaction.objects.filter(wallet__in=wallets).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(count=Count('id')).order_by('month')
    return [
        {"month": t['month'].strftime('%Y-%m'), "transactions": t['count']}
        for t in tx_counts
    ]

def purchase_rule_utilization(shop):
    rules = PurchaseRule.objects.filter(shop=shop)
    utilization = []
    for rule in rules:
        tx_count = WalletTransaction.objects.filter(
            wallet__shop=shop,
            amount__gte=rule.min_purchase_amount,
            amount__lte=rule.max_purchase_amount
        ).count()
        utilization.append({
            "rule_id": rule.id,
            "points": rule.points,
            "min_amount": float(rule.min_purchase_amount),
            "max_amount": float(rule.max_purchase_amount),
            "usage_count": tx_count
        })
    return utilization

def churn_risk(shop):
    threshold = timezone.now() - timedelta(days=30)
    at_risk = Customer.objects.filter(
        shop=shop
    ).annotate(
        last_tx=Max('wallets__transactions__created_at')
    ).filter(
        Q(last_tx__lt=threshold) | Q(last_tx__isnull=True)
    ).count()
    total_customers = Customer.objects.filter(shop=shop).count()
    return {
        "at_risk_customers": at_risk,
        "churn_risk_percentage": round((at_risk / total_customers * 100), 2) if total_customers > 0 else 0
    }
    
def customer_segmentation(shop):
    threshold = timezone.now() - timedelta(days=30)
    customers = Customer.objects.filter(shop=shop)
    total_customers = customers.count()
    active = customers.filter(wallets__transactions__created_at__gte=threshold).distinct().count()
    inactive = total_customers - active
    high_value_threshold = customers.annotate(total_points=Sum('wallets__points') + Sum('directreward__points')).order_by('-total_points')[:int(total_customers * 0.1)].aggregate(Min('total_points'))['total_points__min'] or 0
    high_value = customers.filter(Q(wallets__points__gte=high_value_threshold) | Q(directreward__points__gte=high_value_threshold)).count()
    return {
        "active_customers": active,
        "inactive_customers": inactive,
        "high_value_customers": high_value
    }
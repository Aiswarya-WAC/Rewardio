# customer/urls.py
from django.urls import path
from customer.views import TriggerDeductPointsView, TriggerDirectRewardView, TriggerProcessPurchaseWalletView

urlpatterns = [
    path('api/trigger-deduct-points/', TriggerDeductPointsView.as_view(), name='trigger_deduct_points'),
    path('api/trigger-direct-rewards/', TriggerDirectRewardView.as_view(), name='trigger_direct_rewards'),
    path('api/trigger-process-purchase-wallet/', TriggerProcessPurchaseWalletView.as_view(), name='trigger_process_purchase_wallet'),
]
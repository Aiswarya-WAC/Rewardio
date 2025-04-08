# customer/urls.py
from django.urls import path
from customer.views import TriggerDeductPointsView, TriggerDirectRewardView

urlpatterns = [
    path('api/trigger-deduct-points/', TriggerDeductPointsView.as_view(), name='trigger_deduct_points'),
    path('api/trigger-direct-rewards/', TriggerDirectRewardView.as_view(), name='trigger_direct_rewards'),
]
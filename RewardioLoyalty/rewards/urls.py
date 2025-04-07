from django.urls import path
from .views import (
    
    CreateAndUpdatePurchaseRuleView, 
    CreateAndUpdateCurrencyConversionView, 
    RewardTypeView, 
    DirectRewardView, 
    GetAllRulesView, 
    SetShopRewardLimitView,
    RewardConditionView,
)

from .views import CreateAndUpdatePurchaseRuleView, CreateAndUpdateCurrencyConversionView, GetAllRulesView
from . import views 
urlpatterns = [
    # Purchase Rules
    path('create-purchase-rule/', CreateAndUpdatePurchaseRuleView.as_view(), name='create-purchase-rule'),
    path('update-purchase-rule/<int:rule_id>/', CreateAndUpdatePurchaseRuleView.as_view(), name='update-purchase-rule'),
 

    path("shop-reward-limit/", SetShopRewardLimitView.as_view(), name="shop-reward-limit"),
    # Currency Conversion
    path('create-currency-conversion/', CreateAndUpdateCurrencyConversionView.as_view(), name='create-currency-conversion'),
    path('update-currency-conversion/<int:conversion_id>/', CreateAndUpdateCurrencyConversionView.as_view(), name='update-currency-conversion'),

     # Reward Conditions
    path('reward-conditions/', RewardConditionView.as_view(), name='reward-conditions'),
    path("reward-conditions/<int:condition_id>/", RewardConditionView.as_view(), name="reward-condition-detail"),

    # Reward Types
    path("rewards/", RewardTypeView.as_view(), name="reward-types-list"),
    path("rewards/<int:reward_id>/", RewardTypeView.as_view(), name="reward-type-detail"),

    # Direct Rewards (Assign Rewards to Customers)
    path('direct-rewards/', DirectRewardView.as_view(), name='direct-rewards'),
    # Get All Rules
    path('all-rules/', GetAllRulesView.as_view(), name='get-all-rules'),
    
    path('process-purchase-wallet/', views.ProcessPurchaseWalletView.as_view(), name='process_purchase_wallet'),
    path('view-wallet-details/', views.ViewWalletDetailsView.as_view(), name='view_wallet_details'),
    
    path('view-tansaction-details/',views.ViewWalletTransactionsView.as_view(), name ='view-transaction-details'),
    path('generate-code/', views.GenerateCodeView.as_view(), name='generate_code'),
    path('redeem-code/', views.RedeemCodeView.as_view(), name='redeem_code'),
]

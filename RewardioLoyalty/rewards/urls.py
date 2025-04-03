from django.urls import path
from .views import CreateAndUpdatePurchaseRuleView, CreateAndUpdateCurrencyConversionView, CreateAndUpdateRewardTypeView, CreateAndUpdateDirectRewardView, GetAllRulesView
from . import views 
urlpatterns = [
    path('create-purchase-rule/', CreateAndUpdatePurchaseRuleView.as_view(), name='create-purchase-rule'),
    path('update-purchase-rule/<int:rule_id>/', CreateAndUpdatePurchaseRuleView.as_view(), name='update-purchase-rule'),
    
    path('create-currency-conversion/', CreateAndUpdateCurrencyConversionView.as_view(), name='create-currency-conversion'),
    path('update-currency-conversion/<int:conversion_id>/', CreateAndUpdateCurrencyConversionView.as_view(), name='update-currency-conversion'),
    
    path('create-reward-type/', CreateAndUpdateRewardTypeView.as_view(), name='create-reward-type'),
    path('update-reward-type/<int:reward_type_id>/', CreateAndUpdateRewardTypeView.as_view(), name='update-reward-type'),
    
    path('create-direct-reward/', CreateAndUpdateDirectRewardView.as_view(), name='create-direct-reward'),
    path('update-direct-reward/<int:direct_reward_id>/', CreateAndUpdateDirectRewardView.as_view(), name='update-direct-reward'),
    
    path('all-rules/', GetAllRulesView.as_view(), name='get-all-rules'),
    
    path('process-purchase-wallet/', views.ProcessPurchaseWalletView.as_view(), name='process_purchase_wallet'),
    path('view-wallet-details/', views.ViewWalletDetailsView.as_view(), name='view_wallet_details'),
    
    path('view-tansaction-details/',views.ViewWalletTransactionsView.as_view(), name ='view-transaction-details'),
    path('generate-code/', views.GenerateCodeView.as_view(), name='generate_code'),
    path('redeem-code/', views.RedeemCodeView.as_view(), name='redeem_code'),
]

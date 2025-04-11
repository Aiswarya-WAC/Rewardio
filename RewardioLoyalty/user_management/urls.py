from django.urls import path
from .views import ShopCustomerAnalyticsView, UserAnalyticsView, shop_analytics_view, user_analytics_view

urlpatterns = [
    path('shop-customer-analytics/', ShopCustomerAnalyticsView.as_view(), name='shop-customer-analytics'),
    path('user-analytics/', UserAnalyticsView.as_view(), name='user-analytics'),
    path('user/', user_analytics_view, name='user_dashboard'),
    path('shop/', shop_analytics_view, name='shop_analytics'),
]

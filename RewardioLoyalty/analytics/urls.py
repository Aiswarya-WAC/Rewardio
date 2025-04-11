from django.urls import path
from analytics.views import VendorAnalyticsView,VendorDashboardView,DashboardFrontendView


urlpatterns = [
    path('analytics/<int:shop_id>/', VendorAnalyticsView.as_view(), name='vendor_analytics'),
    path('dashboard/<int:shop_id>/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('', DashboardFrontendView.as_view(), name='dashboard_frontend'),
]
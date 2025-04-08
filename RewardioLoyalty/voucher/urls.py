from django.urls import path
from .views import VoucherCreateView, ApplyVoucherView

urlpatterns = [
    path('api/vouchers/create/', VoucherCreateView.as_view(), name='voucher-create'),
    path('api/vouchers/apply/', ApplyVoucherView.as_view(), name='voucher-apply'),
]
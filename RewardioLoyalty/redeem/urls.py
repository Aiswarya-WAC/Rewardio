# redeem/urls.py
from django.urls import path
from .views import DeductPointsView

urlpatterns = [
    path('api/deduct-points/', DeductPointsView.as_view(), name='deduct_points'),
]
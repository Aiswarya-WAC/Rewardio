# customer/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from rest_framework.permissions import IsAuthenticated



#---------------- Redeem Payload -------------------#
class TriggerDeductPointsView(APIView):
    def post(self, request):
        # Hardcoded JSON payload
        payload = {
            "customer_id": "cust-001",
            "currency_code": "INR",
            "cart_amount": "2500",
            "shop_api_key": "9d12ac21c5d34645a44b24cffd4cd778",
            "points": 20
        }

        # Make an external HTTP call to DeductPointsView
        try:
            response = requests.post(
                'http://127.0.0.1:8000/api/deduct-points/',
                json=payload
            )
            return Response(response.json(), status=response.status_code)
        except requests.RequestException as e:
            return Response({"error": f"Failed to call deduct-points API: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#----- Direct Reward Payload -------#

class TriggerDirectRewardView(APIView):
    #permission_classes = [IsAuthenticated]
    def post(self, request):
        payload = {
            "shop_api_key": "12d06523-323c-4d3b-9b72-fad4975e5364",
            "reward_uuid": "484dd10d-bcf5-4e5f-a123-3a970ca9c56f",
            "customer_id": "cust-55",
            "points": 100,
            "expiry_date": "2026-12-31", 
        }
        try:
            response = requests.post(
                'http://127.0.0.1:8000/direct-rewards/',
                json=payload
            )
            print(f"Raw response: '{response.text}', Status: {response.status_code}")
            if response.status_code in (200, 201):
                return Response(response.json(), status=response.status_code)
            else:
                return Response({
                    "error": "Unexpected response from direct-rewards",
                    "status": response.status_code,
                    "details": response.text
                }, status=response.status_code)
        except requests.RequestException as e:
            return Response({"error": f"Failed to call direct-rewards API: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#---------------- Process Purchase Wallet -------------------#

class TriggerProcessPurchaseWalletView(APIView):
    def post(self, request):
        payload = {
            "customer_id": "newcust1",  # Consistent with previous triggers
            "api_key": "12d06523-323c-4d3b-9b72-fad4975e5364",  # Same shop API key
            "amount": "2200.00"  # Purchase amount to trigger points
        }
        try:
            response = requests.post(
                'http://127.0.0.1:8000/process-purchase-wallet/',
                json=payload
            )
            print(f"Raw response: '{response.text}', Status: {response.status_code}")
            if response.status_code in (200, 201):
                return Response(response.json(), status=response.status_code)
            else:
                return Response({
                    "error": "Unexpected response from process-purchase-wallet",
                    "status": response.status_code,
                    "details": response.text
                }, status=response.status_code)
        except requests.RequestException as e:
            return Response({"error": f"Failed to call process-purchase-wallet API: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
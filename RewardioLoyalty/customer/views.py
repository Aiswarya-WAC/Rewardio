# customer/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests



#---------------- Redeem Payload -------------------#
class TriggerDeductPointsView(APIView):
    def post(self, request):
        # Hardcoded JSON payload
        payload = {
            "customer_id": "cust-001",
            "currency_code": "INR",
            "cart_amount": "2500",
            "shop_api_key": "1a0788b4-3117-46b9-85f2-1fe15e79197c",
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
    def post(self, request):
        payload = {
            "shop_api_key": "2cb17347-5a21-40f5-a882-96fc743ce219",
            "reward_uuid": "6a873418-a7ec-46ca-8a0f-434ca490527b",
            "customer_id": "cust-001",
            "points": 10
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
            "api_key": "7b290d19-5c24-47af-a8f4-0e87b070d928",  # Same shop API key
            "amount": "100.00"  # Purchase amount to trigger points
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
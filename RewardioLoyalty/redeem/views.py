# redeem/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rewards.models import Customer, Wallet, CurrencyConversion, WalletTransaction
from authentication.models import Shop
from django.shortcuts import get_object_or_404
from django.db import transaction  # For atomic transactions
import math  # For rounding

def process_external_payload(payload):
    print(f"Processing external payload: {payload}")
    return {"status": "Payload processed internally", "received_data": payload}

class DeductPointsView(APIView):
    def post(self, request):
        try:
            # Get the data from request
            customer_id = request.data.get('customer_id')
            currency_code = request.data.get('currency_code')
            cart_amount = request.data.get('cart_amount')
            shop_api_key = request.data.get('shop_api_key')
            points = request.data.get('points')

            # Validate input
            if not all([customer_id, currency_code, cart_amount, shop_api_key, points]):
                return Response(
                    {"error": "customer_id, currency_code, cart_amount, shop_api_key, and points are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate cart_amount
            try:
                cart_amount = float(cart_amount)
                if cart_amount <= 0:
                    raise ValueError
            except ValueError:
                return Response(
                    {"error": "Invalid cart_amount value"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate points
            try:
                points = int(points)
                if points <= 0:
                    raise ValueError
            except ValueError:
                return Response(
                    {"error": "Invalid points value"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get shop using api_key
            shop = get_object_or_404(Shop, api_key=shop_api_key)

            # Get customer by customer_id
            customer = get_object_or_404(Customer, customer_id=customer_id)
            
            # Get wallet for this customer and shop
            wallet = get_object_or_404(Wallet, customer=customer, shop=shop)

            # Get currency conversion for this specific shop (moved up)
            currency_conversion = get_object_or_404(
                CurrencyConversion,
                shop=shop,
                currency=currency_code
            )

            # Condition 1: Check if wallet has at least 1 point
            if wallet.points <= 1:
                return Response(
                    {"error": "Wallet must have more than 1 point to redeem"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if enough points available
            if wallet.points < points:
                return Response(
                    {"error": "Insufficient points"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate amount equivalent to points being deducted
            points_per_currency = currency_conversion.points_per_currency
            deducted_amount = points / points_per_currency
            deducted_amount = round(deducted_amount)  # Condition 2: Round to nearest integer

            # Check if deducted amount doesn't exceed cart amount
            if deducted_amount > cart_amount:
                return Response(
                    {"error": "Deducted amount exceeds cart amount"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate remaining cart amount after deduction
            deducted_cart_amount = cart_amount - deducted_amount

            # Deduct points
            with transaction.atomic():
                wallet.points -= points
                wallet.save()

                # Log the redemption in WalletTransaction
                redemption_tx = WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=deducted_amount,
                    points=-points,  # Negative points to indicate deduction
                    redeemable=False,
                    is_redeemed=True,  # Mark as redeemed
                    description=f"Points redeemed: {points} for {deducted_amount} {currency_code}",
                    redeemed_at_shop=shop  # Explicitly set the shop where points were redeemed
                )

            # Prepare payload with hardcoded business_name and calculated values
            payload = request.data.copy()
            payload['deducted_amount'] = deducted_amount
            payload['deducted_cart_amount'] = deducted_cart_amount

            # Process payload internally
            external_result = process_external_payload(payload)
            print(f"Internal processing result: {external_result}")

            return Response({
                "message": "Points deducted successfully",
                "customer_id": customer_id,
                "currency_code": currency_code,
                "cart_amount": cart_amount,
                "shop_api_key": str(shop_api_key),
                "points_deducted": points,
                "deducted_amount": deducted_amount,
                "deducted_cart_amount": deducted_cart_amount,
                "remaining_points": wallet.points,
                "transaction_id": redemption_tx.id  # Return the transaction ID for reference
            }, status=status.HTTP_200_OK)

        except Shop.DoesNotExist:
            return Response({"error": "Invalid shop_api_key"}, status=status.HTTP_404_NOT_FOUND)
        except CurrencyConversion.DoesNotExist:
            return Response({"error": f"Currency conversion not found for {currency_code} in this shop"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
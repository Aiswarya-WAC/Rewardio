# redeem/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rewards.models import Customer, Wallet, CurrencyConversion
from authentication.models import Shop
from django.shortcuts import get_object_or_404

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

            # Get customer and verify they belong to this shop
            customer = get_object_or_404(Customer, customer_id=customer_id, shop=shop)

            # Get wallet
            wallet = get_object_or_404(Wallet, customer=customer, shop=shop)

            # Get currency conversion for this specific shop
            currency_conversion = get_object_or_404(
                CurrencyConversion,
                shop=shop,
                currency=currency_code
            )

            # Check if enough points available
            if wallet.purchase_points < points:  # Changed from wallet.points
                return Response(
                    {"error": "Insufficient points"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate amount equivalent to points being deducted
            points_per_currency = currency_conversion.points_per_currency
            deducted_amount = points / points_per_currency

            # Check if deducted amount doesn't exceed cart amount
            if deducted_amount > cart_amount:
                return Response(
                    {"error": "Deducted amount exceeds cart amount"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate remaining cart amount after deduction
            deducted_cart_amount = cart_amount - deducted_amount

            # Deduct points
            wallet.purchase_points -= points  # Changed from wallet.points
            wallet.save()

            return Response({
                "message": "Points deducted successfully",
                "customer_id": customer_id,
                "currency_code": currency_code,
                "cart_amount": cart_amount,
                "shop_api_key": str(shop_api_key),
                "points_deducted": points,
                "deducted_amount": deducted_amount,
                "deducted_cart_amount": deducted_cart_amount,
                "remaining_points": wallet.purchase_points  # Changed from wallet.points
            }, status=status.HTTP_200_OK)

        except Shop.DoesNotExist:
            return Response(
                {"error": "Invalid shop_api_key"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found or doesn't belong to this shop"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found for this customer"},
                status=status.HTTP_404_NOT_FOUND
            )
        except CurrencyConversion.DoesNotExist:
            return Response(
                {"error": f"Currency conversion not found for {currency_code} in this shop"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
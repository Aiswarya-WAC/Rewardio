from rest_framework import generics, views
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Voucher, VoucherUsage
from authentication.models import Shop
from .serializers import VoucherSerializer, ApplyVoucherSerializer

class VoucherCreateView(generics.CreateAPIView):
    queryset = Voucher.objects.all()
    serializer_class = VoucherSerializer

class ApplyVoucherView(APIView):
    def post(self, request):
        serializer = ApplyVoucherSerializer(data=request.data)
        if serializer.is_valid():
            voucher = serializer.validated_data['voucher']
            cart_amount = serializer.validated_data['cart_amount']
            cust_id = serializer.validated_data['cust_id']
            shop_api_key = serializer.validated_data['shop_api_key']

            # Get the shop instance
            shop = Shop.objects.get(api_key=shop_api_key)

            # Check discount eligibility
            discount = voucher.calculate_discount(cart_amount)
            if discount == 0:
                return Response({
                    'code': voucher.code,
                    'voucher_type': voucher.voucher_type,
                    'discount_applied': 0.0,
                    'new_cart_amount': float(cart_amount),
                    'message': 'Cart amount below minimum purchase requirement or no discount applicable'
                }, status=status.HTTP_200_OK)

            # Record usage
            VoucherUsage.objects.create(voucher=voucher, cust_id=cust_id, shop=shop)
            voucher.usage_count += 1
            voucher.save()

            # Prepare response
            response_data = {
                'code': voucher.code,
                'voucher_type': voucher.voucher_type,
                'discount_applied': float(discount),
                'new_cart_amount': float(cart_amount - discount),
            }
            if voucher.voucher_type == 'tier_based':
                response_data['tier'] = voucher.tier

            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
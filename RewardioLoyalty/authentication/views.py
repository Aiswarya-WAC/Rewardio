from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Shop
from .serializers import ShopSerializer, UserSerializer
from django.http import Http404
from utils . error_messages import Errormessages
from helpers . common import(
    error_response
)

class RegisterOwnerView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save() 
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShopView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data['owner'] = request.user.id
        serializer = ShopSerializer(data=data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        shops = Shop.objects.filter(owner=request.user)
        serializer = ShopSerializer(shops, many=True)
        return Response(serializer.data)
    
    
class ShopDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            shop = Shop.objects.get(pk=pk, owner=self.request.user)
            return shop
        except Shop.DoesNotExist:
            return error_response(Errormessages.ACCESS_DENIED.value )

    def get(self, request, pk):
        shop = self.get_object(pk)
        serializer = ShopSerializer(shop)
        return Response(serializer.data)
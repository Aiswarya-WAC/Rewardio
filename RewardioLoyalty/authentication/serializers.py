from rest_framework import serializers
from .models import Shop
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password'] 
        extra_kwargs = {'password': {'write_only': True}} 

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

 
class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'api_key', 'secret_key', 'created_at']
        read_only_fields = ['api_key', 'secret_key', 'created_at']
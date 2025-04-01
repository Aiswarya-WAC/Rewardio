from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import PurchaseRule, CurrencyConversion, RewardType, Shop, DirectReward
from .serializers import PurchaseRuleSerializer, CurrencyConversionSerializer, RewardTypeSerializer, DirectRewardSerializer

class CreateAndUpdatePurchaseRuleView(APIView):
    def post(self, request, *args, **kwargs):
        shop_id = request.data.get("shop_id")
        shop = Shop.objects.get(id=shop_id)

        # Create a new purchase rule for the shop
        purchase_rule = PurchaseRule.objects.create(
            shop=shop,
            min_purchase_amount=request.data.get("min_purchase_amount"),
            max_purchase_amount=request.data.get("max_purchase_amount"),
            points=request.data.get("points")
        )

        serializer = PurchaseRuleSerializer(purchase_rule)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, rule_id):
        try:
            # Retrieve the existing purchase rule
            purchase_rule = PurchaseRule.objects.get(id=rule_id)

            # Update the purchase rule with new data
            purchase_rule.min_purchase_amount = request.data.get("min_purchase_amount", purchase_rule.min_purchase_amount)
            purchase_rule.max_purchase_amount = request.data.get("max_purchase_amount", purchase_rule.max_purchase_amount)
            purchase_rule.points = request.data.get("points", purchase_rule.points)

            # Save the updated rule
            purchase_rule.save()

            serializer = PurchaseRuleSerializer(purchase_rule)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except PurchaseRule.DoesNotExist:
            return Response({"error": "Purchase Rule not found"}, status=status.HTTP_400_BAD_REQUEST)

class CreateAndUpdateCurrencyConversionView(APIView):
    def post(self, request, *args, **kwargs):
        shop_id = request.data.get("shop_id")
        shop = Shop.objects.get(id=shop_id)

        # Create a new currency conversion rule for the shop
        currency_conversion = CurrencyConversion.objects.create(
            shop=shop,
            currency=request.data.get("currency"),
            points_per_currency=request.data.get("points_per_currency")
        )

        serializer = CurrencyConversionSerializer(currency_conversion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, conversion_id, *args, **kwargs):
        try:
            # Retrieve the existing currency conversion rule
            currency_conversion = CurrencyConversion.objects.get(id=conversion_id)

            # Update the conversion rule with new data
            currency_conversion.currency = request.data.get("currency", currency_conversion.currency)
            currency_conversion.points_per_currency = request.data.get("points_per_currency", currency_conversion.points_per_currency)

            # Save the updated rule
            currency_conversion.save()

            serializer = CurrencyConversionSerializer(currency_conversion)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except CurrencyConversion.DoesNotExist:
            return Response({"error": "Currency Conversion not found"}, status=status.HTTP_400_BAD_REQUEST)


class CreateAndUpdateRewardTypeView(APIView):
    def post(self, request, *args, **kwargs):
        reward_type = RewardType.objects.create(
            reward_name=request.data.get("reward_name"),
            description=request.data.get("description")
        )

        serializer = RewardTypeSerializer(reward_type)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, reward_type_id, *args, **kwargs):
        try:
            # Retrieve the existing reward type by reward_type_id from the URL
            reward_type = RewardType.objects.get(id=reward_type_id)

            # Update the reward type with new data
            reward_type.reward_name = request.data.get("reward_name", reward_type.reward_name)
            reward_type.description = request.data.get("description", reward_type.description)

            # Save the updated reward
            reward_type.save()

            serializer = RewardTypeSerializer(reward_type)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except RewardType.DoesNotExist:
            return Response({"error": "Reward Type not found"}, status=status.HTTP_400_BAD_REQUEST)

class CreateAndUpdateDirectRewardView(APIView):
    def post(self, request, *args, **kwargs):
        shop_id = request.data.get("shop_id")
        reward_type_id = request.data.get("reward_type_id")
        points = request.data.get("points")
        
        try:
            shop = Shop.objects.get(id=shop_id)
            reward_type = RewardType.objects.get(id=reward_type_id)

            # Create the direct reward
            direct_reward = DirectReward.objects.create(
                shop=shop,
                reward_type=reward_type,
                points=points
            )

            serializer = DirectRewardSerializer(direct_reward)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_400_BAD_REQUEST)
        except RewardType.DoesNotExist:
            return Response({"error": "Reward Type not found"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, direct_reward_id, *args, **kwargs):
        try:
            # Retrieve the existing direct reward
            direct_reward = DirectReward.objects.get(id=direct_reward_id)

            # Update the direct reward with new data
            direct_reward.shop = Shop.objects.get(id=request.data.get("shop_id", direct_reward.shop.id))
            direct_reward.reward_type = RewardType.objects.get(id=request.data.get("reward_type_id", direct_reward.reward_type.id))
            direct_reward.points = request.data.get("points", direct_reward.points)

            # Save the updated reward
            direct_reward.save()

            serializer = DirectRewardSerializer(direct_reward)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except DirectReward.DoesNotExist:
            return Response({"error": "Direct Reward not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_400_BAD_REQUEST)
        except RewardType.DoesNotExist:
            return Response({"error": "Reward Type not found"}, status=status.HTTP_400_BAD_REQUEST)


class GetAllRulesView(APIView):
    def get(self, request, *args, **kwargs):
        # Retrieve all loyalty configurations
        currency_configs = CurrencyConversion.objects.all()
        purchase_rules = PurchaseRule.objects.all()
        direct_rewards = DirectReward.objects.all()
        reward_types = RewardType.objects.all()  # Retrieve all reward types

        # Serialize the data
        currency_config_serializer = CurrencyConversionSerializer(currency_configs, many=True)
        purchase_rule_serializer = PurchaseRuleSerializer(purchase_rules, many=True)
        direct_reward_serializer = DirectRewardSerializer(direct_rewards, many=True)
        reward_type_serializer = RewardTypeSerializer(reward_types, many=True)  # Serialize reward types

        # Combine all data in one response
        response_data = {
            "currency_configurations": currency_config_serializer.data,
            "purchase_rules": purchase_rule_serializer.data,
            "direct_rewards": direct_reward_serializer.data,
            "reward_types": reward_type_serializer.data  # Add reward types to the response
        }

        return Response(response_data)

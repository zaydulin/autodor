from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from useraccount.models import Profile
from .serializers import DeviceTokenSerializer


class UpdateDeviceTokenView(APIView):
    """
    API для обновления поля device_token у пользователя.
    Если указан 'id', обновляется device_token для указанного пользователя.
    Если 'id' не указан, обновляется для текущего пользователя.
    """
    permission_classes = []  # Убираем требование аутентификации

    def post(self, request, *args, **kwargs):
        # Получаем ID пользователя из запроса (если есть)
        user_id = request.data.get('id')

        if not user_id:
            return Response({"error": "Не указан id пользователя"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Ищем пользователя по ID
            user = Profile.objects.get(id=user_id)
        except Profile.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Сериализуем данные из запроса
        serializer = DeviceTokenSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Device token обновлен"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from mobiledevaise import serializers
from useraccount.models import Profile

class DeviceTokenSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления device_token пользователя"""

    class Meta:
        model = Profile
        fields = ['device_token']

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer


class SiaTokenRefreshSerializer(TokenRefreshSerializer):
    """Preserva o contrato 401 quando o dono do refresh já não existe."""

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except ObjectDoesNotExist as error:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                'no_active_account',
            ) from error

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserSerializer, CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Кастомний ендпоінт авторизації, що повертає токени 
    та профіль користувача згідно з контрактом.
    """
    serializer_class = CustomTokenObtainPairSerializer

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
def health_check(request):
    """Health-check для Uptime Robot — тримає Render-сервіс «живим». Без авторизації.

    Дозволено GET і HEAD: Uptime Robot за замовчуванням пінгує методом HEAD.
    """
    return Response({'status': 'ok', 'message': 'ERP Backend is alive!'}, status=200)
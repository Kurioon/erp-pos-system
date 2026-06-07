from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from .serializers import UserSerializer, CustomTokenObtainPairSerializer, UserListSerializer, UserCreateSerializer, UserUpdateSerializer
from .permissions import IsAdminRole
from django.contrib.auth import get_user_model

User = get_user_model()

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

class UserListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminRole]
    queryset = User.objects.all().order_by('-date_joined')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserListSerializer

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminRole]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserListSerializer

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()
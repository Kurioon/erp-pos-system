from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer

class UserMeView(APIView):
    # Доступ тільки для авторизованих користувачів із токеном
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # request.user автоматично визначається по JWT токену
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
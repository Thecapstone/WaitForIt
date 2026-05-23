from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView

class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            request.status
        except Exception as e:
            return Response({'message': 'Your page is not ready'})
        return Response({'message': 'Your page is ready'}, status=status.HTTP_200_OK)
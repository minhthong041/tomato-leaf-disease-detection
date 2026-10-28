from django.contrib.auth.models import update_last_login
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DiagnosisHistory
from .serializers import DiagnosisCreateSerializer, DiagnosisSerializer, RegisterSerializer
from .services import run_diagnosis


class RegisterView(generics.GenericAPIView):
    """POST /api/auth/register/ {email, fullname, password, accept_terms} -> {access, refresh}.

    Tạo tài khoản rồi trả luôn cặp token như khi đăng nhập, để frontend vào thẳng trang Tải ảnh.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # không cần đọc token cũ (nếu có) khi đăng ký

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class DiagnosisViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    """API chẩn đoán. Mỗi người dùng chỉ thấy các lần chẩn đoán của mình.

    POST   /api/diagnoses/       multipart "image" -> chạy pipeline ngay, trả kết quả (done hoặc failed)
    GET    /api/diagnoses/       danh sách, mới nhất trước, 20 mục/trang
    GET    /api/diagnoses/:id/   chi tiết
    PATCH  /api/diagnoses/:id/   {"is_bookmarked": true|false}
    """

    serializer_class = DiagnosisSerializer
    # Không có PUT (chỉ sửa một phần) và không có DELETE (giữ lịch sử)
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        return (
            DiagnosisHistory.objects.filter(user=self.request.user)
            .select_related('disease')
            .prefetch_related('steps')
        )

    def create(self, request, *args, **kwargs):
        upload = DiagnosisCreateSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        history = DiagnosisHistory.objects.create(
            user=request.user, original_image=upload.validated_data['image'],
        )
        # Chạy đồng bộ: request trả về khi pipeline xong (ảnh 512x512 mất khoảng vài giây)
        run_diagnosis(history)
        history = self.get_queryset().get(pk=history.pk)
        return Response(self.get_serializer(history).data, status=status.HTTP_201_CREATED)

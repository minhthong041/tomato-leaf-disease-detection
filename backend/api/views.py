from django.contrib.auth.models import update_last_login
from rest_framework import generics, mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DiagnosisHistory
from .serializers import (
    DiagnosisCreateSerializer, DiagnosisSerializer, ErrorReportSerializer, FeedbackSerializer,
    RegisterSerializer,
)
from .services import run_diagnosis

# Lọc danh sách chẩn đoán theo ?is_bookmarked=true|false
BOOKMARK_FILTER_PARAM = 'is_bookmarked'
BOOKMARK_FILTER_VALUES = {'true': True, '1': True, 'false': False, '0': False}
BOOKMARK_FILTER_ERROR = 'Tham số is_bookmarked chỉ nhận true hoặc false.'


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
    GET    /api/diagnoses/       danh sách, mới nhất trước, 20 mục/trang; ?is_bookmarked=true chỉ lấy kết quả đã lưu
    GET    /api/diagnoses/:id/   chi tiết
    PATCH  /api/diagnoses/:id/   {"is_bookmarked": true|false}
    """

    serializer_class = DiagnosisSerializer
    # Không có PUT (chỉ sửa một phần) và không có DELETE (giữ lịch sử)
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            DiagnosisHistory.objects.filter(user=self.request.user)
            .select_related('disease')
            .prefetch_related('steps')
        )
        if self.action == 'list':
            queryset = self.filter_bookmarked(queryset)
        return queryset

    def filter_bookmarked(self, queryset):
        """?is_bookmarked=true|false (không phân biệt hoa thường; 1/0 cũng được). Không có tham số thì lấy hết."""
        value = self.request.query_params.get(BOOKMARK_FILTER_PARAM)
        if value is None or value == '':
            return queryset
        try:
            is_bookmarked = BOOKMARK_FILTER_VALUES[value.strip().lower()]
        except KeyError:
            raise ValidationError({BOOKMARK_FILTER_PARAM: [BOOKMARK_FILTER_ERROR]})
        return queryset.filter(is_bookmarked=is_bookmarked)

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


class FeedbackCreateView(generics.CreateAPIView):
    """POST /api/feedbacks/ {history, title, description}.

    Chỉ gửi được cho lần chẩn đoán của chính mình; mã của người khác hoặc không tồn tại trả 404.
    Trạng thái duyệt (status) do quản trị viên đổi trong /admin/.
    """

    serializer_class = FeedbackSerializer


class ErrorReportCreateView(generics.CreateAPIView):
    """POST /api/error-reports/ {title, description}. Quản trị viên xử lý trong /admin/."""

    serializer_class = ErrorReportSerializer

    def perform_create(self, serializer):
        # Người gửi luôn là tài khoản đang đăng nhập, không nhận từ dữ liệu gửi lên
        serializer.save(user=self.request.user)

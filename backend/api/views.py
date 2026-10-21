from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .services import run_diagnosis
from .models import DiagnosisHistory
from .serializers import DiagnosisCreateSerializer, DiagnosisSerializer


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

from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import DiagnosisViewSet, ErrorReportCreateView, FeedbackCreateView, RegisterView

router = SimpleRouter()
# /diagnoses/ và /diagnoses/<id>/ — xem DiagnosisViewSet
router.register('diagnoses', DiagnosisViewSet, basename='diagnosis')

urlpatterns = [
    # POST {"email", "fullname", "password", "accept_terms": true} -> {"access", "refresh"} (đăng nhập luôn)
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    # POST {"email", "password"} -> {"access", "refresh"}
    path('auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
    # POST {"refresh"} -> {"access", "refresh"} (refresh cũ bị vô hiệu)
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    # POST {"refresh"} -> đăng xuất (đưa refresh token vào blacklist)
    path('auth/logout/', TokenBlacklistView.as_view(), name='auth-logout'),
    # POST {"history", "title", "description"} -> phản hồi kết quả chẩn đoán sai
    path('feedbacks/', FeedbackCreateView.as_view(), name='feedback-create'),
    # POST {"title", "description"} -> báo lỗi ứng dụng
    path('error-reports/', ErrorReportCreateView.as_view(), name='error-report-create'),
    *router.urls,
]

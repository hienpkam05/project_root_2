from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, UserProfileViewSet, LeaveRequestViewSet

router = DefaultRouter()
router.register("departments",DepartmentViewSet,basename="department")
router.register("profiles",UserProfileViewSet,basename="profile")
router.register("leave-requests",LeaveRequestViewSet,basename="leave-requests")

urlpatterns = [
    path("",include(router.urls,))
]

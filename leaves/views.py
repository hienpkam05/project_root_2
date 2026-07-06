from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets,status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Department, UserProfile, LeaveRequest, LeaveStatusHistory
from .serializers import DepartmentSerializer, UserProfileSerializer, LeaveRequestSerializer,LeaveStatusHistorySerializer
from .permissions import (
    CanAccessLeaveRequest,
    get_user_profile, is_admin, is_employee,
    is_manager, is_hr, 
)
from .paginations import CustomPageNumberPagination
# Create your views here.

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        user = request.user
        profile= getattr(user,"profile",None)
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff":user.is_staff,
            "is_superuser":user.is_supperuser,
            "role":profile.role if profile else None,
            "department_id":profile.department.id if profile and profile.department else None,
            "department_name": profile.department.name if profile and profile.department else None,
        })
class DepartmentViewSet(viewsets.ModelViewSet):
    queryset= Department.objects.all()
    serializer_class=DepartmentSerializer
    permission_classes= [IsAuthenticated]

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset= UserProfile.objects.all()
    serializer_class= UserProfileSerializer
    permission_classes=[IsAuthenticated]

class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class= LeaveRequestSerializer
    permission_classes= [IsAuthenticated,CanAccessLeaveRequest]
    pagination_class=CustomPageNumberPagination

    def get_queryset(self):
        user= self.request.user
        profile = get_user_profile(user)

        queryset = LeaveRequest.objects.select_related(
            "owner","department","manager_approved_by","deleted_by"
        ).filter(is_deleted=False).order_by("-created_at")

        if is_admin(user) or is_hr(user):
            return queryset
        if not profile:
            return LeaveRequest.objects.none()
        if is_employee(user):
            return queryset.filter(owner = user)
        if is_manager(user):
            return queryset.filter(department= profile.department)
        
        return LeaveRequest.objects.none()
    
    def perform_create(self, serializer):
        user= self.request.user
        profile = get_user_profile(user)

        serializer.save(
            owner=user,
            department= profile.department if profile else None,
            status= LeaveRequest.STATUS_DRAFT,
        )
         
    def create(self, request, *args, **kwargs):
        if not is_employee(request.user) and not is_admin(request.user):
            return Response({
                "status":"error",
                "message":"Chỉ nhân viên hoặc admin được tạo đơn nghỉ phép."
            },status=status.HTTP_403_FORBIDDEN)
        
        serializer= self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({
            "status":"success",
            "message": "Tạo đơn nghỉ phép thành công.",
            "data": serializer.data
        },status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        leave_request= self.get_object()
        if is_admin(request.user):
            response= super().update(request,*args,**kwargs)
            return Response({
                "status":"success",
                "message":"Sửa đơn nghỉ phép thành công.",
                "data":response.data
            },status=status.HTTP_200_OK)

        if leave_request.owner != request.user:
            return Response({
                "status":"error",
                "message":"Bạn chỉ được sửa đơn nghỉ phép của chính mình."
            },status=status.HTTP_403_FORBIDDEN)
        if leave_request.status not in [
            LeaveRequest.STATUS_DRAFT,
            LeaveRequest.STATUS_REJECTED,
        ]:
            return Response({
                "status":"error",
                "message":"Chỉ được sửa đơn ở trạng thái nháp hoặc bị từ chối."
            },status=status.HTTP_400_BAD_REQUEST)
        
        response=super().update(request,*args,**kwargs)
        return Response({
            "status":"success",
            "message":"Sửa đơn nghỉ phép thành công.",
            "data": response.data
        },status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        leave_request= self.get_object()
        user= request.user
        is_admin_user= is_admin(user)
        is_owner_of_daft= (
            leave_request.owner_id == user.id 
            and leave_request.status == LeaveRequest.STATUS_DRAFT
        )
        if not is_admin_user and is_owner_of_daft:
            return Response({
                "status":"error",
                "message": (
                    "Bạn chỉ được xóa đơn của chính mình"
                    "khi đơn còn ở trạng thái nháp.")
            },status=status.HTTP_403_FORBIDDEN)
        
        leave_request.is_deleted= True
        leave_request.deleted_at = timezone.now()
        leave_request.deleted_by= user

        leave_request.save(
            update_fields=[
                "is_deleted","deleted_at","deleted_by", "updated_at",
            ]
        )
        return Response({
            "status":"success",
            "message":"Đơn nghỉ phép đã được xóa mềm thành công."
        }, status=status.HTTP_200_OK)
    def _create_history(self,leave_request,old_status,new_status,user, reason=""):
        LeaveStatusHistory.objects.create(
            leave_request= leave_request,
            old_status=old_status,
            new_status= new_status,
            changed_by = user,
            reason= reason,
        )

    @action(detail=True,methods=["post"],url_path="submit")
    def submit(self,request,pk=None):
        with transaction.atomic(): # nguyên tác: tất cả thành công -> lưu toàn bộ || Có lỗi phát sinh -> rollback toàn bộ 
            leave_request= LeaveRequest.objects.select_for_update().get(pk=pk, is_deleted=False)

            if leave_request.owner != request.user and not is_admin(request.user):
                return Response({
                    "status":"error",
                    "message":"Bạn chỉ được gửi duyệt đơn của chính mình."
                },status=status.HTTP_403_FORBIDDEN)
            
            if leave_request.status not in [
                LeaveRequest.STATUS_DRAFT,
                LeaveRequest.STATUS_REJECTED
            ]:
                return Response({
                    "status":"error",
                    "message":"Chỉ đơn nháp hoặc bị từ chối mới được gửi duyệt."
                },status=status.HTTP_400_BAD_REQUEST)
            
            old_status = leave_request.status
            leave_request.status = LeaveRequest.STATUS_PENDING_MANAGER
            leave_request.save(update_fields=["status","updated_at"])
            self._create_history(leave_request,old_status,LeaveRequest.STATUS_PENDING_MANAGER, request.user,"Gửi duyệt")

            serializer= self.get_serializer(leave_request)
            return Response({
                "status":"success",
                "message":"Gửi đơn nghỉ phép lên trưởng phòng duyệt thành công.",
                "data": serializer.data
            },status=status.HTTP_200_OK)
        
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self,request,pk=None):
        with transaction.atomic():
            leave_request= LeaveRequest.objects.select_for_update().get(pk=pk,is_deleted= False)
            
            profile = get_user_profile(request.user)

            if not is_admin(request.user):
                if not is_manager(request.user):
                    return Response({
                        "status":"error",
                        "message":"Chỉ trưởng phòng | admin có thể được duyệt đơn."
                    },status=status.HTTP_403_FORBIDDEN)
                if not profile or leave_request.department != profile.department:
                    return Response({
                        "status": "error",
                        "message":"Bạn chỉ được duyệt đơn của phòng mình."
                    },status=status.HTTP_403_FORBIDDEN)
            if leave_request.status != LeaveRequest.STATUS_PENDING_MANAGER:
                return Response({
                    "status":"error",
                    "message": "Chỉ đơn đang chờ duyệt mới được duyệt."
                },status= status.HTTP_400_BAD_REQUEST)
            
            old_status= leave_request.status
            leave_request.status = LeaveRequest.STATUS_MANAGER_APPROVED
            leave_request.manager_approved_by = request.user
            leave_request.reject_reason = ""
            leave_request.save(update_fields=["status","manager_approved_by","updated_at"])
            self._create_history(leave_request,old_status,LeaveRequest.STATUS_MANAGER_APPROVED, request.user,"Duyệt đơn")

            serializer= self.get_serializer(leave_request)
            return Response({
                "status":"success",
                "message": "Duyệt đơn nghỉ phép thành công ",
                "data": serializer.data
            },status=status.HTTP_200_OK)
        
    @action(detail=True,methods=["post"],url_path="reject")
    def reject(self,request, pk=None):
        reject_reason= request.data.get("reject_reason","")
        # lấy giá trị của field reject_reason từ request body
        # Nếu client ko gửi field đó thì dùng giá trị mặc định là "" (chuỗi rỗng)
        leave_request= LeaveRequest.objects.select_for_update().get(pk=pk,is_deleted=False)
        profile= get_user_profile(request.user)
        if not is_admin(request.user):
            if not is_manager(request.user):
                return Response({
                    "status":"success",
                    "message":"Chỉ có trưởng phòng | admin được từ chối đơn."
                },status=status.HTTP_403_FORBIDDEN)
            if not profile and profile.department != leave_request.department:
                return Response({
                    "status":"error",
                    "message":"Bạn chỉ được phpes từ chối đơn của phòng mình."
                },status=status.HTTP_400_BAD_REQUEST)
        if leave_request.status != LeaveRequest.STATUS_PENDING_MANAGER:
            return Response({
                "status":"error",
                "message":"Chỉ đơn đang chờ duyệt mới được từ chối."
            },status=status.HTTP_400_BAD_REQUEST)
        
        old_status= leave_request.status
        leave_request.status= LeaveRequest.STATUS_REJECTED
        leave_request.reason =  reject_reason
        leave_request.save(update_fields=["status","reason","updated_at"])

        self._create_history(leave_request,old_status,LeaveRequest.STATUS_REJECTED,request.user, reject_reason)

        serializer= self.get_serializer(leave_request)

        return Response({
            "status":"success",
            "message":"Từ chối đơn nghỉ phép thành công.",
            "data": serializer.data
        },status= status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"],url_path="cancel")
    def cancel(self,request,pk=None):
        leave_request= LeaveRequest.objects.select_for_update.get(pk=pk,is_deleted= False)
        
        if request.user != leave_request.owner and not is_admin(request.user):
           return Response({
               "status":"error",
               "message":"bạn chỉ được phép sửa đơn nghỉ phép của chính mình."
           },status=status.HTTP_403_FORBIDDEN)
        if leave_request.status == LeaveRequest.STATUS_MANAGER_APPROVED:
            return Response({
                "status":"error",
                "message": "Không thể hủy đơn đã được duyệt."
            },status=status.HTTP_400_BAD_REQUEST)

        old_status= leave_request.status
        leave_request.status= LeaveRequest.STATUS_CANCELLED
        leave_request.save(update_field= ["status","updated_at"]) 
        self._create_history(leave_request,old_status,LeaveRequest.STATUS_CANCELLED,request.user,"Hủy đơn")

        serializer= self.get_serializer(leave_request)
        return Response({
            "status":"success",
            "message": "Đã Hủy đơn thành công.",
            "data": serializer.data
        },status=status.HTTP_200_OK)
    
    # Xem các đơn nghỉ phép đã bị xóa
    @action(detail=False,methods=["get"],url_path="trash")
    # detail=true => dùng cho 1 đối tượng cụ thể
    # detail =False => Dùng cho tập hợp
    def trash(self,request):
        if not is_admin(request.user) and not is_hr(request.user):
            return Response({
                "status":"error",
                "message":"Chỉ HR hoặc admin được xem thùng rác."
            },status= status.HTTP_403_FORBIDDEN)
        # select_related : khi lấy các đơn nghỉ phép , Django sẽ lấy 
        #luôn thông tin của các đối tượng liên quan như 
        queryset= LeaveRequest.objects.select_related(
            "owner","department","manager_approved_by","deleted_by"
        ).filter(is_deleted=True).order_by("-deleted_at")
        
        page= self.paginate_queryset(queryset)
        if page is not None:
            serializer= self.get_serializer(page,many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset,many=True)
        return Response({
            "status":"success",
            "message":"Danh sách đơn nghỉ phép đã bị ẩn.",
            "data":serializer.data
        },status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        if not is_admin(request.user) and not is_hr(request.user):
            return Response({
                "status": "error",
                "message": "Chỉ HR hoặc admin được khôi phục đơn từ thùng rác."
            }, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            leave_request = LeaveRequest.objects.select_for_update().get(pk=pk)

            if not leave_request.is_deleted:
                return Response({
                    "status": "error",
                    "message": "Đơn này chưa bị xóa mềm."
                }, status=status.HTTP_400_BAD_REQUEST)

            leave_request.is_deleted = False
            leave_request.deleted_at = None
            leave_request.deleted_by = None
            leave_request.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

        serializer = self.get_serializer(leave_request)
        return Response({
            "status": "success",
            "message": "Khôi phục đơn nghỉ phép thành công.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
        
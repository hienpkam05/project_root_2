from rest_framework.permissions import BasePermission
from .models import UserProfile, LeaveRequest

def get_user_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None
def is_admin(user):
    if user.is_superuser or user.is_staff:
        return True
    profile = get_user_profile(user)
    return profile is not None and profile.role == UserProfile.ROLE_ADMIN

def is_employee(user):
    profile= get_user_profile(user)
    return profile is not None and profile.role == UserProfile.ROLE_EMPLOYEE

def is_manager(user):
    profile = get_user_profile(user)
    return profile is not None and profile.role == UserProfile.ROLE_MANAGER

def is_hr(user):
    profile = get_user_profile(user)
    return profile is not None and profile.role == UserProfile.ROLE_HR

class CanAccessLeaveRequest(BasePermission):
    def has_object_permission(self, request, view, obj):
        user= request.user
        if is_admin(user) or is_hr(user):
            return True
        if is_employee(user):
            return obj.owner == user
        if is_manager(user):
            profile= get_user_profile(user)
            return profile is not None and obj.department == profile.department
        
        return False
        
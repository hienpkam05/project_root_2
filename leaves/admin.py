from django.contrib import admin
from .models import Department, UserProfile, LeaveRequest, LeaveStatusHistory
# Register your models here.

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display=["id","name"]
    search_fields=["name"]

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display=["id","user","department","role"]
    list_filter=["role","department"]
    search_fields= ['user__username']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display=[
        "id","owner","department","leave_type","start_date",
        "end_date","total_days","status","is_deleted","created_at"
    ]
    list_filter=["status","leave_type","department","is_deleted"]
    search_fields=["owner__username","reason"]

@admin.register(LeaveStatusHistory)
class LeaveStatusHistoryAdmin(admin.ModelAdmin):
    list_display= [
        "id","leave_request","old_status","new_status",
        "changed_by","created_at"
    ]
    list_filter=["old_status","new_status"]
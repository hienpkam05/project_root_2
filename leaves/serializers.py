from rest_framework import serializers
from .models import Department,UserProfile, LeaveRequest,LeaveStatusHistory

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model= Department
        fields=["id","name"]

class UserProfileSerializer(serializers.ModelSerializer):
    username= serializers.CharField(source="user.username",read_only=True)
    department_name= serializers.CharField(source="department.name",read_only=True)
    class Meta:
        model= UserProfile
        fields= ["id","username","department","department_name","role"]

class LeaveStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username= serializers.CharField(source="changed_by.username",read_only= True)
    class Meta:
        model=LeaveStatusHistory
        fields=[
            "id","old_status","new_status","changed_by",
            "changed_by_username","reason","created_at"
        ]
        read_only_fields= fields

class LeaveRequestSerializer(serializers.ModelSerializer):
    owner_username= serializers.CharField(source="owner.username",read_only=True)
    department_name=serializers.CharField(source="department.name",read_only=True)
    status_histories= LeaveStatusHistorySerializer(many=True,read_only=True)

    class Meta:
        model=LeaveRequest
        fields=[
            "id",
            "owner", "owner_username",
            "department", "department_name",
            "leave_type", "start_date", "end_date", "total_days",
            "reason", "manager_note", "hr_note", "status",
            "manager_approved_by", "hr_confirmed_by",
            "hr_confirmed_at", "is_deleted", "deleted_at", "deleted_by",
            "created_at", "updated_at",
            "status_histories",
        ]
        read_only_fields= [
            "id", "owner", "department", "status",
            "manager_approved_by", "hr_confirmed_by",
            "hr_confirmed_at", "is_deleted", "deleted_at", "deleted_by",
            "created_at", "updated_at", "status_histories",
        ]
    def validate_total_day(self,value):
        if value <=0:
            raise serializers.ValidationError(
                "Số ngày nghỉ phải lớn hơn 0."
            )
        return value
    def validate(self, attrs):
        start_date= attrs.get("start_date")
        end_date= attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu."}
            )
        return attrs
        
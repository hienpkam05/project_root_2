from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Department(models.Model):
    name=models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    ROLE_EMPLOYEE = "employee"
    ROLE_MANAGER = "manager"
    ROLE_HR= "hr"
    ROLE_ADMIN= "admin"

    ROLE_CHOICES= [
        (ROLE_EMPLOYEE,"Nhân viên"),
        (ROLE_MANAGER,"Trưởng phòng"),
        (ROLE_HR,"Nhân sự"),
        (ROLE_ADMIN,"Admin")
    ]
    user=models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    department= models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name= "user"
    )
    role= models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_EMPLOYEE
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class LeaveRequest(models.Model):
    TYPE_ANNUAL="annual"
    TYPE_SICK= "sick"
    TYPE_UNPAID="unpaid"
    TYPE_PERSONAL= "personal"

    LEAVE_TYPE_CHOICES=[
        (TYPE_ANNUAL,"Nghỉ phép năm"),
        (TYPE_SICK,"Nghỉ ốm"),
        (TYPE_UNPAID,"Nghỉ không lượng"),
        (TYPE_PERSONAL,"Nghỉ việc cá nhân"),
    ]
    STATUS_DRAFT='draft'
    STATUS_PENDING_MANAGER='peniding_manager'
    STATUS_MANAGER_APPROVED= "manager_approved"
    STATUS_REJECTED="rejected"
    STATUS_HR_CONFIRMED= "hr_confirmed"
    STATUS_CANCELLED="cancelled"

    STATUS_CHOICES=[
        (STATUS_DRAFT, "Nháp"),
        (STATUS_PENDING_MANAGER, "Chờ trưởng phòng duyệt"),
        (STATUS_MANAGER_APPROVED, "Trưởng phòng đã duyệt"),
        (STATUS_REJECTED, "Bị từ chối"),
        (STATUS_HR_CONFIRMED, "HR đã xác nhận"),
        (STATUS_CANCELLED, "Đã hủy"),
    ]

    owner=models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="leave_requests"
    )
    department=models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="leave_requests"
    )
    leave_type= models.CharField(
        max_length=30,
        choices=LEAVE_TYPE_CHOICES,
        default=TYPE_ANNUAL
    )

    start_date=models.DateField()
    end_date= models.DateField()
    total_days= models.PositiveIntegerField(default=1)
    reason= models.TextField()
    manager_note=models.TextField(blank=True)
    hr_note=models.TextField(blank=True)
    status= models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    manager_approved_by= models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manager_approved_leave_requests"
    )
    hr_confirmed_by= models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_confirmed_leave_requests"
    )
    hr_confirmed_at= models.DateTimeField(null=True,blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True,blank=True)
    deleted_by=models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_leave_requests"
    )
    created_at= models.DateTimeField(auto_now=True)
    updated_at= models.DateTimeField(auto_now=True)

    class Meta:
        indexes= [
            models.Index(fields=["is_deleted", "status"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_days__gt=0),
                name="leave_total_days_gt_0"
            )
        ]

    def __str__(self):
        return f"LeaveRequest #{self.id} - {self.owner.username}"
    
class LeaveStatusHistory(models.Model):
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="status_histories"
    )

    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_status_changes"
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.old_status} -> {self.new_status}"
              
from django.contrib import admin
from .models import User, JobPost, Application, VendorProfile, WorkerProfile
from .models import Group

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'role', 'email', 'is_staff')

@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    # आपके models.py के हिसाब से सही फील्ड्स:
    list_display = ('job_title', 'vendor_user', 'posted_at', 'status')

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    # 'worker' की जगह 'applicant' है आपके models.py में
    list_display = ('applicant', 'job', 'status', 'applied_at')

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    # आपके models.py में 'phone' है, 'phone_number' नहीं
    list_display = ('user', 'company_name', 'phone')

@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    # आपके models.py में 'skills' और 'phone' है
    list_display = ('user', 'skills', 'phone')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
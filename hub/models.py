import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  # Important for SystemCheckError fix

# 1. Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = (
        ('vendor', 'Vendor (Company)'),
        ('worker', 'Worker (Job Seeker)'),
    )
    phone_number = models.CharField(max_length=12, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='worker')
    
    # Ye rahi wo nayi field:
    last_seen = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} ({self.role})"

from django.db import models
from django.conf import settings
from django.utils import timezone

class JobPost(models.Model):
    vendor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'vendor'})
    company_name = models.CharField(max_length=100)
    # Nayi field niche add ki hai
    company_domain = models.CharField(max_length=100, null=True, blank=True) 
    
    job_title = models.CharField(max_length=100)
    salary = models.CharField(max_length=50)
    description = models.TextField()
    location = models.CharField(max_length=255, default="Farukhnagar")
    posted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='active') 
    
    required_skills = models.CharField(max_length=500, blank=True, null=True) 
    is_featured = models.BooleanField(default=False)
    featured_until = models.DateTimeField(null=True, blank=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='job_likes', blank=True)

    def total_likes(self):
        return self.likes.count()

    def is_currently_featured(self):
        if self.is_featured and self.featured_until:
            return self.featured_until > timezone.now()
        return False

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

# 3. Application Model
class Application(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
    ]

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    def __str__(self):
        return f"{self.applicant.username if self.applicant else 'Guest'} - {self.job.job_title} ({self.status})"

class WorkerProfile(models.Model):
    # Existing Fields
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile')
    email = models.EmailField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    photo = models.ImageField(upload_to='worker_photos/', null=True, blank=True)
    location = models.CharField(max_length=100, default="Farukhnagar")
    designation = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.ImageField(upload_to='workers/images/', null=True, blank=True) 
    
    # Engagement & Professional Fields
    likes_count = models.PositiveIntegerField(default=0) 
    work_category = models.CharField(max_length=50, default="Logistics")
    headline = models.CharField(max_length=150, blank=True)
    
    # 🟢 Nayi LinkedIn-style Fields add ki gayi hain:
    about = models.TextField(blank=True, null=True, help_text="Apne baare mein thoda likhein...")
    profile_banner = models.ImageField(upload_to='worker_banners/', null=True, blank=True)
    industry = models.CharField(max_length=100, default="Logistics")
    website = models.URLField(blank=True, null=True)

    # Experience & Salary
    last_company = models.CharField(max_length=150, blank=True, null=True)
    total_experience = models.CharField(max_length=50, blank=True)
    expected_salary = models.CharField(max_length=50, blank=True)

    # Details
    skills = models.TextField(null=True, blank=True)
    experience_summary = models.TextField(blank=True)
    work_history = models.TextField(blank=True)
    certifications = models.TextField(null=True, blank=True)
    
    # Verification
    is_aadhar_verified = models.BooleanField(default=False)
    verified_date = models.DateField(null=True, blank=True)
    is_available = models.BooleanField(default=True) # इसे जोड़ें

    def save(self, *args, **kwargs):
        if self.is_aadhar_verified and not self.verified_date:
            import datetime
            self.verified_date = datetime.date.today()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.work_category})"
    
# 5. Vendor Profile Model
class VendorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_profile')
    company_name = models.CharField(max_length=150)
    company_logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    description = models.TextField(blank=True)
    
    # --- Naye Fields (Trust Signals) ---
    about_us = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    company_size = models.CharField(max_length=50, choices=[
        ('1-10', '1-10 Employees'),
        ('11-50', '11-50 Employees'),
        ('50+', '50+ Employees')
    ], default='1-10')
    is_verified = models.BooleanField(default=False) # Hiring Badge logic

    def __str__(self):
        return self.company_name

# 6. Message Model
class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True, null=True) 
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    document = models.FileField(upload_to='chat_docs/', blank=True, null=True) 
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    # is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    # Yahan related_name='comments' add karna zaroori hai
    job = models.ForeignKey('JobPost', on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    
# 1. Activity (Posts) Model
class Post(models.Model):
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # Like ke liye many-to-many field add karein
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='post_likes', blank=True)

    def total_likes(self):
        return self.likes.count()

# 2. Skills Model
class Skill(models.Model):
    worker = models.ForeignKey('WorkerProfile', on_delete=models.CASCADE, related_name='worker_skills') # 👈 related_name badal diya
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    worker_profile = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'worker_profile')

from django.conf import settings
from django.db import models

# models.py mein ye structure rakhein
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifs', null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True)
    group = models.ForeignKey('Group', on_delete=models.CASCADE, null=True, blank=True) # Yahan comma hatayein
    # notification_type add karein filtering ke liye
    notification_type = models.CharField(max_length=50, default='general')

class Follow(models.Model):
    worker = models.ForeignKey('WorkerProfile', on_delete=models.CASCADE, related_name='following')
    vendor = models.ForeignKey('VendorProfile', on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('worker', 'vendor') # Ek worker ek vendor ko ek hi baar follow kar sakta hai

# models.py
class Worker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to='workers/images/')
    designation = models.CharField(max_length=100) # e.g., Logistics Manager

from django.db import models
# hub/models.py

class Group(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_groups', 
        null=True, 
        blank=True
    )
    members = models.ManyToManyField(User, related_name='joined_groups', blank=True)

    def __str__(self):
        return self.name
    
from django.db import models
from django.conf import settings  # settings ko import karna zaroori hai

class Invitation(models.Model):
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    
    # Yahan 'User' ki jagah settings.AUTH_USER_MODEL use karein
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_invitations')
    
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'receiver')

    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username}"
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages # Success messages ke liye
from .models import JobPost, WorkerProfile, Application, Message, Comment
from .forms import JobPostForm, WorkerProfileForm
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import WorkerProfile
from django.db.models import Q
from .models import WorkerProfile, VendorProfile, JobPost
from .models import Group as Group, WorkerProfile, Message, Notification


from django.shortcuts import render, redirect
from .models import JobPost, WorkerProfile, VendorProfile, Application

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required  # <-- Isko import karein
from .models import JobPost, WorkerProfile, VendorProfile, Application

@login_required(login_url='signup')  # <-- Isko yahan lagana zaroori hai
def home(request):
    jobs = JobPost.objects.all().order_by('-posted_at')[:3]
    recent_workers = WorkerProfile.objects.all().order_by('-id')[:4]
    
    applied_job_ids = []
    user_profile = None

    if request.user.is_authenticated:
        worker = WorkerProfile.objects.filter(user=request.user).first()
        vendor = VendorProfile.objects.filter(user=request.user).first()
        
        user_role = getattr(request.user, 'role', None)

        if user_role == 'worker':
            user_profile = worker
            applied_job_ids = Application.objects.filter(applicant=request.user).values_list('job_id', flat=True)
        elif user_role == 'vendor':
            user_profile = vendor
        else:
            user_profile = worker or vendor
            if not user_profile:
                return redirect('select_role')

    context = {
        'jobs': jobs,
        'recent_workers': recent_workers,
        'user_profile': user_profile,      
        'applied_job_ids': applied_job_ids,
    }

    return render(request, 'index.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()

# --- 1. JOBS FEED VIEW ---
# --- 1. JOBS FEED VIEW ---
def job_list(request, job_id=None):  
    # Search logic (Same rahega, bas ordering mein is_featured add kiya hai)
    query = request.GET.get('search')
    if query:
        # Search mein bhi featured jobs upar dikhengi
        jobs = JobPost.objects.filter(
            Q(job_title__icontains=query) | Q(company_name__icontains=query)
        ).order_by('-is_featured', '-posted_at')
    else:
        # Agar job_id aayi hai toh sirf wahi 1 job dikhao, varna saari
        if job_id:
            jobs = JobPost.objects.filter(id=job_id)
        else:
            # 🚀 IQ200 Strategy: '-is_featured' se True wali jobs upar aayengi
            jobs = JobPost.objects.all().order_by('-is_featured', '-posted_at')

    user_profile = None
    applied_job_ids = []
    unread_count = 0

    if request.user.is_authenticated:
        user_profile = WorkerProfile.objects.filter(user=request.user).first()
        applied_job_ids = Application.objects.filter(applicant=request.user).values_list('job_id', flat=True)
        unread_count = Message.objects.filter(receiver=request.user, is_read=False).count()

    return render(request, 'job_list.html', {
        'jobs': jobs,
        'applied_job_ids': applied_job_ids,
        'user_profile': user_profile,
        'unread_messages_count': unread_count,
        'query': query
    })

import json
import pytz
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Message, Notification, User, VendorProfile, WorkerProfile


@login_required
def messaging(request):
  # 🟢 User Profile Resolution (Vendor vs Worker)
  user_profile = None
  if getattr(request.user, 'role', None) == 'vendor':
    user_profile = getattr(request.user, 'vendor_profile', None)
  else:
    user_profile = getattr(request.user, 'worker_profile', None)

  # 🟢 Optimized contact fetching with subqueries
  last_msg_subquery = Message.objects.filter(
      Q(sender=OuterRef('pk'), receiver=request.user)
      | Q(sender=request.user, receiver=OuterRef('pk'))
  ).order_by('-timestamp')

  contacts = (
      User.objects.filter(
          Q(sent_messages__receiver=request.user)
          | Q(received_messages__sender=request.user)
      )
      .distinct()
      .annotate(
          last_msg_content=Subquery(last_msg_subquery.values('content')[:1]),
          last_msg_time=Subquery(last_msg_subquery.values('timestamp')[:1]),
      )
      .order_by('-last_msg_time')
  )

  active_user = None
  target_username = request.GET.get('user')
  if target_username:
    active_user = get_object_or_404(User, username=target_username)

  chat_messages = []
  if active_user:
    chat_messages = (
        Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=active_user))
            | (Q(sender=active_user) & Q(receiver=request.user))
        )
        .select_related('sender', 'receiver')
        .order_by('timestamp')
    )

    # Batch update read status for active chat
    chat_messages.filter(receiver=request.user, is_read=False).update(
        is_read=True
    )

  # 🟢 Badge Counters & Helper Data for Template Header
  msg_count = Message.objects.filter(
      receiver=request.user, is_read=False
  ).count()
  notif_count = Notification.objects.filter(
      user=request.user, is_read=False
  ).count() if hasattr(Notification, 'user') else 0

  # Vendor Groups fallback (if present in project models or context)
  vendor_groups = []

  return render(
      request,
      'messaging.html',
      {
          'contacts': contacts,
          'active_user': active_user,
          'chat_messages': chat_messages,
          'user_profile': user_profile,
          'msg_count': msg_count,
          'notif_count': notif_count,
          'vendor_groups': vendor_groups,
      },
  )

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth.models import User
from .models import Message, Notification
import pytz

@login_required
@csrf_protect
def send_message(request):
    if request.method == 'POST':
        # 1. Data extraction (FormData support)
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        document = request.FILES.get('document')

        # 2. Basic Validation
        if not receiver_id:
            return JsonResponse({'status': 'error', 'message': 'Receiver ID missing'}, status=400)
        
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
        
        # FIX: Agar content khali hai par file bheji hai, toh error mat do
        if not content and not image and not document:
            return JsonResponse({'status': 'error', 'message': 'Message cannot be empty'}, status=400)

        # 3. Save Message
        try:
            with transaction.atomic():
                msg = Message.objects.create(
                    sender=request.user,
                    receiver=receiver,
                    content=content,
                    image=image,      # Image field support
                    document=document # Document field support
                )
                
                # Notification
                Notification.objects.create(
                    user=receiver, 
                    sender=request.user, 
                    message="sent you a new message.",
                    # link=f"/messaging/?user={request.user.username}"
                    link=f"/messaging/?user={request.user.username}"
                )
                
                # Success Response
                return JsonResponse({
                    'id': msg.id,
                    'status': 'success',
                    'content': msg.content,
                    'timestamp': msg.timestamp.astimezone(pytz.timezone('Asia/Kolkata')).strftime("%I:%M %p"),
                    'image_url': msg.image.url if msg.image else None,
                    'doc_url': msg.document.url if msg.document else None,
                    'doc_name': msg.document.name.split('/')[-1] if msg.document else None
                })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Database error: {str(e)}'}, status=500)
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


import urllib.parse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .models import JobPost, Application

@login_required
def apply_for_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    
    # 1. Pehle hi check karein ki kya user ne apply kiya hua hai
    already_applied = Application.objects.filter(job=job, applicant=request.user).exists()
    if already_applied:
        messages.info(request, f"Aapne pehle hi {job.company_name} ke liye apply kiya hua hai.")
        return redirect('worker_dashboard')

    if request.method == 'POST':
        # 2. Application Create karein
        # Yahan hum maan kar chal rahe hain ki Application model mein automatic status 'submitted' ho jayega
        application = Application.objects.create(
            job=job,
            applicant=request.user,
            status='submitted'
        )
        Notification.objects.create(
            user=job.vendor_user, # Job ke owner (vendor) ko notification bhejein
            message=f"🚀 {request.user.username.title()} ne aapki '{job.job_title}' job ke liye apply kiya hai.",
            link=f"/job-detail/{job.id}/" 
        )
        # 3. WhatsApp Message Logic (Professional LinkedIn Style)
        # Vendor ka phone check karein (Sirf numbers extract karein)
        vendor_phone = job.vendor_user.phone_number if job.vendor_user and job.vendor_user.phone_number else "9027522164"
        
        # Phone number cleanup (agar user ne +91 ya 0 pehle lagaya ho)
        if len(vendor_phone) > 10:
            vendor_phone = vendor_phone[-10:]
            
        worker_name = request.user.username.title()
        
        raw_msg = (
            f"🚀 *New Job Application Alert!*\n\n"
            f"📌 *Job Title:* {job.job_title}\n"
            f"🏢 *Company:* {job.company_name}\n"
            f"👤 *Applicant:* {worker_name}\n"
            f"📍 *Location:* {job.location}\n\n"
            f"Check details on [FN Logistic Hub](http://pgease.pythonanywhere.com/vendor-dashboard/)"
        )
        
        encoded_msg = urllib.parse.quote(raw_msg)
        # Indian standard format ke liye 91 prefix
        whatsapp_url = f"https://wa.me/91{vendor_phone}?text={encoded_msg}"

        messages.success(request, f"Success! Applied for {job.company_name}.")
        
        # WhatsApp par redirect karein
        return redirect(whatsapp_url)
    
    return render(request, 'apply_form.html', {'job': job})

# 3. Vendor Dashboard
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import JobPost, Application, WorkerProfile, VendorProfile

@login_required
def vendor_dashboard(request):
    if request.user.role != 'vendor':
        return redirect('worker_dashboard')

    request.session.set_expiry(31536000)

    # 1. Profile Fetching
    user_profile = VendorProfile.objects.filter(user=request.user).first()
    
    # 2. Jobs Data
    jobs = JobPost.objects.filter(vendor_user=request.user)
    job_filter = request.GET.get('job_id')

    # --- AUTO-SELECT LOGIC START ---
    # Agar job_filter nahi hai aur jobs exist karti hain, toh pehli job ko select kar lo
    if not job_filter and jobs.exists():
        first_job = jobs.first()
        job_filter = str(first_job.id)
    # --- AUTO-SELECT LOGIC END ---

    # 3. Application Filtering
    if job_filter and job_filter != '':
        # applications = Application.objects.filter(job_id=job_filter).order_by('-applied_at')
        applications = Application.objects.filter(job__in=jobs).select_related('applicant__worker_profile').order_by('-applied_at')
        active_job = JobPost.objects.filter(id=job_filter, vendor_user=request.user).first()
    else:
        applications = Application.objects.filter(job__in=jobs).order_by('-applied_at')
        active_job = None

    # 4. Analytics
    total_applicants_count = applications.count()
    shortlisted_count = applications.filter(status='shortlisted').count()
    new_count = applications.filter(status='applied').count()

    # 5. Worker Info Injection
    for app in applications:
        app.worker_info = WorkerProfile.objects.filter(user=app.applicant).first()

    return render(request, 'vendor_dashboard.html', {
        'jobs': jobs,
        'applications': applications,
        'selected_job': active_job,
        'selected_job_id': job_filter,
        'app_count': total_applicants_count,
        'total_applicants': total_applicants_count,
        'shortlisted_count': shortlisted_count,
        'new_count': new_count,
        'active_job': active_job,
        'user_profile': user_profile 
    })

# 4. Create Job
@login_required
def create_job(request):
    if request.method == "POST":
        form = JobPostForm(request.POST)
        if form.is_valid():
            # 1. Save the job initially
            job = form.save(commit=False)
            job.vendor_user = request.user
            job.save()
            
            # 2. IQ200 Notification Logic: Notify all followers
            # Hum vendor ke followers nikal rahe hain
            vendor_profile = request.user.vendor_profile
            followers = vendor_profile.followers.all()
            
            for f in followers:
                Notification.objects.create(
                    user=f.worker.user,
                    message=f"🔔 {vendor_profile.company_name} has just posted a new job: {job.job_title}",
                    link=f"/job-detail/{job.id}/"
                )
            
            # 3. Success message in English
            messages.success(request, "Job has been posted successfully and followers have been notified!")
            return redirect('vendor_dashboard')
    else:
        form = JobPostForm()
    return render(request, 'create_job.html', {'form': form})

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WorkerProfile, VendorProfile
from .forms import WorkerProfileForm, VendorProfileForm

@login_required
def create_profile(request):
    """
    DYNAMIC PROFILE HUB:
    Strictly optimized to render the correct onboarding template files 
    instead of falling back or looping into the vendor dashboard layout.
    """
    user_role = request.user.role
    existing_profile = None
    form_class = None

    # 🔄 ROLE CHECK & FORM MAPPING
    if user_role == 'vendor':
        existing_profile = VendorProfile.objects.filter(user=request.user).first()
        form_class = VendorProfileForm
    else:
        existing_profile = WorkerProfile.objects.filter(user=request.user).first()
        form_class = WorkerProfileForm
    
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=existing_profile)
        
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            
            # User profile setup state completion mark (if custom field exists)
            if hasattr(request.user, 'is_profile_complete'):
                request.user.is_profile_complete = True
                request.user.save(update_fields=['is_profile_complete'])
                
            messages.success(request, "Success! Your profile configuration has been saved.")
            
            # 🚀 GUARANTEED REDIRECT FOR VENDOR
            if user_role == 'vendor':
                return redirect('vendor_dashboard')
            return redirect('home')
        else:
            print("--- FORM VALIDATION FAILED ---")
            print(form.errors)
            
            for field, errors in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errors[0]}")
            
            # 🎯 EMERGENCY FIX 1: Explicitly force the onboarding template on validation fail
            return render(request, 'create_profile.html', {
                'form': form, 
                'profile': existing_profile,
                'user_profile': existing_profile  # 🟢 Added user_profile to resolve navbar template errors
            })
            
    else:
        form = form_class(instance=existing_profile)
        
    # 🎯 EMERGENCY FIX 2: Explicitly force the onboarding template on initial GET request
    return render(request, 'create_profile.html', {
        'form': form, 
        'profile': existing_profile,
        'user_profile': existing_profile  # 🟢 Added user_profile to resolve navbar template errors
    })

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from .models import WorkerProfile, VendorProfile

User = get_user_model()

def signup_view(request):
    # 🚨 FIX: Agar user pehle se login hai, toh use forcibly logout karo
    # Taki naya signup page bina redirection loop ke dikh sake
    if request.user.is_authenticated:
        logout(request)
        return redirect('signup')

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone_number')
        password = request.POST.get('password')
        role = request.POST.get('role')

        try:
            # Step 1: Handle existing user
            existing_user = User.objects.filter(username=phone).first()
            if existing_user:
                existing_user.delete()

            # Step 2: Create User
            user = User.objects.create_user(username=phone, password=password)
            
            # Ensure attributes exist
            user.phone_number = phone
            user.role = role
            user.save()

            # Step 3: Log in
            login(request, user)

            # Step 4: Profile Creation
            if role == 'worker':
                WorkerProfile.objects.get_or_create(
                    user=user, 
                    defaults={'full_name': full_name}
                )
                return redirect('update_worker')
            else:
                VendorProfile.objects.get_or_create(
                    user=user, 
                    defaults={'contact_person': full_name, 'phone': phone}
                )
                return redirect('update_vendor')

        except Exception as e:
            return render(request, 'signup.html', {'error': f'System Error: {e}'})

    return render(request, 'signup.html')

from django.core.paginator import Paginator
from django.shortcuts import render
from .models import WorkerProfile

def worker_directory(request):
    worker_list = WorkerProfile.objects.all().order_by('-id')
    
    # 🔍 Search Logic: Naam ya Category se dhoondhne ke liye
    query = request.GET.get('q')
    if query:
        worker_list = worker_list.filter(full_name__icontains=query) | worker_list.filter(work_category__icontains=query)

    # 📄 Pagination Logic: Har page par 9 workers
    paginator = Paginator(worker_list, 9) 
    page_number = request.GET.get('page')
    workers = paginator.get_page(page_number)
    
    return render(request, 'worker_list.html', {'workers': workers, 'query': query})

from django.shortcuts import render, get_object_or_404
from .models import WorkerProfile

# 1. Ye aapki purani profile dikhayega
def worker_detail(request, pk):
    worker = get_object_or_404(WorkerProfile, pk=pk)
    return render(request, 'worker_detail.html', {'worker': worker})

# 2. Ye naya function sirf Resume dikhayega
def worker_resume(request, pk):
    worker = get_object_or_404(WorkerProfile, pk=pk)
    return render(request, 'worker_cv_pdf.html', {'worker': worker})

# views.py
def worker_resume_preview(request, pk):
    worker = get_object_or_404(WorkerProfile, pk=pk)
    # Ye function specifically resume template dikhayega
    return render(request, 'worker_cv_pdf.html', {'worker': worker})

def send_whatsapp_alert(vendor_phone, worker_name, job_title):
    # WhatsApp message template
    message = f"Hello! Naya application aaya hai.\n\nWorker: {worker_name}\nJob: {job_title}\n\nTurant check karein: http://pgease.pythonanywhere.com/vendor-dashboard/"
    
    # URL encode the message
    whatsapp_url = f"https://wa.me/91{vendor_phone}?text={message.replace(' ', '%20').replace('\n', '%0A')}"
    return whatsapp_url

def find_workers(request):
    worker_list_query = WorkerProfile.objects.all().order_by('-id')
    
    # Search Logic
    query = request.GET.get('q') or request.GET.get('search')
    if query:
        worker_list_query = worker_list_query.filter(full_name__icontains=query) | \
                            worker_list_query.filter(work_category__icontains=query)

    # Pagination
    paginator = Paginator(worker_list_query, 9) 
    page_number = request.GET.get('page')
    workers = paginator.get_page(page_number)

    # Like Logic
    if request.user.is_authenticated:
        for worker in workers:
            worker.is_liked = worker.likes.filter(user=request.user).exists()

    # User Profile Fetch
    user_profile = None
    if request.user.is_authenticated:
        if request.user.role == 'vendor':
            user_profile = VendorProfile.objects.filter(user=request.user).first()
        else:
            user_profile = WorkerProfile.objects.filter(user=request.user).first()
        
    return render(request, 'find_workers.html', {
        'workers': workers, 
        'user_profile': user_profile, # YEH LINE ADD KI HAI
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import WorkerProfile, Application, Follow # Follow import karna zaroori hai

@login_required
def worker_dashboard(request):
    # 🛡️ HARD SECURITY RULE
    if request.user.role != 'worker':
        return redirect('vendor_dashboard')

    # Session persistence
    request.session.set_expiry(31536000)

    # Worker ki profile nikalna ya create karna
    profile, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    # 🛠️ SYSTEM FIX: Total applications
    total_applications = Application.objects.filter(applicant=request.user).count()
    
    # 🌟 NEW: Following list for the Sidebar
    following_list = Follow.objects.filter(worker=profile)

    # 1. Messaging Count
    msg_count = 0 

    # 2. Notification Count
    notif_count = 0 

    # 3. Context Builder
    return render(request, 'worker_dashboard.html', {
        'profile': profile,
        'user_profile': profile,
        'worker_profile': profile,
        'msg_count': msg_count,
        'notif_count': notif_count,
        'app_count': total_applications,
        'following_list': following_list, # <--- Ye add ho gaya hai
        'my_applications': Application.objects.filter(applicant=request.user).order_by('-applied_at')
    })

@login_required
def update_status(request, app_id, new_status):
    application = get_object_or_404(Application, id=app_id)
    
    # Check ki kya ye job isi vendor ki hai?
    if application.job.vendor_user == request.user:
        application.status = new_status
        application.save()
        messages.success(request, f"Status updated to {new_status}!")
    
    return redirect('vendor_dashboard')

@login_required
def like_job(request, pk):
    job = get_object_or_404(JobPost, pk=pk)
    if job.likes.filter(id=request.user.id).exists():
        job.likes.remove(request.user)
        is_liked = False
    else:
        job.likes.add(request.user)
        is_liked = True

    return JsonResponse({
        'total_likes': job.likes.count(),
        'is_liked': is_liked
    })

import os
import re
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.shortcuts import get_object_or_404
from .models import WorkerProfile

def download_cv(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    # PDF ke liye alag template use karein (worker_cv_pdf.html)
    template_path = 'worker_cv_pdf.html' 
    context = {'worker': worker}
    
    template = get_template(template_path)
    html = template.render(context)

    # Response taiyar karein
    response = HttpResponse(content_type='application/pdf')
    # "attachment" se direct download hoga, naya tab/blank page nahi khulega
    response['Content-Disposition'] = f'attachment; filename="Resume_{worker.full_name}.pdf"'

    # Path resolver (Images ke liye)
    def link_callback(uri, rel):
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        elif uri.startswith(settings.STATIC_URL):
            path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        else:
            return uri
        return path

    # PDF Generate karein (html variable direct use karein, cleaning ki zaroorat nahi)
    pisa_status = pisa.CreatePDF(
        html, 
        dest=response, 
        link_callback=link_callback,
        encoding='utf-8'
    )

    if pisa_status.err:
        return HttpResponse('<h2>PDF Error</h2><p>Template design mein issue hai.</p>', status=500)
        
    return response

@login_required
def add_comment(request, job_id=None, worker_id=None):
    if request.method == "POST":
        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'status': 'error', 'message': 'Content empty'}, status=400)
        
        # User name aur Photo logic
        user_name = request.user.username
        photo_url = None
        
        if hasattr(request.user, 'worker_profile'):
            if request.user.worker_profile.full_name:
                user_name = request.user.worker_profile.full_name
            if request.user.worker_profile.photo:
                photo_url = request.user.worker_profile.photo.url
            
        # Logic: Agar job_id hai toh Job Comment, else Worker Comment
        if job_id:
            job = get_object_or_404(JobPost, id=job_id)
            comment = Comment.objects.create(user=request.user, job=job, content=content)
            count = job.comments.count()
        elif worker_id:
            worker = get_object_or_404(WorkerProfile, id=worker_id)
            comment = Comment.objects.create(user=request.user, worker=worker, content=content)
            count = worker.comments.count()
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid target'}, status=400)
            
        return JsonResponse({
            'status': 'success',
            'user': user_name,
            'content': comment.content,
            'comment_count': count,
            'comment_id': comment.id,     # <--- ADDED: Frontend ko delete karne ke liye chahiye
            'photo_url': photo_url,       # <--- ADDED: Avatar display ke liye
            'user_initial': user_name[0].upper()
        })
    
@login_required
def reply_comment(request, comment_id):
    if request.method == "POST":
        parent_comment = get_object_or_404(Comment, id=comment_id)
        content = request.POST.get('content')
        
        if content:
            reply = Comment.objects.create(
                job=parent_comment.job,
                user=request.user,
                content=content,
                parent=parent_comment # Ye isse 'Revert' (Reply) banayega
            )
            return JsonResponse({
                'status': 'success',
                'user': reply.user.username,
                'content': reply.content
            })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_comment(request, comment_id):
    # Comment object fetch karo
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check karo ki user authorized hai ya nahi
    if comment.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    # Yahan hum check karenge ki comment kis se juda hai (Worker ya Job)
    # Agar 'worker' field null hai, toh hum 'job' field check karenge
    if comment.worker:
        parent_obj = comment.worker
        # Worker ke liye filter
        new_count = Comment.objects.filter(worker=parent_obj).count()
    elif hasattr(comment, 'job') and comment.job:
        parent_obj = comment.job
        # Job ke liye filter
        new_count = Comment.objects.filter(job=parent_obj).count()
    else:
        # Agar dono hi nahi hain (fallback)
        new_count = 0

    # Ab comment delete karo
    comment.delete()
    
    return JsonResponse({
        'status': 'success', 
        'comment_count': new_count
    })

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_router(request):
    # 1. Jab koi bhi purani id se login kare, toh uski session memory 1 saal tak active rakho
    # Isse tab close karne ya app par dobara aane par password nahi maangega
    request.session.set_expiry(31536000)  # 365 days seconds mein
    
    # 2. User ke role ke mutabik unhe sahi dashboard par route (bhej) karo
    if request.user.role == 'vendor':
        return redirect('vendor_dashboard')
    else:
        return redirect('worker_dashboard')
    
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import WorkerProfile, VendorProfile

@login_required
def profile_settings(request):
    # Agar user Worker hai
    if request.user.role == 'worker':
        profile, created = WorkerProfile.objects.get_or_create(user=request.user)
        if request.method == 'POST':
            profile.full_name = request.POST.get('full_name')
            profile.work_category = request.POST.get('work_category')
            profile.skills = request.POST.get('skills')
            if request.FILES.get('photo'):
                profile.photo = request.FILES.get('photo')
            profile.save()
            return redirect('worker_dashboard')
        return render(request, 'update_worker.html', {'profile': profile})

    # Agar user Vendor hai
    elif request.user.role == 'vendor':
        company, created = VendorProfile.objects.get_or_create(user=request.user)
        if request.method == 'POST':
            company.company_name = request.POST.get('company_name')
            company.address = request.POST.get('address')
            company.phone = request.POST.get('phone')
            if request.FILES.get('company_logo'):
                company.company_logo = request.FILES.get('company_logo')
            company.save()
            return redirect('vendor_dashboard')
        return render(request, 'update_vendor.html', {'company': company})

def select_role(request):
    return render(request, 'role_selection.html')

@login_required
def update_worker(request):
    # 1. Profile uthao ya banao
    profile, created = WorkerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # 2. Form mein data bharo (Files ke sath)
        form = WorkerProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            print("✅ Profile saved successfully!")
            # Yahan redirect confirm karo ki URL name 'worker_dashboard' hi hai
            return redirect('worker_dashboard')
        else:
            # 🚨 Yahan errors print honge, terminal mein check karo
            print(f"❌ Form Validation Errors: {form.errors}")
            # Errors ko messages mein bhejo taaki user ko page par dikhe
            messages.error(request, "Profile save nahi hui, kripya sahi jankari bharein.")
    else:
        # 3. Khali ya purana data wala form dikhao
        form = WorkerProfileForm(instance=profile)
        
    return render(
        request, 
        'create_profile.html', 
        {
            'profile': profile, 
            'user_profile': profile,  # 🛠️ Fixed: Isse base.html (line 268) ko user_profile mil jayega
            'form': form
        }
    )

from django.shortcuts import render
from django.http import HttpResponse
from .models import Worker

def generate_pdf(request, pk):
    try:
        worker = Worker.objects.get(pk=pk)
    except Worker.DoesNotExist:
        return HttpResponse(
            f"<div style='font-family: sans-serif; text-align: center; padding: 50px;'>"
            f"<h2 style='color: #e11d48;'>Worker ID {pk} Not Found!</h2>"
            f"<p style='color: #64748b;'>Please create a profile in the database or enter a valid Worker ID.</p>"
            f"</div>"
        )

    # Render LinkedIn styled template when worker exists
    return render(request, 'worker_pdf.html', {'worker': worker})

@login_required
def update_vendor(request):
    company, created = VendorProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        company.company_name = request.POST.get('company_name')
        company.contact_person = request.POST.get('contact_person')
        company.address = request.POST.get('address')
        company.phone = request.user.phone_number 
        company.description = request.POST.get('hosted_companies', '')

        if request.FILES.get('company_logo'):
            company.company_logo = request.FILES.get('company_logo')
            
        try:
            company.save()
            return redirect('vendor_dashboard')
        except Exception as e:
            print(f"Error saving vendor profile: {e}")
            
    # Yahan humne 'is_onboarding' add kar diya hai
    return render(request, 'update_vendor.html', {
        'company': company,
        'is_onboarding': True 
    })

@login_required
def dual_dashboard(request):
    # This view will show common data for the dual tab dashboard
    return render(request, 'dual_dashboard.html')

# Inhe views.py ke niche add karein
def messages_view(request):
    # Abhi ke liye sirf ek blank page dikhayega
    return render(request, 'messaging.html', {
        'user_profile': WorkerProfile.objects.get(user=request.user)
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import WorkerProfile, Notification # Notification import karna zaroori hai

# hub/views.py

@login_required 
def notifications_view(request):
    # .select_related() ka istemal karein taaki profile details ek hi query mein aa jayein
    notifications = Notification.objects.filter(user=request.user).select_related(
        'sender__worker_profile', 
        'sender__vendor_profile'
    ).order_by('-timestamp')
    
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    # User profile fetch karna
    profile = None
    if hasattr(request.user, 'worker_profile'):
        profile = request.user.worker_profile
    elif hasattr(request.user, 'vendor_profile'):
        profile = request.user.vendor_profile

    return render(request, 'notifications.html', {
        'notifications': notifications,
        'notif_count': unread_count,
        'user_profile': profile, # Sahi variable pass karein
    })

from django.http import JsonResponse

def like_post(request, pk):
    post = get_object_or_404(Post, id=pk)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        is_liked = False
    else:
        post.likes.add(request.user)
        is_liked = True
    
    return JsonResponse({'is_liked': is_liked, 'total_likes': post.total_likes()})
# hub/views.py mein ye function add karein (agar nahi hai)
def worker_profile_detail(request, pk):
    worker = get_object_or_404(WorkerProfile, pk=pk)
    # Skills ko list mein convert kar rahe hain taaki comma-separated ho
    skills_list = worker.skills.split(',') if worker.skills else []
    
    return render(request, 'worker_detail.html', {
        'worker': worker,
        'skills': skills_list
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import VendorProfile, JobPost, WorkerProfile

# 🏢 1. VENDOR PROFILE VIEW (For both Vendor & Worker to see)
def vendor_detail_view(request, vendor_id):
    # Vendor profile data uthao (user_id ke base par)
    vendor_profile = get_object_or_404(VendorProfile, user_id=vendor_id)
    
    # Is vendor ne jitni bhi jobs post ki hain aur jo active hain, unhe nikalen
    active_hiring_jobs = JobPost.objects.filter(vendor_user_id=vendor_id).order_by('-posted_at')
    
    # Active hiring jobs ka count
    job_count = active_hiring_jobs.count()

    context = {
        'vendor_profile': vendor_profile,
        'jobs': active_hiring_jobs,
        'job_count': job_count,
    }
    return render(request, 'vendor_detail.html', context)


# ✍️ 2. EDIT VENDOR PROFILE (Only for the logged-in Vendor)
@login_required
def edit_vendor_profile(request):
    if request.user.role != 'vendor':
        return redirect('worker_dashboard')
        
    # Profile fetch ya create karo agar nahi bani hai
    vendor_profile, created = VendorProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Form submission data catch karo
        vendor_profile.company_name = request.POST.get('company_name')
        vendor_profile.industry = request.POST.get('industry', 'Logistics')
        vendor_profile.location = request.POST.get('location')
        vendor_profile.description = request.POST.get('description')
        
        # Logo update check
        if 'company_logo' in request.FILES:
            vendor_profile.company_logo = request.FILES['company_logo']
            
        vendor_profile.save()
        return redirect('vendor_dashboard') # Update ke baad seedha dashboard par bhejdo
        
    return render(request, 'edit_vendor_profile.html', {'vendor_profile': vendor_profile})

def custom_logout(request):
    logout(request)
    return redirect('signup') # Logout ke baad seedha signup page par bheje

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required  # Ye import zaroori hai
from .models import WorkerProfile, Comment, Like 

@csrf_exempt
@login_required
def like_worker(request, pk):
    worker = get_object_or_404(WorkerProfile, pk=pk)
    # Galti yahan thi: 'worker' ki jagah 'worker_profile'
    like_obj = Like.objects.filter(user=request.user, worker_profile=worker)
    
    if like_obj.exists():
        like_obj.delete()
        liked = False
    else:
        Like.objects.create(user=request.user, worker_profile=worker)
        liked = True
        
    return JsonResponse({
        'total_likes': worker.likes.count(),
        'liked': liked
    })

@login_required
def add_comment_to_worker(request, pk):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        worker = get_object_or_404(WorkerProfile, pk=pk)
        
        new_comment = Comment.objects.create(user=request.user, worker=worker, content=content)
        
        # Name aur Photo logic
        # Agar WorkerProfile hai toh wahan se, nahi toh username
        profile = getattr(request.user, 'worker_profile', None)
        display_name = profile.full_name if profile and profile.full_name else request.user.username
        photo_url = profile.photo.url if profile and profile.photo else None
            
        return JsonResponse({
            'comment_id': new_comment.id,
            'user': display_name,
            'content': content,
            'comment_count': worker.comments.count(),
            'photo_url': photo_url
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_comment_to_job(request, pk):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'status': 'error', 'message': 'Content is empty'}, status=400)
            
        job = get_object_or_404(JobPost, pk=pk)
        new_comment = Comment.objects.create(user=request.user, job=job, content=content)
        
        # Default fallback
        display_name = request.user.username
        photo_url = None
        
        # 1. Worker Profile Check
        worker_prof = WorkerProfile.objects.filter(user=request.user).first()
        if worker_prof and worker_prof.full_name:
            display_name = worker_prof.full_name
            if worker_prof.photo: 
                photo_url = worker_prof.photo.url
        
        # 2. Vendor Profile Check (Priority: Personal Name > Company Name)
        else:
            vendor_prof = VendorProfile.objects.filter(user=request.user).first()
            if vendor_prof:
                # Agar contact_person hai toh wo dikhao, varna company_name
                display_name = vendor_prof.contact_person if vendor_prof.contact_person else vendor_prof.company_name
                if vendor_prof.company_logo: 
                    photo_url = vendor_prof.company_logo.url
            
        return JsonResponse({
            'status': 'success',
            'comment_id': new_comment.id,
            'user': display_name,
            'content': content,
            'comment_count': job.comments.count(),
            'photo_url': photo_url 
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def notification_list(request):
    # User ki sari notifications fetch karein
    notifications = request.user.notifications.all()
    return render(request, 'notifications.html', {'notifications': notifications})

# Yeh code aapke existing views.py mein hona chahiye
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Notification
from django.urls import reverse

@login_required
def mark_notification_read(request, notif_id):
    # .first() use karne se 404 error nahi aayega
    notif = Notification.objects.filter(id=notif_id, user=request.user).first()
    
    # Agar notification nahi mili, toh seedha notifications page par bhej do
    if not notif:
        return redirect('notifications') 
    
    # Mark as read
    Notification.objects.filter(
        user=request.user, 
        sender=notif.sender, 
        is_read=False
    ).update(is_read=True)
    
    # Link redirection
    if notif.link and notif.link.strip() != "":
        try:
            return redirect(notif.link)
        except:
            return redirect('notifications')
    return redirect('notifications')

from django.shortcuts import render, get_object_or_404
from .models import VendorProfile, JobPost, Follow # Follow model zaroor import karein

def vendor_profile_detail(request, pk):
    vendor = get_object_or_404(VendorProfile, pk=pk)
    
    # 1. Jobs fetch karo
    all_jobs = JobPost.objects.filter(vendor_user=vendor.user)
    
    # Agar model mein 'status' field nahi hai, toh simple filter use karein
    # Ya niche diye gaye alternative logic ka use karein
    active_jobs = all_jobs.filter(status='active') 
    past_jobs = all_jobs.filter(status='closed')[:5]
    
    # 2. Analytics
    total_jobs = all_jobs.count()
    hiring_rate = "98%"
    
    # 3. Follow Status (Button active karne ke liye)
    is_following = False
    if request.user.is_authenticated and hasattr(request.user, 'worker_profile'):
        is_following = Follow.objects.filter(worker=request.user.worker_profile, vendor=vendor).exists()
    
    return render(request, 'vendor_profile.html', {
        'vendor': vendor,
        'active_jobs': active_jobs,
        'past_jobs': past_jobs,
        'total_jobs': total_jobs,
        'hiring_rate': hiring_rate,
        'is_following': is_following, # Template mein button active karne ke liye
    })

from django.http import JsonResponse
from .models import Follow, VendorProfile, WorkerProfile

@login_required
def follow_vendor(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    worker = request.user.worker_profile
    
    follow_obj, created = Follow.objects.get_or_create(worker=worker, vendor=vendor)
    
    if not created:
        follow_obj.delete() # Unfollow kar diya
        return JsonResponse({'status': 'unfollowed'})
    
    return JsonResponse({'status': 'followed'})

from django.http import JsonResponse
from .models import Follow, VendorProfile

@login_required
def toggle_follow(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    worker = request.user.worker_profile
    
    # Check agar pehle se follow kar rakha hai
    follow_obj = Follow.objects.filter(worker=worker, vendor=vendor)
    
    if follow_obj.exists():
        follow_obj.delete() # Unfollow
        status = 'unfollowed'
    else:
        Follow.objects.create(worker=worker, vendor=vendor) # Follow
        status = 'followed'
        
    return JsonResponse({'status': status})

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import pytz
from .models import Message

@login_required
def get_new_messages(request, receiver_id):
  last_id = request.GET.get('last_msg_id', 0)
  new_msgs = Message.objects.filter(
      (Q(sender_id=receiver_id) & Q(receiver=request.user))
      | (Q(sender=request.user) & Q(receiver_id=receiver_id)),
      id__gt=last_id,
  ).order_by('timestamp')

  data = [{
      'id': m.id,
      'content': m.content,
      'is_me': m.sender == request.user,
      'timestamp': m.timestamp.astimezone(
          pytz.timezone('Asia/Kolkata')
      ).strftime('%I:%M %p'),
  } for m in new_msgs]

  new_msgs.filter(receiver=request.user).update(is_read=True)
  return JsonResponse({'messages': data})

# hub/views.py
@login_required
@csrf_exempt
def delete_message(request, message_id): # <--- Ye id zaroori hai
    if request.method == 'POST':
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        message.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

from django.http import JsonResponse

@login_required
def load_more_messages(request, receiver_id):
    offset = int(request.GET.get('offset', 0))
    limit = 20
    
    # Purane messages offset ke hisaab se
    messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver_id=receiver_id)) |
        (Q(sender_id=receiver_id) & Q(receiver=request.user))
    ).order_by('-timestamp')[offset:offset+limit]
    
    # Reverse karo taaki purane upar dikhein
    msg_list = list(reversed(messages))
    
    data = [{
        'sender': msg.sender.username,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime("%H:%M"),
        'is_me': msg.sender == request.user
    } for msg in msg_list]
    
    return JsonResponse({'messages': data})

from django.utils import timezone
from datetime import timedelta

def is_user_online(user):
    # Agar user ka last_login 5 minute se kam purana hai, to online hai
    return user.last_login and user.last_login > timezone.now() - timedelta(minutes=5)

@login_required
def feature_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id, vendor_user=request.user)
    from django.utils import timezone
    import datetime
    
    job.is_featured = True
    job.featured_until = timezone.now() + datetime.timedelta(hours=24)
    job.save()
    
    messages.success(request, "Your job is now featured and visible at the top! 🚀")
    return redirect('vendor_dashboard')

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import JobPost, Application

@login_required
def auto_shortlist_applicants(request, job_id):
    # Agar job_id 0 (All) hai, toh error se bachne ke liye redirect
    if not job_id:
        return redirect('vendor_dashboard')
        
    job = get_object_or_404(JobPost, id=int(job_id))
    required_skills = [s.strip().lower() for s in job.required_skills.split(',')] if job.required_skills else []
    
    applications = Application.objects.filter(job=job, status='applied')
    
    for app in applications:
        # Check karein ki worker profile exist karti hai
        if hasattr(app.applicant, 'worker_profile') and app.applicant.worker_profile.skills:
            worker_skills = [s.strip().lower() for s in app.applicant.worker_profile.skills.split(',')]
            
            # Intersection (Common skills)
            matches = len(set(required_skills) & set(worker_skills))
            
            # Agar 1 bhi skill match ho ya aapki condition set karein
            if matches >= 1: 
                app.status = 'shortlisted'
                app.save()
            
    return redirect(f'/vendor-dashboard/?job_id={job_id}')

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import pytz
from .models import Message, Notification, WorkerProfile, VendorProfile, Group
from django.contrib.auth import get_user_model

User = get_user_model()

def community_hub(request):
    username = request.GET.get('user')
    # Defaulting active_user to None if not found
    active_user = User.objects.filter(username=username).first()
    
    context = {
        'active_user': active_user,
        'active_group': Group.objects.filter(members=request.user).first(),
        'groups': Group.objects.none(),
        'messages': Message.objects.none(),
        'user_profile': None,
    }
    
    if request.user.is_authenticated:
        # Load user's groups
        context['groups'] = Group.objects.filter(members=request.user)
        
        # Load messages if active_user is valid
        if active_user:
            context['messages'] = Message.objects.filter(
                (Q(sender=request.user) & Q(receiver=active_user)) |
                (Q(sender=active_user) & Q(receiver=request.user))
            ).order_by('timestamp')
            
        # Profile Fetching
        # Optimized: Use getattr to safely check roles
        role = getattr(request.user, 'role', None)
        if role == 'vendor':
            context['user_profile'] = VendorProfile.objects.filter(user=request.user).first()
        elif role == 'worker':
            context['user_profile'] = WorkerProfile.objects.filter(user=request.user).first()
            
    return render(request, 'community.html', context)

# 3. AI MATCHMAKER (Role-based)
@login_required
def get_ai_worker_matches(request):
    role = request.GET.get('role', 'Picker')
    matches = WorkerProfile.objects.filter(
        work_category__icontains=role,
        is_available=True
    ).order_by('-total_experience')[:3]
    
    data = [{
        'name': w.full_name,
        'rating': str(w.total_experience) if hasattr(w, 'total_experience') else '4.5',
        'id': w.id
    } for w in matches]
    
    return JsonResponse({'workers': data})

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Group, WorkerProfile, Invitation, Notification

@csrf_exempt
@login_required
def invite_worker(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    try:
        # Check if request body is empty
        if not request.body:
            return JsonResponse({'status': 'error', 'message': 'Empty request body'}, status=400)
            
        data = json.loads(request.body)
        worker_id = data.get('worker_id')
        group_id = data.get('group_id')

        # Validation
        if not worker_id or not group_id:
            return JsonResponse({'status': 'error', 'message': 'Missing IDs: worker_id or group_id'}, status=400)

        worker_profile = get_object_or_404(WorkerProfile, id=worker_id)
        group = get_object_or_404(Group, id=group_id)
        worker_user = worker_profile.user

        # Business Logic
        if group.members.filter(id=worker_user.id).exists():
            return JsonResponse({'status': 'info', 'message': 'Worker already a member'})
        
        if Invitation.objects.filter(group=group, receiver=worker_user, status='pending').exists():
            return JsonResponse({'status': 'info', 'message': 'Invitation already pending'})

        # Action
        Invitation.objects.create(group=group, sender=request.user, receiver=worker_user, status='pending')
        
        # Notification
        Notification.objects.create(
            user=worker_user, sender=request.user, 
            message=f"{request.user.username} invited you to {group.name}", link='/community/'
        )

        return JsonResponse({'status': 'success', 'message': 'Invitation sent!'})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

from django.db.models import Q

def get_chat_messages(user1, user2):
    # Ye function dono taraf ke messages nikalega
    return Message.objects.filter(
        (Q(sender=user1) & Q(receiver=user2)) |
        (Q(sender=user2) & Q(receiver=user1))
    ).order_by('timestamp')

from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def search_workers(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'workers': []})
    
    # .select_related('user') performance ke liye behtar hai 
    # agar aap future mein 'user' model se kuch fetch karna chahein
    results = WorkerProfile.objects.select_related('user').filter(
        Q(full_name__icontains=query) | Q(work_category__icontains=query)
    )[:10] 
    
    worker_list = [
        {
            'id': w.id,
            'name': w.full_name,
            'designation': w.work_category,
            'image_url': w.photo.url if w.photo else '/static/default-avatar.png'
        } for w in results
    ]
    return JsonResponse({'workers': worker_list})

from django.core.paginator import Paginator

@login_required
def get_workers_list(request):
    # Page number lein (default 1)
    page = request.GET.get('page', 1)
    # Saare active workers
    workers = WorkerProfile.objects.all().order_by('full_name')
    
    # Pagination (10 workers per load)
    paginator = Paginator(workers, 10)
    worker_page = paginator.get_page(page)
    
    worker_list = [
        {
            'id': w.id,
            'name': w.full_name,
            'designation': w.work_category,
            'image_url': w.photo.url if w.photo else '/static/default-avatar.png'
        } for w in worker_page
    ]
    
    return JsonResponse({
        'workers': worker_list,
        'has_next': worker_page.has_next()
    })

from django.shortcuts import render, get_object_or_404
from .models import Group

# hub/views.py
def community_view(request):
    # Sirf wahi group dikhayein jismein atleast ek member ho ya basic validation
    groups = Group.objects.all()
    return render(request, 'community.html', {'groups': groups})

def group_detail(request, pk):
    # ग्रुप ढूँढने का कोड
    group = get_object_or_404(Group, pk=pk)
    return render(request, 'group_detail.html', {'group': group})

def accept_invite(request, notification_id):
    notification = Notification.objects.get(id=notification_id)
    group = notification.group # मान लीजिए नोटिफिकेशन में ग्रुप लिंक है
    
    # यूजर को ग्रुप का मेंबर बनाएं
    group.members.add(request.user)
    group.save()
    
    # नोटिफिकेशन हटा दें या 'accepted' मार्क कर दें
    notification.delete() 
    
    return redirect('community_hub')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Group # Apna model import karein

@login_required
@csrf_exempt
def create_group(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            group_name = data.get('group_name')
            
            if group_name:
                # Yahan new_group object banayein
                new_group = Group.objects.create(name=group_name, owner=request.user)
                new_group.members.add(request.user)
                new_group.save()
                
                return JsonResponse({'status': 'success', 'message': 'Group created'})
            
            return JsonResponse({'status': 'error', 'message': 'Name missing'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# hub/views.py

def community_page(request):
    # Sirf wahi groups filter karein jahan user 'owner' hai
    my_groups = Group.objects.filter(owner=request.user)
    
    # Debugging ke liye (Terminal mein check karein)
    print(f"Logged in user: {request.user.username}")
    print(f"Groups found: {my_groups.count()}")
    
    # 'my_groups' ko hi template mein pass karein
    return render(request, 'community.html', {'groups': my_groups})

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
@csrf_exempt # Agar aap JS se POST kar rahe hain, toh ye zaroori hai
def accept_invitation(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            group_id = data.get('group_id')
            
            if not group_id:
                return JsonResponse({'status': 'error', 'message': 'Group ID missing'}, status=400)
            
            # 1. Group check karein
            group = get_object_or_404(Group, id=group_id)
            
            # 2. Worker ko add karein (Already member check)
            if not group.members.filter(id=request.user.id).exists():
                group.members.add(request.user)
                group.save()
            
            # 3. Notification ko mark as read ya delete kar dein
            # Iske liye request mein notification_id bhejna best practice hai
            notif_id = data.get('notification_id')
            if notif_id:
                Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
            
            return JsonResponse({'status': 'success', 'message': 'Group joined successfully!'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


# hub/views.py

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def delete_notification(request, id):
    # Ensure 'user' is the correct field name in your Notification model
    notification = get_object_or_404(Notification, id=id, user=request.user)
    notification.delete()
    return JsonResponse({'status': 'success'})
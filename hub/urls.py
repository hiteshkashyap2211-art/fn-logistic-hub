from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import path
from django.views.generic import TemplateView

from . import views


# Direct Verification Views (Bina kisi Login check ke)
def google_verification_file(request):
  # Google HTML File Method
  return HttpResponse('google-site-verification: google3c120d71fc732d2a.html')


urlpatterns = [
    # 1. Google Verification Routes (Sabse Upar Rakhein)
    path('google3c120d71fc732d2a.html', google_verification_file),
    # --- Auth ---
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='login.html'),
        name='login',
    ),
    path('logout/', views.custom_logout, name='logout'),
    path('select-role/', views.select_role, name='select_role'),
    # --- Dashboards ---
    path('vendor-dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('my-dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('dashboard/', views.dashboard_router, name='dashboard_router'),
    path('dual-dashboard/', views.dual_dashboard, name='dual_dashboard'),
    # --- Jobs & Applications ---
    path('jobs/', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_list, name='job_detail'),
    path('post-job/', views.create_job, name='post_job'),
    path('apply/<int:job_id>/', views.apply_for_job, name='apply_for_job'),
    path(
        'update-status/<int:app_id>/<str:new_status>/',
        views.update_status,
        name='update_status',
    ),
    path('like-job/<int:pk>/', views.like_job, name='like_job'),
    # --- Profiles ---
    path('update-worker/', views.update_worker, name='update_worker'),
    path('update-vendor/', views.update_vendor, name='update_vendor'),
    path('create-profile/', views.create_profile, name='create_profile'),
    path(
        'vendor/profile/<int:vendor_id>/',
        views.vendor_detail_view,
        name='vendor_detail',
    ),
    path(
        'vendor/profile/edit/',
        views.edit_vendor_profile,
        name='edit_vendor_profile',
    ),
    # --- Workers ---
    path('workers/', views.worker_directory, name='worker_list'),
    path(
        'worker-profile/<int:pk>/',
        views.worker_profile_detail,
        name='worker_detail',
    ),
    path('download-cv/<int:worker_id>/', views.download_cv, name='download_cv'),
    path('worker/<int:pk>/resume/', views.worker_resume, name='worker_resume'),
    path(
        'worker/<int:pk>/resume-preview/',
        views.worker_resume_preview,
        name='worker_resume_preview',
    ),
    # --- Messaging & Notifications ---
    path('messages/', views.messaging, name='messages'),
    path('messages-old/', views.messages_view, name='messages_old'),
    path('notifications/', views.notifications_view, name='notifications'),
    path(
        'notifications/read/<int:notif_id>/',
        views.mark_notification_read,
        name='mark_notification_read',
    ),
    # --- Interactions ---
    path(
        'comment/<int:comment_id>/reply/',
        views.reply_comment,
        name='reply_comment',
    ),
    path(
        'comment/<int:comment_id>/delete/',
        views.delete_comment,
        name='delete_comment',
    ),
    path('find-workers/', views.find_workers, name='find_worker'),
    path('worker/<int:pk>/like/', views.like_worker, name='like_worker'),
    path(
        'worker/<int:pk>/comment/',
        views.add_comment_to_worker,
        name='add_comment_to_worker',
    ),
    path('job/<int:job_id>/comment/', views.add_comment, name='add_job_comment'),
    path(
        'worker/<int:worker_id>/comment/',
        views.add_comment,
        name='add_worker_comment',
    ),
    path('messaging/', views.messaging, name='messaging'),
    path(
        'vendor-profile/<int:pk>/',
        views.vendor_profile_detail,
        name='vendor_profile_detail',
    ),
    path('follow/<int:vendor_id>/', views.toggle_follow, name='toggle_follow'),
    path(
        'get-new-messages/<int:receiver_id>/',
        views.get_new_messages,
        name='get_new_messages',
    ),
    path(
        'delete-message/<int:message_id>/',
        views.delete_message,
        name='delete_message',
    ),
    path(
        'load-more-messages/<int:receiver_id>/',
        views.load_more_messages,
        name='load_more_messages',
    ),
    path('feature-job/<int:job_id>/', views.feature_job, name='feature_job'),
    path(
        'auto-shortlist/<int:job_id>/',
        views.auto_shortlist_applicants,
        name='auto_shortlist',
    ),
    path('community/', views.community_hub, name='community_hub'),
    path('get-ai-matches/', views.get_ai_worker_matches, name='get_ai_matches'),
    path('send-message/', views.send_message, name='send_message'),
    path(
        'get-new-messages/<int:user_id>/',
        views.get_new_messages,
        name='get_new_messages',
    ),
    path('api/search-workers/', views.search_workers, name='search_workers'),
    path('api/get-workers/', views.get_workers_list, name='get_workers'),
    path('api/invite-worker/', views.invite_worker, name='invite_worker_api'),
    path('community/', views.community_view, name='community'),
    path('group/<int:pk>/', views.group_detail, name='group_detail'),
    path(
        'accept-invite/<int:notification_id>/',
        views.accept_invite,
        name='accept_invite',
    ),
    path('create-group/', views.create_group, name='create_group'),
    path('accept-invitation/', views.accept_invitation, name='accept_invitation'),
    path(
        'notifications/delete/<int:id>/',
        views.delete_notification,
        name='delete_notification',
    ),
    path(
        'worker/<int:pk>/generate-pdf/', views.generate_pdf, name='generate_pdf'
    ),
]
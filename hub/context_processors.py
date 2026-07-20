from .models import WorkerProfile

def notification_count(request):
    """
    Returns total unread notifications count for the logged-in user.
    """
    if request.user.is_authenticated:
        # अगर आपके पास Notification मॉडल है तो उसका unread count यहाँ निकाल सकते हैं:
        # count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': 0}
    return {'unread_notifications_count': 0}


def user_profile_context(request):
    """
    Returns the logged-in worker's profile globally across all templates.
    """
    if request.user.is_authenticated:
        try:
            return {'user_profile': WorkerProfile.objects.get(user=request.user)}
        except WorkerProfile.DoesNotExist:
            return {'user_profile': None}
    return {'user_profile': None}
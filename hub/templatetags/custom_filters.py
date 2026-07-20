from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter(name='is_online')
def is_online(user):
    # 'hasattr' check karta hai ki kya user ke paas 'last_seen' hai
    if hasattr(user, 'last_seen') and user.last_seen:
        return timezone.now() - user.last_seen < timedelta(minutes=5)
    
    # Extra comma hata diya hai
    return False
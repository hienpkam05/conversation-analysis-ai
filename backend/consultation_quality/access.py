from django.db.models import Q
from .models import Conversation


def can_review(user):
    return user.is_authenticated and user.has_perm("consultation_quality.review_quality")


def visible_conversations(user):
    rows = Conversation.objects.all()
    return rows if can_review(user) else rows.filter(Q(owner=user) | Q(members=user)).distinct()

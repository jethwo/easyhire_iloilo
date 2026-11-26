"""Template tags for user-composed messages."""
from django import template

from apps.core.constants import MESSAGE_MAX_LENGTH

register = template.Library()


@register.simple_tag
def message_max_length():
    """The shared 1000-character cap for messages composed by users.

    Used for the textarea `maxlength` and the live character counter on both
    the employer's contact modal and the jobseeker's apply modal, so the
    number in the UI can never drift from the one the view enforces.
    """
    return MESSAGE_MAX_LENGTH

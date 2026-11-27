import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    """Like {% static %}, but appends ?v=<file mtime> so browsers re-download
    the file whenever it changes instead of serving a stale cached copy."""
    url = static(path)
    try:
        found = finders.find(path)
        if found:
            url += f'?v={int(os.path.getmtime(found))}'
    except Exception:
        pass
    return url


@register.filter
def since1(value):
    """Django's timesince shows two units ("18 hours, 53 minutes"); keep just the
    largest one ("18 hours") for compact labels."""
    from django.utils.timesince import timesince
    try:
        return timesince(value).split(',')[0].replace(' ', ' ')
    except Exception:
        return ''

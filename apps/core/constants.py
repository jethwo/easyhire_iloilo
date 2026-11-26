"""Project-wide constants shared across apps.

Kept here (rather than in settings.py) so templates can pull them in via a
template tag and views can import them without touching Django settings.
"""

# Hard cap on the length of a user-composed message, applied to BOTH sides
# of the platform: an employer's Send Requirements / Schedule Interview body
# (EmployerContact.body) and a jobseeker's application message
# (Application.message). Enforced server-side in the POST handlers and
# mirrored as a `maxlength` + live counter on the textareas, so the limit is
# visible before submit and cannot be bypassed by editing the markup.
MESSAGE_MAX_LENGTH = 1000

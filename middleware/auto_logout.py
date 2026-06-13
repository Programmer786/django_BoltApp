import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.timezone import now

logger = logging.getLogger(__name__)

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip static/media/admin paths
        if any(request.path.startswith(path) for path in ['/static/', '/media/', '/admin/']):
            return self.get_response(request)

        if request.user.is_authenticated:
            last_activity_str = request.session.get('last_activity')
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    elapsed = (now() - last_activity).total_seconds()
                    if elapsed > settings.SESSION_COOKIE_AGE:
                        logout(request)
                        return redirect(settings.LOGIN_URL)
                except (ValueError, TypeError) as e:
                    logger.warning(f"AutoLogoutMiddleware: corrupt session timestamp, resetting. {e}")
                    pass

            request.session['last_activity'] = now().isoformat()

        return self.get_response(request)
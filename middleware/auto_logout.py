from django.conf import settings
from django.shortcuts import redirect
from django.utils.timezone import now
from datetime import datetime
from django.contrib.auth import logout

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip static/media/admin paths
        if any(request.path.startswith(path) for path in ['/static/', '/media/', '/admin/']):
            return self.get_response(request)

        if request.user.is_authenticated:
            try:
                last_activity_str = request.session.get('last_activity')
                if last_activity_str:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    elapsed = (now() - last_activity).total_seconds()
                    if elapsed > settings.SESSION_COOKIE_AGE:
                        logout(request)
                        return redirect(settings.LOGIN_URL)

                # Refresh activity timestamp
                request.session['last_activity'] = now().isoformat()
            except Exception as e:
                print("AutoLogoutMiddleware error:", e)
                logout(request)
                return redirect(settings.LOGIN_URL)

        return self.get_response(request)
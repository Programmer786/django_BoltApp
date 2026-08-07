from base.utils import can_edit_amounts as _can_edit_amounts


def permissions(request):
    """
    Exposes permission flags to every template so list pages don't each need
    to compute them. The per-record city check still happens server-side on
    save — this only decides what gets rendered as editable.
    """
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'can_edit_amounts': False}
    return {'can_edit_amounts': _can_edit_amounts(user)}

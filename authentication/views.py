import os
import re
import random
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.password_validation import validate_password
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

from django.db.models import Q
from base.utils import log_activity, get_manager_city
from .models import Profile, Note


def login_page(request):
    if request.user.is_authenticated:
        return redirect('index')

    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.warning(request, 'Account not found.')
            return HttpResponseRedirect(request.path_info)

        if not user_obj.profile.is_email_verified:
            messages.warning(request, 'Your account is not verified.')
            return HttpResponseRedirect(request.path_info)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return redirect('index')
            else:
                messages.error(request, 'Account is disabled.')
        else:
            messages.error(request, 'Invalid username or password.')

        return HttpResponseRedirect(request.path_info)

    return render(request, 'authentication/login.html', {'next': next_url})


def register_page(request):
    """
    Handle user registration with email verification.
    Creates a new user account; Profile and email_token handled via signal.
    """
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        city = request.POST.get('city')

        if User.objects.filter(username=username).exists():
            messages.warning(request, 'Username is already taken.')
            return HttpResponseRedirect(request.path_info)

        if User.objects.filter(email=email).exists():
            messages.warning(request, 'Email is already taken.')
            return HttpResponseRedirect(request.path_info)

        try:
            # Create user (no 'city' here)
            user_obj = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username
            )
            user_obj.set_password(password)
            user_obj.save()

            # Update profile (city)
            user_obj.profile.city = city
            user_obj.profile.save()

            log_activity(user=user_obj, action=f"Registered new account: {user_obj.username}", request=request)
            messages.success(request, 'An email has been sent to your mail.')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return HttpResponseRedirect(request.path_info)

    return render(request, 'authentication/register.html')


def activate_email(request, email_token):
    """
    Activate a user account using email verification token.
    """
    try:
        user = Profile.objects.get(email_token=email_token)
        user.is_email_verified = True
        user.save()
        log_activity(user=user.user, action=f"Email verified for account: {user.user.username}", request=request)
        messages.success(request, 'Your account has been verified successfully!')
        return redirect('login')
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid email verification token.')
        return redirect('login')
    except Exception as e:
        messages.error(request, f'Activation failed: {str(e)}')
        return redirect('login')


@login_required
def users_profile(request, user_id):
    """
    Display user profile information.
    Requires authentication.
    """
    user = get_object_or_404(User, id=user_id)
    context = {
        'user_profile': user,
        'title': 'Profile'
    }
    return render(request, 'authentication/update_profile.html', context)


@login_required
def update_profile(request):
    if request.method != 'POST':
        return redirect('users_profile', user_id=request.user.id)

    user = request.user
    profile = user.profile

    try:
        # User model fields
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name).title()
        user.last_name = request.POST.get('last_name', user.last_name).title()
        user.save()

        # Profile model fields
        profile.phone = request.POST.get('phone', profile.phone)
        profile.country = request.POST.get('country', profile.country)
        profile.address = request.POST.get('address', profile.address)
        profile.bio = request.POST.get('bio', profile.bio)

        profile.save()
        log_activity(user=user, action=f"Updated profile info for: {user.username}", request=request)
        messages.success(request, 'Profile updated successfully!')

    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('users_profile', user_id=user.id)


@login_required
def change_password(request):
    if request.method != 'POST':
        return redirect('users_profile', user_id=request.user.id)

    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    renew_password = request.POST.get('renew_password')
    user = request.user

    try:
        if not user.check_password(current_password):
            raise ValidationError('Invalid current password.')
        if new_password != renew_password:
            raise ValidationError('New passwords do not match.')

        validate_password(new_password, user)
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        log_activity(user=user, action=f"Changed own password: {user.username}", request=request)
        messages.success(request, 'Password changed successfully!')
    except ValidationError as e:
        messages.error(request, str(e) if isinstance(e, str) else ', '.join(e.messages))

    return redirect('users_profile', user_id=user.id)


@login_required
def disable_role_user(request):
    if request.method != 'POST':
        return redirect('users_profile', user_id=request.user.id)

    user = request.user
    try:
        user.is_active = 0
        user.save()
        log_activity(user=user, action=f"Disabled own account: {user.username}", request=request)
        messages.success(request, 'Record Successfully Disable!')
    except ValidationError as e:
        messages.error(request, str(e) if isinstance(e, str) else ', '.join(e.messages))

    return redirect('users_profile', user_id=user.id)


@login_required
def enable_role_user(request):
    if request.method != 'POST':
        return redirect('users_profile', user_id=request.user.id)

    user = request.user
    try:
        user.is_active = 1
        user.save()
        log_activity(user=user, action=f"Enabled own account: {user.username}", request=request)
        messages.success(request, 'Record Successfully Enable!')
    except ValidationError as e:
        messages.error(request, str(e) if isinstance(e, str) else ', '.join(e.messages))

    return redirect('users_profile', user_id=user.id)


@login_required
def update_profile_image(request):
    if request.method != 'POST':
        return redirect('users_profile', user_id=request.user.id)

    user = request.user
    profile = user.profile

    try:
        if 'profile_image' in request.FILES:
            uploaded_file = request.FILES['profile_image']

            # Validation
            if not uploaded_file.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError("Only JPG, JPEG, and PNG files are allowed.")
            if uploaded_file.size > 5 * 1024 * 1024:
                raise ValidationError("File size must be less than 5MB.")

            # Delete old image
            if profile.profile_image and os.path.isfile(profile.profile_image.path):
                os.remove(profile.profile_image.path)

            # Generate random filename
            _, ext = os.path.splitext(uploaded_file.name)
            random_number = random.randint(100000, 999999)
            new_filename = f"{random_number}_{user.id}{ext}"

            # Save renamed file
            profile.profile_image.save(new_filename, uploaded_file)

            profile.save()
            messages.success(request, "Profile image successfully updated!")
            # Add log
            log_activity(user=user, action="Updated profile", request=request)
        else:
            messages.error(request, "Please upload a profile image.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect('users_profile', user_id=user.id)


def user_has_records(user):
    """
    Return True if the user has created at least one record in any module.
    Used to lock the City/Region once records exist (city groups those records).
    """
    return (
        user.new_certificates.exists() or
        user.new_cards.exists() or
        user.new_trainings.exists() or
        user.new_non_destructive_testing.exists() or
        user.new_calibrations.exists()
    )


@login_required
def manage_accounts(request):
    """
    Display and manage user accounts.
    Superuser: sees everyone. Manager: sees only employees of their city.
    """
    manager_city = get_manager_city(request.user)

    users_list = User.objects.filter(is_superuser=False).order_by('-date_joined')

    # Manager sees only employees (not other staff/managers) of their own city
    if manager_city:
        users_list = users_list.filter(is_staff=False, profile__city=manager_city)

    # Search filter: username / full name / email
    q = request.GET.get('q', '').strip()
    if q:
        users_list = users_list.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    # City filter (superuser only; managers are already locked to their city)
    city_filter = request.GET.get('city', '').strip()
    if city_filter and not manager_city:
        users_list = users_list.filter(profile__city=city_filter)

    total_accounts = users_list.count()

    # Pagination
    paginator = Paginator(users_list, 10)
    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    # Flag each user: City/Region is locked once they have any records
    for account in users:
        account.has_records = user_has_records(account)

    context = {
        'users': users,
        'total_accounts': total_accounts,
        'manager_city': manager_city,
        'search_q': q,
        'city_filter': city_filter,
        'title': 'Manage Accounts',
        'sidebar_active': 'manage_accounts',
    }
    return render(request, 'authentication/manage_accounts.html', context)



from base.emails import send_account_created_email
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@login_required
def edit_user(request, user_id):
    """
    Edit user details - handles both GET and POST requests
    """
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit users.')
        return redirect('manage_accounts')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get or create user profile
    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        try:
            # Get form data with proper cleaning
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip().lower()
            city = request.POST.get('city', '').strip()

            # Lock City/Region once the user has created any records:
            # changing it would mis-group their existing entries.
            if user_has_records(user):
                city = profile.city

            # Basic validation
            if not all([first_name, last_name, username, email, city]):
                messages.error(request, 'All fields are required.')
                return redirect('manage_accounts')
                
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                messages.error(request, 'Please enter a valid email address.')
                return redirect('manage_accounts')
                
            # Check if username is taken by another user
            if username != user.username and User.objects.filter(username__iexact=username).exists():
                messages.error(request, 'This username is already taken.')
                return redirect('manage_accounts')
                
            # Check if email is taken by another user
            if email != user.email and User.objects.filter(email__iexact=email).exists():
                messages.error(request, 'This email is already registered.')
                return redirect('manage_accounts')
            
            # Update user details
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.email = email
            
            # Save user and profile
            user.save()
            profile.city = city
            profile.save()

            log_activity(user=request.user, action=f"Edited account: {user.username} (by {request.user.username})", request=request)
            messages.success(request, f'User {user.username} has been updated successfully.')
            return redirect('manage_accounts')
            
        except Exception as e:
            messages.error(request, f'An error occurred while updating the user: {str(e)}')
            return redirect('manage_accounts')
    
    # For GET request, return JSON data for the modal
    profile = getattr(user, 'profile', None)
    user_data = {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'city': profile.city if profile else ''
    }
    return JsonResponse(user_data)


@login_required
def add_account(request):
    """
    Handle user registration and send account details via email.
    """
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        city = request.POST.get('city')
        role = request.POST.get('role')  # 'manager' or 'employee'

        # Managers can only add employees in their own city
        adding_manager_city = get_manager_city(request.user)
        if adding_manager_city:
            city = adding_manager_city
            role = 'employee'

        if User.objects.filter(username=username).exists():
            messages.warning(request, 'Username is already taken.')
            return redirect('manage_accounts')

        if User.objects.filter(email=email).exists():
            messages.warning(request, 'Email is already taken.')
            return redirect('manage_accounts')

        try:
            # Create the user (Manager -> is_staff=True, Employee -> is_staff=False)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_staff=(role == 'manager')
            )
            
            # Update profile
            user.profile.city = city
            user.profile.save()
            
            # Get the email token from the user's profile
            email_token = user.profile.email_token
            if not email_token:
                # Generate a new token if one doesn't exist
                email_token = str(uuid.uuid4())
                user.profile.email_token = email_token
                user.profile.save()
            
            # Send account creation email with activation link
            send_account_created_email(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email_token=email_token
            )
            
            log_activity(user=request.user, action=f"Created account for {username} ({role})", request=request)
            messages.success(request, f'User account created successfully. Login details sent to {email}.')
            return redirect('manage_accounts')

        except Exception as e:
            # If email sending fails, still create the user but log the error
            messages.warning(request, f'User created but failed to send email: {str(e)}')
            return redirect('manage_accounts')

    return redirect('manage_accounts')


@login_required
def toggle_user_status(request, user_id):
    """
    Toggle user active status (activate/deactivate)
    """
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied')
        return redirect('manage_accounts')
    
    try:
        user = User.objects.get(id=user_id)
        # Prevent deactivating yourself
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account')
            return redirect('manage_accounts')
        
        # Get the action from the form
        is_active = request.POST.get('is_active') == 'true'
        user.is_active = is_active
        user.save()
        
        action = 'activated' if is_active else 'deactivated'
        log_activity(user=request.user, action=f"Account {action}: {user.username}", request=request)
        messages.success(request, f'User {action} successfully')
        
    except User.DoesNotExist:
        messages.error(request, 'User not found')
    except Exception as e:
        messages.error(request, f'Error toggling user status: {str(e)}')
    
    return redirect('manage_accounts')


@login_required
def admin_change_password(request, user_id):
    """
    Allow admins to change user passwords without requiring current password
    """
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied')
        return redirect('manage_accounts')

    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)

            # Prevent changing another superuser's password
            if user.is_superuser and user != request.user:
                messages.error(request, 'Cannot reset another superuser\'s password.')
                return redirect('manage_accounts')

            new_password = request.POST.get('new_password')
            
            if not new_password or len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long')
                return redirect('manage_accounts')
                
            user.set_password(new_password)
            user.save()

            # Update session if admin changed their own password
            if user == request.user:
                update_session_auth_hash(request, user)

            log_activity(user=request.user, action=f"Reset password for: {user.username} (by {request.user.username})", request=request)
            messages.success(request, 'Password updated successfully')
            
        except User.DoesNotExist:
            messages.error(request, 'User not found')
        except Exception as e:
            messages.error(request, f'Error updating password: {str(e)}')
    
    return redirect('manage_accounts')


def logout_page(request):
    """
    Handle user logout and redirect to login page.
    """
    logout(request)
    return redirect('login')


@login_required
def logs_activity(request):
    """
    Display user activity logs with optional date range filtering.
    Requires authentication.
    """
    from .models import ActivityLog
    from django.db.models import Q
    from datetime import datetime
    
    # Scope logs by role:
    # - Superuser: all logs
    # - Manager: logs for users in their city + their own logs
    # - Employee: only their own logs
    logs_list = ActivityLog.objects.select_related('user').order_by('-timestamp')
    manager_city = get_manager_city(request.user)
    if manager_city:
        city_user_ids = User.objects.filter(
            is_superuser=False, is_staff=False, profile__city=manager_city
        ).values_list('id', flat=True)
        logs_list = logs_list.filter(
            Q(user=request.user) | Q(user__id__in=city_user_ids)
        )
    elif not request.user.is_superuser:
        logs_list = logs_list.filter(user=request.user)
    
    from datetime import date, timedelta
    
    # Get filter parameters with defaults (last 30 days)
    today = date.today()
    default_start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    default_end_date = today.strftime('%Y-%m-%d')
    
    start_date = request.GET.get('start_date', default_start_date)
    end_date = request.GET.get('end_date', default_end_date)
    
    # Apply date filters if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            logs_list = logs_list.filter(timestamp__date__gte=start_date)
        except (ValueError, TypeError):
            # If date format is invalid, ignore the filter
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the entire end date
            logs_list = logs_list.filter(timestamp__date__lte=end_date)
        except (ValueError, TypeError):
            # If date format is invalid, ignore the filter
            pass
    
    # Pagination - 25 logs per page
    paginator = Paginator(logs_list, 25)
    page = request.GET.get('page')
    
    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)
    
    # Add start_index to show correct count in template
    if logs.number == 1:
        start_index = 1
    else:
        start_index = (logs.number - 1) * paginator.per_page + 1
    
    context = {
        'logs': logs,
        'total_logs': logs_list.count(),
        'start_index': start_index,
        'end_index': start_index + len(logs.object_list) - 1,
        'title': 'Activity Logs',
        'sidebar_active': 'logs_activity',
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    }
    return render(request, 'authentication/logs_activity.html', context)


@login_required
def manage_notes(request):
    """
    Display and manage user notes.
    Requires authentication.
    """
    notes_list = Note.objects.all().order_by('type')
    
    # Pagination
    paginator = Paginator(notes_list, 10)  # Show 10 notes per pages
    page = request.GET.get('page')
    
    try:
        notes = paginator.page(page)
    except PageNotAnInteger:
        notes = paginator.page(1)
    except EmptyPage:
        notes = paginator.page(paginator.num_pages)
    
    # Types that don't have a note yet (Note.type is unique -> one note per type)
    used_types = set(notes_list.values_list('type', flat=True))
    available_types = [
        (value, label) for value, label in Note.NoteType.choices
        if value not in used_types
    ]

    context = {
        'notes': notes,
        'total_notes': notes_list.count(),
        'available_types': available_types,
        'title': 'Manage Notes',
        'sidebar_active': 'manage_notes',
    }
    return render(request, 'authentication/manage_notes.html', context)


@login_required
@require_http_methods(["POST"])
def add_note(request):
    """Create a note for a given type (one note per type)."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to add notes.')
        return redirect('manage_notes')

    note_type = request.POST.get('type', '').strip()
    note_text = request.POST.get('note', '').strip()

    valid_types = {value for value, _ in Note.NoteType.choices}
    if note_type not in valid_types:
        messages.error(request, 'Please select a valid note type.')
        return redirect('manage_notes')

    if Note.objects.filter(type=note_type).exists():
        messages.warning(request, f"A note for '{note_type}' already exists.")
        return redirect('manage_notes')

    Note.objects.create(type=note_type, note=note_text)
    log_activity(user=request.user, action=f"Created note for type: {note_type}", request=request)
    messages.success(request, 'Note added successfully.')
    return redirect('manage_notes')


@login_required
@require_http_methods(["POST"])
def update_note(request, note_id):
    """Update the text of an existing note."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit notes.')
        return redirect('manage_notes')

    note = get_object_or_404(Note, id=note_id)
    note.note = request.POST.get('note', '').strip()
    note.save()
    log_activity(user=request.user, action=f"Updated note for type: {note.type}", request=request)
    messages.success(request, 'Note updated successfully.')
    return redirect('manage_notes')
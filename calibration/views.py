from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.timezone import now  # Make sure this import is present
from base.utils import (
    items_per_page, current_date, get_manager_city,
    can_access_record, can_manage_record, assert_city_allowed, safe_cell,
    handle_amount_field_update, redirect_back, can_approve_reject, log_activity,
)
from calibration.models import Calibration
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse


@login_required
def manage_calibration(request):
    # Get the current logged-in user
    current_user = request.user
    total_calibrations = 0
    total_jeddah_calibrations = pending_jeddah_calibrations = verified_jeddah_calibrations = 0
    total_riyadh_calibrations = pending_riyadh_calibrations = verified_riyadh_calibrations = 0
    total_neom_calibrations = pending_neom_calibrations = verified_neom_calibrations = 0
    total_damman_calibrations = pending_damman_calibrations = verified_damman_calibrations = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0
    total_paid_jeddah_calibrations = total_paid_riyadh_calibrations = total_paid_neom_calibrations = total_paid_damman_calibrations = 0
    total_unpaid_jeddah_calibrations_count = total_unpaid_riyadh_calibrations_count = total_unpaid_neom_calibrations_count = total_unpaid_damman_calibrations_count = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    calibration_list = Calibration.objects.none()  # Default to an empty queryset

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        calibration_list = Calibration.objects.filter(isApprove=True).order_by('-cert_no')
        # Apply city filter if selected
        if selected_city:
            calibration_list = calibration_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            calibration_list = calibration_list.filter(
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_calibrations = len(calibration_list)

        total_jeddah_calibrations = Calibration.objects.filter(user__profile__city__iexact="Jeddah").count()
        pending_jeddah_calibrations = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=False).count()
        verified_jeddah_calibrations = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).count()

        total_riyadh_calibrations = Calibration.objects.filter(user__profile__city__iexact="Riyadh").count()
        pending_riyadh_calibrations = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=False).count()
        verified_riyadh_calibrations = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).count()

        total_neom_calibrations = Calibration.objects.filter(user__profile__city__iexact="NEOM").count()
        pending_neom_calibrations = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=False).count()
        verified_neom_calibrations = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).count()

        total_damman_calibrations = Calibration.objects.filter(user__profile__city__iexact="Damman").count()
        pending_damman_calibrations = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=False).count()
        verified_damman_calibrations = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).count()

        # Paid Cards
        total_paid_jeddah_calibrations = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).count()
        total_paid_riyadh_calibrations = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).count()
        total_paid_neom_calibrations = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).count()
        total_paid_damman_calibrations = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).count()

        # Unpaid Cards
        total_unpaid_jeddah_calibrations_count = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_calibrations_count = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_calibrations_count = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_calibrations_count = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()

        # Paid Amount
        total_paid_jeddah_amount = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0

    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        calibration_list = Calibration.objects.filter(user=current_user, isApprove=False, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

        if searching_query:
            calibration_list = calibration_list.filter(Q(cert_no__icontains=searching_query))

    paginator = Paginator(calibration_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        calibrations = paginator.page(int(page))
    except PageNotAnInteger:
        calibrations = paginator.page(1)
    except EmptyPage:
        calibrations = paginator.page(paginator.num_pages)

    context = {
        'title': 'Manage Calibration',
        'calibrations': calibrations,
        'current_date': current_date,
        'total_calibrations': total_calibrations,
        'total_jeddah_calibrations': total_jeddah_calibrations,
        'pending_jeddah_calibrations': pending_jeddah_calibrations,
        'verified_jeddah_calibrations': verified_jeddah_calibrations,
        'total_riyadh_calibrations': total_riyadh_calibrations,
        'pending_riyadh_calibrations': pending_riyadh_calibrations,
        'verified_riyadh_calibrations': verified_riyadh_calibrations,
        'total_neom_calibrations': total_neom_calibrations,
        'pending_neom_calibrations': pending_neom_calibrations,
        'verified_neom_calibrations': verified_neom_calibrations,
        'total_damman_calibrations': total_damman_calibrations,
        'pending_damman_calibrations': pending_damman_calibrations,
        'verified_damman_calibrations': verified_damman_calibrations,
        'total_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_jeddah_calibrations': total_paid_jeddah_calibrations,
        'total_unpaid_jeddah_calibrations_count': total_unpaid_jeddah_calibrations_count,
        'total_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_riyadh_calibrations': total_paid_riyadh_calibrations,
        'total_unpaid_riyadh_calibrations_count': total_unpaid_riyadh_calibrations_count,
        'total_neom_amount': total_paid_neom_amount,
        'total_paid_neom_calibrations': total_paid_neom_calibrations,
        'total_unpaid_neom_calibrations_count': total_unpaid_neom_calibrations_count,
        'total_damman_amount': total_paid_damman_amount,
        'total_paid_damman_calibrations': total_paid_damman_calibrations,
        'total_unpaid_damman_calibrations_count': total_unpaid_damman_calibrations_count,
        'searching_query': searching_query,  # Include for pre-filling the input
        'manager_city': manager_city,
        'sidebar_active': 'manage_calibration',
    }
    return render(request, 'calibration/manage_calibration.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_calibration_manual(request):
    if request.method == 'GET':
        messages.warning(request, "This form must be submitted through the Manage Calibration page.")
        return redirect('manage_calibration')

    if request.method == 'POST':
        try:
            cert_no = request.POST.get('cert_no')
            if Calibration.objects.filter(cert_no=cert_no).exists():
                messages.warning(request, "Calibration with this Certificate No already exists.")
                return redirect('manage_calibration')

            # Parse date strings
            date_of_calibration_str = request.POST.get('date_of_calibration')
            expiry_date_str = request.POST.get('expiry_date')
            calibration_date = datetime.strptime(date_of_calibration_str, '%Y-%m-%d').date() if date_of_calibration_str else None
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

            # Calculate the remaining months
            remaining_months = None
            if calibration_date and expiry_date:
                delta = relativedelta(expiry_date, calibration_date)
                remaining_months = delta.years * 12 + delta.months

            if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
                messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                return redirect('manage_calibration')

            calibration = Calibration(
                user=request.user,
                sr_no=request.POST.get('sr_no'),
                lh_serial_no=request.POST.get('lh_serial_no'),
                cert_no=cert_no,
                sticker_no=request.POST.get('sticker_no'),
                equipment_name=request.POST.get('equipment_name'),
                company_name=request.POST.get('company_name'),
                received_on=request.POST.get('received_on'),
                technician=request.POST.get('technician'),
                date_of_calibration=request.POST.get('date_of_calibration'),
                expiry_date=request.POST.get('expiry_date'),
                validity=remaining_months,
                requested_by=request.POST.get('requested_by'),
                prepared_by=request.POST.get('prepared_by'),
                wasted_serial=request.POST.get('wasted_serial'),
                invoice_no=request.POST.get('invoice_no'),
                invoice_date=datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date() if request.POST.get('invoice_date') else now().date(),
                total_amount=Decimal(request.POST.get('total_amount')),
                amount=Decimal(request.POST.get('amount')),
                cash_bank=request.POST.get('cash_bank'),
                client_rep_name=request.POST.get('client_rep_name'),
                client_rep_number=request.POST.get('client_rep_number'),
                email=request.POST.get('email'),
                remarks=request.POST.get('remarks'),
            )

            calibration._request_user = request.user
            calibration._request = request
            calibration._activity_message = f"Manually added calibration certificate {calibration.cert_no}"
            calibration.save()
            messages.success(request, "Calibration added successfully.")

        except Exception as e:
            messages.error(request, f"Error adding calibration: {e}")
            return redirect('manage_calibration')

    return redirect('manage_calibration')


@login_required
def update_calibration(request, uid):
    calibration = get_object_or_404(Calibration, uid=uid)
    if not can_access_record(request.user, calibration):
        messages.error(request, 'You do not have permission to edit this calibration.')
        return redirect('manage_calibration')

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('manage_calibration')
        calibration.sr_no = request.POST.get('sr_no')
        calibration.lh_serial_no = request.POST.get('lh_serial_no')
        calibration.cert_no = request.POST.get('cert_no')
        calibration.sticker_no = request.POST.get('sticker_no')
        calibration.equipment_name = request.POST.get('equipment_name')
        calibration.company_name = request.POST.get('company_name')
        calibration.received_on = request.POST.get('received_on')
        calibration.technician = request.POST.get('technician')
        calibration.date_of_calibration = request.POST.get('date_of_calibration')
        calibration.expiry_date = request.POST.get('expiry_date')
        calibration.validity = request.POST.get('validity')
        calibration.requested_by = request.POST.get('requested_by')
        calibration.prepared_by = request.POST.get('prepared_by')
        calibration.wasted_serial = request.POST.get('wasted_serial')
        calibration.invoice_no = request.POST.get('invoice_no')
        calibration.invoice_date = datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date() if request.POST.get('invoice_date') else now().date()
        calibration.total_amount = Decimal(request.POST.get('total_amount'))
        calibration.amount = Decimal(request.POST.get('amount'))
        calibration.cash_bank = request.POST.get('cash_bank')
        calibration.client_rep_name = request.POST.get('client_rep_name')
        calibration.client_rep_number = request.POST.get('client_rep_number')
        calibration.email = request.POST.get('email')
        calibration.remarks = request.POST.get('remarks')

        calibration._request_user = request.user
        calibration._request = request
        calibration._activity_message = f"Updated calibration certificate {calibration.cert_no}"
        calibration.save()

        messages.success(request, "Calibration updated successfully.")
    return redirect('manage_calibration')


@login_required
def pending_calibration(request):
    # Get the current logged-in user
    current_user = request.user

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    calibration_list = Calibration.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        calibration_list = Calibration.objects.filter(isApprove=False, isReject=False).order_by('-cert_no')
        # Apply city filter if selected
        if selected_city:
            calibration_list = calibration_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            calibration_list = calibration_list.filter(
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        calibration_list = Calibration.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago, isApprove=False, isReject=False).order_by('-cert_no')

        if searching_query:
            calibration_list = calibration_list.filter(Q(cert_no__icontains=searching_query))

    paginator = Paginator(calibration_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        calibrations = paginator.page(int(page))
    except PageNotAnInteger:
        calibrations = paginator.page(1)
    except EmptyPage:
        calibrations = paginator.page(paginator.num_pages)

    context = {
        'title': 'Pending Certificates',
        'calibrations': calibrations,
        'current_date': current_date,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'pending_calibration',
    }
    return render(request, 'calibration/pending_calibration.html', context)


@login_required
def rejected_calibration(request):
    """
    Rejected calibration records — previously invisible everywhere once
    isReject=True: excluded from Pending on purpose, and not shown by
    Manage (isApprove required). This is the only place they can be
    found and restored.
    """
    current_user = request.user
    if not (current_user.is_superuser or current_user.is_staff):
        messages.error(request, 'You do not have permission to view rejected calibration records.')
        return redirect('index')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()

    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    calibration_list = Calibration.objects.filter(isReject=True).order_by('-updated_at')
    if selected_city:
        calibration_list = calibration_list.filter(user__profile__city__iexact=selected_city)
    if searching_query:
        calibration_list = calibration_list.filter(
            Q(cert_no__icontains=searching_query) |
            Q(company_name__icontains=searching_query)
        )

    total_calibrations = calibration_list.count()
    paginator = Paginator(calibration_list, items_per_page)
    page = request.GET.get('page', '1')
    try:
        calibrations = paginator.page(int(page))
    except PageNotAnInteger:
        calibrations = paginator.page(1)
    except EmptyPage:
        calibrations = paginator.page(paginator.num_pages)

    context = {
        'title': 'Rejected Calibration',
        'calibrations': calibrations,
        'current_date': current_date,
        'total_calibrations': total_calibrations,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'rejected_calibration',
    }
    return render(request, 'calibration/rejected_calibration.html', context)


@login_required
@require_POST
def restore_rejected_calibration(request, uid):
    """Move a rejected calibration record back to Pending."""
    calibration = get_object_or_404(Calibration, uid=uid)
    if not can_manage_record(request.user, calibration):
        messages.error(request, 'You do not have permission to restore this calibration record.')
        return redirect_back(request, 'rejected_calibration')

    if not calibration.isReject:
        messages.warning(request, f'Calibration {calibration.cert_no} is not rejected.')
        return redirect_back(request, 'rejected_calibration')

    calibration.isReject = False
    calibration._request_user = request.user
    calibration._request = request
    approver = request.user.get_full_name() or request.user.username
    calibration._activity_message = f"Restored rejected calibration {calibration.cert_no} to pending by {approver}"
    calibration.save()

    messages.success(request, f'Calibration {calibration.cert_no} has been restored to Pending.')
    return redirect_back(request, 'rejected_calibration')


@login_required
@require_POST
def delete_rejected_calibration(request, uid):
    """Permanently delete a rejected calibration record after confirmation."""
    calibration = get_object_or_404(Calibration, uid=uid)
    if not can_manage_record(request.user, calibration):
        messages.error(request, 'You do not have permission to delete this calibration record.')
        return redirect_back(request, 'rejected_calibration')

    if not calibration.isReject:
        messages.warning(request, f'Calibration {calibration.cert_no} is not rejected.')
        return redirect_back(request, 'rejected_calibration')

    cert_no = calibration.cert_no
    log_activity(
        user=request.user,
        action=f"Permanently deleted rejected calibration {cert_no} by {request.user.get_full_name() or request.user.username}",
        request=request,
    )
    calibration.delete()

    messages.success(request, f'Calibration {cert_no} has been permanently deleted.')
    return redirect_back(request, 'rejected_calibration')


@login_required
def approve_reject_calibration(request, uid):
    calibration = get_object_or_404(Calibration, uid=uid)
    if not can_approve_reject(request.user, calibration):
        messages.error(request, 'You do not have permission to approve or reject calibration records. Ask an admin to grant it from Manage Accounts.')
        return redirect_back(request, 'pending_calibration')

    if request.method == 'POST':
        # Check which button was clicked
        action = request.POST.get('action')
        if action == 'approve':
            calibration.isApprove = True
            calibration.isReject = False
            messages.success(request, 'Calibration approved and updated successfully.')
        elif action == 'reject':
            calibration.isApprove = False
            calibration.isReject = True
            messages.warning(request, 'Calibration rejected and updated successfully.')

        approver = request.user.get_full_name() or request.user.username
        owner = calibration.user.get_full_name() or calibration.user.username
        verdict = 'Approved' if calibration.isApprove else 'Rejected'
        calibration._request_user = request.user
        calibration._request = request
        calibration._activity_message = f"{verdict} calibration {calibration.cert_no} (owner: {owner}) by {approver}"
        calibration.save()
    return redirect_back(request, 'pending_calibration')


@login_required
def export_calibration_data_excel(request, model_name, city):
    if model_name != "calibration":
        return HttpResponse("Invalid category", status=400)
    if not assert_city_allowed(request.user, city):
        messages.error(request, 'You do not have permission to export this city.')
        return redirect('manage_calibration')

    queryset = Calibration.objects.select_related('user', 'user__profile').filter(user__profile__city__iexact=city)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{model_name.title()} - {city.title()}"

    headers = [
        "S.No", "LH Serial No", "Cert No", "Sticker No", "Equipement Name", "Company Name",
        "Received on", "Technician", "Date of Calibration", "Next Date of Cal", "Validity", "Status",
        "Note", "Requested By", "Prepared By", "Wasted Serial No", "Invoice No", "Total Amount", "Paid Amount", "Cash/Bank",
        "Client Representative Name", "Client Representative Number", "Email", "Remarks"
    ]
    ws.append(headers)

    # Style the header
    header_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Add data rows
    for idx, obj in enumerate(queryset, start=1):
        ws.append([safe_cell(v) for v in [
            idx,
            obj.lh_serial_no,
            obj.cert_no,
            obj.sticker_no,
            obj.equipment_name,
            obj.company_name,
            obj.received_on,
            obj.technician,
            obj.date_of_calibration,
            obj.expiry_date,
            obj.validity,
            obj.status,
            obj.note,
            obj.requested_by,
            obj.prepared_by,
            obj.wasted_serial,
            obj.invoice_no,
            obj.total_amount,
            obj.amount,
            obj.cash_bank,
            obj.client_rep_name,
            obj.client_rep_number,
            obj.email,
            obj.remarks,
        ]])

    # Export to Excel response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{model_name}_{city}_export.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@login_required
def unpaid_calibration(request):
    # Get the current logged-in user
    current_user = request.user
    total_unpaid_calibrations = 0
    total_unpaid_jeddah_calibrations = total_unpaid_riyadh_calibrations = total_unpaid_neom_calibrations = total_unpaid_damman_calibrations = 0

    searching_query = request.GET.get('searching_query', '').strip()
    calibration_list = Calibration.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        calibration_list = Calibration.objects.filter(isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).order_by('-cert_no')

        # Managers only see their own city's records
        if manager_city:
            calibration_list = calibration_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            calibration_list = calibration_list.filter(Q(cert_no__icontains=searching_query))

        total_unpaid_calibrations = calibration_list.count()

        # Unpaid Card
        total_unpaid_jeddah_calibrations = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_calibrations = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_calibrations = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_calibrations = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        calibration_list = Calibration.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

        if searching_query:
            calibration_list = calibration_list.filter(Q(cert_no__icontains=searching_query))

    paginator = Paginator(calibration_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        calibrations = paginator.page(int(page))
    except PageNotAnInteger:
        calibrations = paginator.page(1)
    except EmptyPage:
        calibrations = paginator.page(paginator.num_pages)

    context = {
        'title': 'Unpaid Calibrations',
        'calibrations': calibrations,
        'current_date': current_date,
        'total_unpaid_calibrations': total_unpaid_calibrations,
        'total_unpaid_jeddah_calibrations': total_unpaid_jeddah_calibrations,
        'total_unpaid_riyadh_calibrations': total_unpaid_riyadh_calibrations,
        'total_unpaid_neom_calibrations': total_unpaid_neom_calibrations,
        'total_unpaid_damman_calibrations': total_unpaid_damman_calibrations,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'unpaid_calibration',
    }
    return render(request, 'calibration/unpaid_calibration.html', context)


@login_required
def update_unpaid_calibration(request, uid):
    calibration = get_object_or_404(Calibration, uid=uid)
    if not can_access_record(request.user, calibration):
        messages.error(request, 'You do not have permission to edit this calibration.')
        return redirect('unpaid_calibrations')

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('unpaid_calibrations')
        calibration.sr_no = request.POST.get('sr_no')
        calibration.lh_serial_no = request.POST.get('lh_serial_no')
        calibration.cert_no = request.POST.get('cert_no')
        calibration.sticker_no = request.POST.get('sticker_no')
        calibration.equipment_name = request.POST.get('equipment_name')
        calibration.company_name = request.POST.get('company_name')
        calibration.received_on = request.POST.get('received_on')
        calibration.technician = request.POST.get('technician')
        calibration.date_of_calibration = request.POST.get('date_of_calibration')
        calibration.expiry_date = request.POST.get('expiry_date')
        calibration.validity = request.POST.get('validity')
        calibration.requested_by = request.POST.get('requested_by')
        calibration.prepared_by = request.POST.get('prepared_by')
        calibration.wasted_serial = request.POST.get('wasted_serial')
        calibration.invoice_no = request.POST.get('invoice_no')
        calibration.amount = request.POST.get('amount')
        calibration.cash_bank = request.POST.get('cash_bank')
        calibration.client_rep_name = request.POST.get('client_rep_name')
        calibration.client_rep_number = request.POST.get('client_rep_number')
        calibration.email = request.POST.get('email')
        calibration.remarks = request.POST.get('remarks')

        calibration._request_user = request.user
        calibration._request = request
        calibration._activity_message = f"Updated calibration certificate {calibration.cert_no}"
        calibration.save()

        messages.success(request, "Calibration updated successfully.")
    return redirect('unpaid_calibrations')


@login_required
def paid_calibration(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_calibrations = 0
    total_paid_jeddah_calibrations = total_paid_riyadh_calibrations = total_paid_neom_calibrations = total_paid_damman_calibrations = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    calibration_list = Calibration.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        calibration_list = Calibration.objects.filter(isApprove=True).exclude(amount=0).order_by('-cert_no')

        # Managers only see their own city's records
        if manager_city:
            calibration_list = calibration_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            calibration_list = calibration_list.filter(Q(cert_no__icontains=searching_query))

        total_paid_calibrations = calibration_list.count()

        # Paid Certificate
        total_paid_jeddah_calibrations = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).count()
        total_paid_riyadh_calibrations = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).count()
        total_paid_neom_calibrations = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).count()
        total_paid_damman_calibrations = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).count()

        # Paid Amount
        total_paid_jeddah_amount = Calibration.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Calibration.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Calibration.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Calibration.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        calibration_list = Calibration.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

        if searching_query:
            calibration_list = calibration_list.filter(Q(cert_no__icontains=searching_query))

    paginator = Paginator(calibration_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        calibrations = paginator.page(int(page))
    except PageNotAnInteger:
        calibrations = paginator.page(1)
    except EmptyPage:
        calibrations = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Calibrations',
        'calibrations': calibrations,
        'current_date': current_date,
        'total_paid_calibrations': total_paid_calibrations,
        'total_paid_jeddah_calibrations': total_paid_jeddah_calibrations,
        'total_paid_riyadh_calibrations': total_paid_riyadh_calibrations,
        'total_paid_neom_calibrations': total_paid_neom_calibrations,
        'total_paid_damman_calibrations': total_paid_damman_calibrations,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'paid_calibration',
    }
    return render(request, 'calibration/paid_calibration.html', context)


@login_required
def report_calibration(request):
    current_user = request.user

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    equipment_name = request.GET.get('equipment_name', '').strip()

    calibration_list = Calibration.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # For admin users (superuser or manager)
    if current_user.is_superuser or current_user.is_staff:
        calibration_list = Calibration.objects.all().order_by('-cert_no')

        if status == 'True':
            calibration_list = calibration_list.filter(isApprove=True)
        elif status == 'False':
            calibration_list = calibration_list.filter(isApprove=False)

        if from_date and to_date:
            from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
            calibration_list = calibration_list.filter(created_at__range=[from_dt, to_dt])

        if selected_city:
            calibration_list = calibration_list.filter(user__profile__city__iexact=selected_city)

        if company_name:
            calibration_list = calibration_list.filter(company_name__icontains=company_name)

        if equipment_name:
            calibration_list = calibration_list.filter(equipment_name__icontains=equipment_name)
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        calibration_list = Calibration.objects.filter(
            user=current_user, isApprove=False, created_at__gte=twenty_four_hours_ago
        ).order_by('-cert_no')

    paginator = Paginator(calibration_list, 50)
    page = request.GET.get('page', '1')

    try:
        calibrations = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        calibrations = paginator.page(1)

    context = {
        'title': 'Report Calibration',
        'calibrations': calibrations,
        'current_date': timezone.now().date(),
        'total_calibrations': calibration_list.count(),
        'from_date': from_date,
        'to_date': to_date,
        'selected_city': selected_city,
        'selected_status': status,
        'company_name': company_name,
        'equipment_name': equipment_name,
        'manager_city': manager_city,
        'sidebar_active': 'report_calibration',
    }
    return render(request, 'calibration/report_calibration.html', context)


@login_required
def report_paid_calibration(request):
    current_user = request.user
    total_paid_calibrations = 0
    total_paid_jeddah_calibrations = total_paid_riyadh_calibrations = total_paid_neom_calibrations = total_paid_damman_calibrations = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = total_paid_amount = 0

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    calibration_list = Calibration.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    if current_user.is_superuser or current_user.is_staff:
        calibration_list = Calibration.objects.filter(isApprove=True).exclude(amount=0).order_by('-cert_no')

        # Managers only see their own city's records
        if manager_city:
            calibration_list = calibration_list.filter(user__profile__city__iexact=manager_city)

        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                calibration_list = calibration_list.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass

        total_paid_calibrations = calibration_list.count()

        # Base query for city statistics
        city_queryset = Calibration.objects.filter(isApprove=True).exclude(amount=0)
        if manager_city:
            city_queryset = city_queryset.filter(user__profile__city__iexact=manager_city)

        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                city_queryset = city_queryset.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass

        total_paid_jeddah_calibrations = city_queryset.filter(user__profile__city__iexact="Jeddah").count()
        total_paid_riyadh_calibrations = city_queryset.filter(user__profile__city__iexact="Riyadh").count()
        total_paid_neom_calibrations = city_queryset.filter(user__profile__city__iexact="NEOM").count()
        total_paid_damman_calibrations = city_queryset.filter(user__profile__city__iexact="Damman").count()

        total_paid_jeddah_amount = city_queryset.filter(user__profile__city__iexact="Jeddah").aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = city_queryset.filter(user__profile__city__iexact="Riyadh").aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = city_queryset.filter(user__profile__city__iexact="NEOM").aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = city_queryset.filter(user__profile__city__iexact="Damman").aggregate(Sum('amount'))['amount__sum'] or 0

        total_paid_amount = total_paid_jeddah_amount + total_paid_riyadh_amount + total_paid_neom_amount + total_paid_damman_amount
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        calibration_list = Calibration.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

    paginator = Paginator(calibration_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        calibrations = paginator.page(int(page))
    except PageNotAnInteger:
        calibrations = paginator.page(1)
    except EmptyPage:
        calibrations = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Calibration',
        'calibrations': calibrations,
        'current_date': current_date,
        'total_paid_calibrations': total_paid_calibrations,
        'total_paid_jeddah_calibrations': total_paid_jeddah_calibrations,
        'total_paid_riyadh_calibrations': total_paid_riyadh_calibrations,
        'total_paid_neom_calibrations': total_paid_neom_calibrations,
        'total_paid_damman_calibrations': total_paid_damman_calibrations,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'total_paid_amount': total_paid_amount,
        'from_date': from_date,
        'to_date': to_date,
        'manager_city': manager_city,
        'sidebar_active': 'report_paid_calibration',
    }
    return render(request, 'calibration/report_paid_calibration.html', context)

@login_required
@require_POST
def update_calibration_field(request, uid):
    """Inline Total/Paid Amount edit from the Paid & Unpaid tables."""
    return handle_amount_field_update(request, Calibration, uid)

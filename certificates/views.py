import csv
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_POST, require_http_methods
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from base.utils import (
    current_date, get_manager_city, get_next_numeric_sr_no, items_per_page,
    can_access_record, can_manage_record, assert_city_allowed, safe_cell,
    handle_amount_field_update, redirect_back, can_approve_reject, log_activity,
)
from .models import Certificate

logger = logging.getLogger(__name__)
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


@login_required
def manage_certificates(request):
    # Get the current logged-in user
    current_user = request.user
    total_certificates = 0
    total_jeddah_certificates = pending_jeddah_certificates = verified_jeddah_certificates = 0
    total_riyadh_certificates = pending_riyadh_certificates = verified_riyadh_certificates = 0
    total_neom_certificates = pending_neom_certificates = verified_neom_certificates = 0
    total_damman_certificates = pending_damman_certificates = verified_damman_certificates = 0
    total_paid_jeddah_certificates = total_paid_riyadh_certificates = total_paid_neom_certificates = total_paid_damman_certificates = 0
    total_unpaid_jeddah_certificates = total_unpaid_riyadh_certificates = total_unpaid_neom_certificates = total_unpaid_damman_certificates = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    certificate_list = Certificate.objects.none()  # Default to an empty queryset

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Base query for admin users
        certificate_list = Certificate.objects.filter(isApprove=True, isCancel=False).order_by('-cert_no')

        # Apply city filter if selected
        if selected_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            certificate_list = certificate_list.filter(
                Q(cert_no__icontains=searching_query) | 
                Q(company_name__icontains=searching_query)
            )

        total_certificates = certificate_list.count()

        total_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah").count()
        pending_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=False, isCancel=False).count()
        verified_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).count()

        total_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh").count()
        pending_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=False, isCancel=False).count()
        verified_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).count()

        total_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM").count()
        pending_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=False, isCancel=False).count()
        verified_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).count()

        total_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman").count()
        pending_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=False, isCancel=False).count()
        verified_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).count()

        # Paid Certificate
        total_paid_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).count()

        # Unpaid Certificate
        total_unpaid_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()

        # Paid Amount
        total_paid_jeddah_amount = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        certificate_list = Certificate.objects.filter(user=current_user, isApprove=False, isCancel=False, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

        if searching_query:
            certificate_list = certificate_list.filter(Q(cert_no__icontains=searching_query) | Q(company_name__icontains=searching_query))

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Manage Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_certificates': total_certificates,
        'total_jeddah_certificates': total_jeddah_certificates,
        'pending_jeddah_certificates': pending_jeddah_certificates,
        'verified_jeddah_certificates': verified_jeddah_certificates,
        'total_riyadh_certificates': total_riyadh_certificates,
        'pending_riyadh_certificates': pending_riyadh_certificates,
        'verified_riyadh_certificates': verified_riyadh_certificates,
        'total_neom_certificates': total_neom_certificates,
        'pending_neom_certificates': pending_neom_certificates,
        'verified_neom_certificates': verified_neom_certificates,
        'total_damman_certificates': total_damman_certificates,
        'pending_damman_certificates': pending_damman_certificates,
        'verified_damman_certificates': verified_damman_certificates,
        'total_paid_jeddah_certificates': total_paid_jeddah_certificates,
        'total_paid_riyadh_certificates': total_paid_riyadh_certificates,
        'total_paid_neom_certificates': total_paid_neom_certificates,
        'total_paid_damman_certificates': total_paid_damman_certificates,
        'total_unpaid_jeddah_certificates': total_unpaid_jeddah_certificates,
        'total_unpaid_riyadh_certificates': total_unpaid_riyadh_certificates,
        'total_unpaid_neom_certificates': total_unpaid_neom_certificates,
        'total_unpaid_damman_certificates': total_unpaid_damman_certificates,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,  # Include for pre-filling the input
        'manager_city': manager_city,
        'sidebar_active': 'manage_certificates',
    }
    return render(request, 'certificates/manage_certificates.html', context)


@login_required
def report_certificates(request):
    current_user = request.user
    total_certificates = 0

    # Get filter parameters
    # Keep original date strings for the template
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    equipment_type = request.GET.get('equipment_type', '').strip()

    certificate_list = Certificate.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # For admin users (superuser or manager)
    if current_user.is_superuser or current_user.is_staff:
        certificate_list = Certificate.objects.all().order_by('-cert_no')

        # Apply status filter
        if status == 'True':
            certificate_list = certificate_list.filter(isApprove=True, isCancel=False)
        elif status == 'False':
            certificate_list = certificate_list.filter(isApprove=False, isCancel=False)

        # Apply date range filter with timezone awareness
        if from_date and to_date:
            from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
            certificate_list = certificate_list.filter(created_at__range=[from_dt, to_dt])

        # Apply city filter
        if selected_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)
            
        # Apply company name filter
        if company_name:
            certificate_list = certificate_list.filter(company_name__icontains=company_name)
            
        # Apply equipment type filter
        if equipment_type:
            certificate_list = certificate_list.filter(equipment_type__icontains=equipment_type)

    # For regular users
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        certificate_list = Certificate.objects.filter(
            user=current_user,
            isApprove=False, isCancel=False,
            created_at__gte=twenty_four_hours_ago
        ).order_by('-cert_no')

    # Pagination
    paginator = Paginator(certificate_list, 50)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        certificates = paginator.page(1)

    context = {
        'title': 'Report Certificates',
        'certificates': certificates,
        'current_date': timezone.now().date(),
        'total_certificates': certificate_list.count(),
        'from_date': from_date,
        'to_date': to_date,
        'selected_city': selected_city,
        'selected_status': status,
        'company_name': company_name,
        'equipment_type': equipment_type,
        'manager_city': manager_city,
        'sidebar_active': 'report_certificates',
    }
    return render(request, 'certificates/report_certificates.html', context)


@login_required
def export_certificates_csv(request):
    # Only staff/superusers may bulk-export; managers are locked to their own city
    manager_city = get_manager_city(request.user)
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'You do not have permission to export certificates.')
        return redirect('manage_certificates')

    # Get filter parameters from the request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    equipment_type = request.GET.get('equipment_type', '').strip()

    if manager_city:
        selected_city = manager_city

    # Start with base queryset — select_related avoids N+1 on user/profile per row
    certificate_list = Certificate.objects.select_related('user', 'user__profile').all()
    
    # Apply filters
    if status == 'True':
        certificate_list = certificate_list.filter(isApprove=True, isCancel=False)
    elif status == 'False':
        certificate_list = certificate_list.filter(isApprove=False, isCancel=False)
    
    if from_date and to_date:
        from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
        to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
        certificate_list = certificate_list.filter(created_at__range=[from_dt, to_dt])
    
    if selected_city:
        certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)
        
    # Apply company name filter
    if company_name:
        certificate_list = certificate_list.filter(company_name__icontains=company_name)
        
    # Apply equipment type filter
    if equipment_type:
        certificate_list = certificate_list.filter(equipment_type__icontains=equipment_type)
    
    # Create the HttpResponse object with the appropriate Excel header
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="certificates_export.xlsx"'
    
    # Create a new Excel workbook and add a worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Certificates"
    
    # Define headers
    headers = [
        'S.No', 'Name', 'City', 'LH Serial No', 'Certificate No', 'Sticker No',
        'Eq Serial No', 'Equipment Type', 'Company Name', 'Inspection Date',
        'Expiry Date', 'Remaining Months', 'Plate No', 'Manufacturer',
        'Inspected By', 'Status', 'Note', 'Requested By', 'Prepared By',
        'Wasted Serial', 'Invoice No', 'Invoice Date', 'Total Amount',
        'Paid Amount', 'Cash/Bank', 'Client Representative Name',
        'Client Representative Number', 'Email', 'Remarks', 'Created Date',
        'Payment Status'
    ]
    
    # Write headers to the first row
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill("solid", fgColor="DDDDDD")

    def format_date(date_value):
        if not date_value:
            return ''
        if hasattr(date_value, 'strftime'):
            return date_value.strftime('%Y-%m-%d')
        try:
            # Try to parse the string date if it's in a known format
            from datetime import datetime
            if isinstance(date_value, str):
                # Try common date formats
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S'):
                    try:
                        dt = datetime.strptime(date_value.split(' ')[0], fmt)
                        return dt.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        continue
            return str(date_value).split(' ')[0]  # Return just the date part if parsing fails
        except Exception:
            return str(date_value) if date_value else ''
    
    # Write data rows
    for row_num, cert in enumerate(certificate_list, 2):  # Start from row 2 (after header)
        row_data = [
            row_num - 1,  # S.No
            f"{getattr(cert.user, 'first_name', '') or ''}_{getattr(cert.user, 'last_name', '') or ''}",
            getattr(cert, 'city', '') or '',
            getattr(cert, 'lh_serial_no', '') or '',
            getattr(cert, 'cert_no', '') or '',
            getattr(cert, 'sticker_no', '') or '',
            getattr(cert, 'eq_serial_no', '') or '',
            getattr(cert, 'equipment_type', '') or '',
            getattr(cert, 'company_name', '') or '',
            format_date(getattr(cert, 'inspection_date', None)),
            format_date(getattr(cert, 'expiry_date', None)),
            getattr(cert, 'remaining_months', '') or '',
            getattr(cert, 'plate_no', '') or '',
            getattr(cert, 'manufacturer', '') or '',
            getattr(cert, 'inspected_by', '') or '',
            getattr(cert, 'status', '') or '',
            getattr(cert, 'note', '') or '',
            getattr(cert, 'requested_by', '') or '',
            getattr(cert, 'prepared_by', '') or '',
            getattr(cert, 'wasted_serial', '') or '',
            getattr(cert, 'invoice_no', '') or '',
            format_date(getattr(cert, 'invoice_date', None)),
            float(getattr(cert, 'total_amount', 0) or 0),
            float(getattr(cert, 'amount', 0) or 0),
            getattr(cert, 'cash_bank', '') or '',
            getattr(cert, 'client_rep_name', '') or '',
            getattr(cert, 'client_rep_number', '') or '',
            getattr(cert, 'email', '') or '',
            getattr(cert, 'remarks', '') or '',
            format_date(getattr(cert, 'created_at', None)),
            'Paid' if getattr(cert, 'amount', 0) and float(cert.amount) > 0 else 'Unpaid'
        ]
        
        # Write each cell in the row
        for col_num, cell_value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num, value=safe_cell(cell_value))

    # Auto-size columns based on actual data (runs after all rows are written)
    for col in ws.columns:
        max_length = max(
            (len(str(cell.value)) for cell in col if cell.value is not None),
            default=10
        )
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    # Save the workbook to the response
    output = BytesIO()
    wb.save(output)
    response.write(output.getvalue())
    output.close()

    return response


from django.db import IntegrityError
@login_required
@require_http_methods(["GET", "POST"])
def add_certificate_manual(request):
    if request.method == 'GET':
        messages.warning(request, "This form must be submitted through the Manage Certificate page.")
        return redirect('manage_certificates')

    if request.method == 'POST':
        try:
            cert_no = request.POST.get('cert_no', '').strip()
            
            # Check for empty certificate number
            if not cert_no:
                messages.error(request, "Certificate number cannot be empty.")
                return redirect('manage_certificates')
                
            # Check for duplicate (case-insensitive and trimmed)
            if Certificate.objects.filter(cert_no__iexact=cert_no).exists():
                existing = Certificate.objects.filter(cert_no__iexact=cert_no).first()
                messages.warning(request, f"A certificate with number '{existing.cert_no}' already exists (case-insensitive match).")
                return redirect('manage_certificates')

            # Parse and calculate dates
            inspection_date_str = request.POST.get('inspection_date')
            expiry_date_str = request.POST.get('expiry_date')
            inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date() if inspection_date_str else None
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

            # Calculate remaining months
            remaining_months = None
            if inspection_date and expiry_date:
                delta = relativedelta(expiry_date, inspection_date)
                remaining_months = delta.years * 12 + delta.months

            if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
                messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                return redirect('manage_certificates')

            # Create certificate with the trimmed cert_no
            cert = Certificate(
                user=request.user,
                sr_no=get_next_numeric_sr_no(),
                lh_serial_no=request.POST.get('lh_serial_no'),
                cert_no=cert_no,  # Using the already trimmed cert_no
                sticker_no=request.POST.get('sticker_no'),
                eq_serial_no=request.POST.get('eq_serial_no'),
                equipment_type=request.POST.get('equipment_type'),
                company_name=request.POST.get('company_name'),
                inspection_date=inspection_date_str,
                expiry_date=expiry_date_str,
                remaining_months=remaining_months,
                plate_no=request.POST.get('plate_no'),
                manufacturer=request.POST.get('manufacturer'),
                inspected_by=request.POST.get('inspected_by'),
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

                # New: Inspection Summary Fields
                summary_result_1=request.POST.get('summary_result_1'),
                summary_comments_1=request.POST.get('summary_comments_1'),
                summary_result_2=request.POST.get('summary_result_2'),
                summary_comments_2=request.POST.get('summary_comments_2'),
                summary_result_3=request.POST.get('summary_result_3'),
                summary_comments_3=request.POST.get('summary_comments_3'),
            )

            # Audit log metadata
            cert._request_user = request.user
            cert._request = request
            cert._activity_message = f"Manually created certificate {cert.cert_no}"

            try:
                cert.save()
                messages.success(request, "Certificate added successfully.")
            except IntegrityError as e:
                if 'unique' in str(e).lower():
                    messages.error(request, "This certificate number was just added by another user. Please try a different number.")
                else:
                    messages.error(request, f"Database error while saving: {str(e)}")
                return redirect('manage_certificates')

        except Exception as e:
            messages.error(request, f"Error adding certificate: {str(e)}")
            return redirect('manage_certificates')

    return redirect('manage_certificates')


@login_required
def update_certificate(request, uid):
    cert = get_object_or_404(Certificate, uid=uid)
    if not can_access_record(request.user, cert):
        messages.error(request, 'You do not have permission to edit this certificate.')
        return redirect('manage_certificates')

    if request.method == 'POST':
        try:
            # Validate amounts
            try:
                if Decimal(request.POST.get('amount', 0)) > Decimal(request.POST.get('total_amount', 0)):
                    messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                    return redirect('manage_certificates')
            except (TypeError, ValueError) as e:
                messages.error(request, "Invalid amount values. Please check the form data.")
                return redirect('manage_certificates')

            # Get and validate certificate number
            cert_no = request.POST.get('cert_no', '').strip()
            if not cert_no:
                messages.error(request, "Certificate number cannot be empty.")
                return redirect('manage_certificates')

            # Check for duplicate (case-insensitive, excluding current record)
            if Certificate.objects.exclude(uid=uid).filter(cert_no__iexact=cert_no).exists():
                existing = Certificate.objects.filter(cert_no__iexact=cert_no).first()
                messages.warning(request, f"Another certificate with number '{existing.cert_no}' already exists (case-insensitive match).")
                return redirect('manage_certificates')

            # Update certificate fields
            cert.cert_no = cert_no
            cert.lh_serial_no = request.POST.get('lh_serial_no')
            cert.sticker_no = request.POST.get('sticker_no')
            cert.eq_serial_no = request.POST.get('eq_serial_no')
            cert.equipment_type = request.POST.get('equipment_type')
            cert.company_name = request.POST.get('company_name')
            cert.inspection_date = request.POST.get('inspection_date')
            cert.expiry_date = request.POST.get('expiry_date')
            cert.remaining_months = request.POST.get('remaining_months')
            cert.plate_no = request.POST.get('plate_no')
            cert.manufacturer = request.POST.get('manufacturer')
            cert.inspected_by = request.POST.get('inspected_by')
            cert.requested_by = request.POST.get('requested_by')
            cert.prepared_by = request.POST.get('prepared_by')
            cert.wasted_serial = request.POST.get('wasted_serial')
            cert.invoice_no = request.POST.get('invoice_no')

            # Handle date fields
            try:
                cert.invoice_date = datetime.strptime(
                    request.POST.get('invoice_date'),
                    '%Y-%m-%d'
                ).date() if request.POST.get('invoice_date') else now().date()
            except ValueError:
                cert.invoice_date = now().date()

            # Handle decimal fields
            try:
                cert.total_amount = Decimal(request.POST.get('total_amount', 0))
                cert.amount = Decimal(request.POST.get('amount', 0))
            except (TypeError, ValueError):
                cert.total_amount = Decimal('0')
                cert.amount = Decimal('0')

            cert.cash_bank = request.POST.get('cash_bank')
            cert.client_rep_name = request.POST.get('client_rep_name')
            cert.client_rep_number = request.POST.get('client_rep_number')
            cert.email = request.POST.get('email')
            cert.remarks = request.POST.get('remarks')

            # Summary fields
            cert.summary_result_1 = request.POST.get('summary_result_1')
            cert.summary_comments_1 = request.POST.get('summary_comments_1')
            cert.summary_result_2 = request.POST.get('summary_result_2')
            cert.summary_comments_2 = request.POST.get('summary_comments_2')
            cert.summary_result_3 = request.POST.get('summary_result_3')
            cert.summary_comments_3 = request.POST.get('summary_comments_3')

            # Set audit fields
            cert._request_user = request.user
            cert._request = request
            cert._activity_message = f"Manually updated certificate {cert.cert_no}"

            try:
                cert.save()
                messages.success(request, "Certificate updated successfully.")
            except IntegrityError as e:
                if 'unique' in str(e).lower():
                    messages.error(request, "This certificate number was just updated by another user. Please try again.")
                else:
                    messages.error(request, f"Database error while saving: {str(e)}")
                return redirect('manage_certificates')

        except Exception as e:
            messages.error(request, f"Error updating certificate: {str(e)}")
            return redirect('manage_certificates')

    return redirect('manage_certificates')


@login_required
def pending_certificates(request):
    # Get the current logged-in user
    current_user = request.user

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    certificate_list = Certificate.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        certificate_list = Certificate.objects.filter(isApprove=False, isCancel=False, isReject=False).order_by('-cert_no')
        # Apply city filter if selected
        if selected_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            certificate_list = certificate_list.filter(
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        certificate_list = Certificate.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago, isApprove=False, isCancel=False, isReject=False).order_by('-cert_no')

        if searching_query:
            certificate_list = certificate_list.filter(Q(cert_no__icontains=searching_query) | Q(company_name__icontains=searching_query))

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Pending Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'pending_certificates',
    }
    return render(request, 'certificates/pending_certificates.html', context)


@login_required
def approve_reject_certificate(request, uid):
    cert = get_object_or_404(Certificate, uid=uid)
    if not can_approve_reject(request.user, cert):
        messages.error(request, 'You do not have permission to approve or reject certificates. Ask an admin to grant it from Manage Accounts.')
        return redirect_back(request, 'pending_certificates')

    if request.method == 'POST':
        # Check which button was clicked
        action = request.POST.get('action')
        if action == 'approve':
            cert.isApprove = True
            cert.isReject = False
            messages.success(request, 'Certificate approved and updated successfully.')
        elif action == 'reject':
            cert.isApprove = False
            cert.isReject = True
            messages.warning(request, 'Certificate rejected and updated successfully.')

        approver = request.user.get_full_name() or request.user.username
        owner = cert.user.get_full_name() or cert.user.username
        verdict = 'Approved' if cert.isApprove else 'Rejected'
        cert._request_user = request.user
        cert._request = request
        cert._activity_message = f"{verdict} certificate {cert.cert_no} (owner: {owner}) by {approver}"
        cert.save()
    return redirect_back(request, 'pending_certificates')


@login_required
def export_certificate_data_excel(request, model_name, city):
    if model_name != "certificate":
        return HttpResponse("Invalid category", status=400)
    if not assert_city_allowed(request.user, city):
        messages.error(request, 'You do not have permission to export this city.')
        return redirect('manage_certificates')

    queryset = Certificate.objects.filter(user__profile__city__iexact=city)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{model_name.title()} - {city.title()}"

    # Column headers matching <th>
    headers = [
        "S.No", "LH Serial No", "Cert No", "Sticker No", "Eq Serial No", "Equipment Type",
        "Company Name", "Inspection Date", "Expiry Date", "Remaining Months", "Plate No",
        "Manufacturer", "Inspected By", "Status", "Note", "Requested By", "Prepared By", "Wasted Serial",
        "Invoice No", "Total Amount", "Paid Amount", "Cash/Bank", "Client Representative Name",
        "Client Representative Number", "Email", "Remarks"
    ]
    ws.append(headers)

    # Style header row
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
            obj.eq_serial_no,
            obj.equipment_type,
            obj.company_name,
            obj.inspection_date,
            obj.expiry_date,
            obj.remaining_months,
            obj.plate_no,
            obj.manufacturer,
            obj.inspected_by,
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

    # Export as Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{model_name}_{city}_export.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@login_required
def generate_certificate_pdf(request, cert_uid):
    cert = get_object_or_404(Certificate, uid=cert_uid)
    if not can_access_record(request.user, cert):
        messages.error(request, 'You do not have permission to download this certificate.')
        return redirect('manage_certificates')

    # Load the background certificate design
    template_path = os.path.join(settings.BASE_DIR, 'public', 'static', 'certificates', 'Format.pdf')
    template_reader = PdfReader(open(template_path, "rb"))

    # Output buffer for final PDF
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)


    # Adjusted layout based on visual alignment with Format.pdf
    can.setFont("Times-Bold", 13)
    can.drawCentredString(380, 595, cert.company_name or '')  # Inspection Sponsor/Client
    can.setFont("Times-Roman", 10)
    can.drawString(200, 567, cert.project_location or '')  # Project / Location
    can.drawString(200, 550, cert.inspection_date or '')  # Date of Inspection
    can.drawString(200, 535, cert.date_of_report or '')  # Date of Report
    can.setFont("Times-Bold", 10)
    can.drawString(200, 520, cert.date_of_last_inspection or '')  # Date of Last Inspection
    can.setFont("Times-Roman", 10)
    can.drawString(190, 485, cert.manufacturer or '')  # Manufacturer
    can.drawString(190, 466, cert.type_model_year or '')  # Type / Model / Year
    can.drawString(190, 452, cert.eq_serial_no or '')  # Serial number / ID
    can.drawString(190, 438, cert.plate_no or '')  # Plate Number
    can.setFont("Times-Bold", 12)
    can.setFillColor(colors.red)  # 🔴 Set text color to red
    can.drawString(490, 567, cert.cert_no or '')  # Certificate No
    can.drawString(490, 550, cert.sticker_no or '')  # Sticker No
    can.drawString(490, 535, cert.expiry_date or '')  # Due Date
    can.drawString(490, 520, cert.reference_standard or '')  # Reference Standard
    can.setFont("Times-Roman", 10)
    can.setFillColor(colors.black)  # ✅ Reset to black for the following text
    can.drawString(490, 485, cert.bucket_capacity or '')  # Bucket Capacity

    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleN.fontName = 'Times-Roman'
    styleN.fontSize = 9

    summary_data = [
        ["Description", "Result", "Comments"]
    ]

    summaries = [
        (cert.summary_description_1, cert.summary_result_1, cert.summary_comments_1),
        (cert.summary_description_2, cert.summary_result_2, cert.summary_comments_2),
        (cert.summary_description_3, cert.summary_result_3, cert.summary_comments_3),
    ]

    for desc, result, comment in summaries:
        if desc or result or comment:
            summary_data.append([
                Paragraph(desc or "N/A", styleN),
                Paragraph(result or "N/A", styleN),
                Paragraph(comment or "N/A", styleN)
            ])

    table = Table(summary_data, colWidths=[300, 80, 157])

    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))

    table.wrapOn(can, 500, 500)
    table.drawOn(can, 43, 320)


    # Signature
    can.setFont("Times-Roman", 11)
    can.drawString(105, 210, cert.inspected_by or '')

    # Finalize overlay
    can.save()
    packet.seek(0)

    # Merge overlay with template
    overlay_reader = PdfReader(packet)
    writer = PdfWriter()
    base_page = template_reader.pages[0]
    base_page.merge_page(overlay_reader.pages[0])
    writer.add_page(base_page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    # Return as response
    response = HttpResponse(output, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{cert.cert_no}.pdf"'
    return response


@login_required
def unpaid_certificates(request):
    # Get the current logged-in user
    current_user = request.user
    total_unpaid_certificates = 0
    total_unpaid_jeddah_certificates = total_unpaid_riyadh_certificates = total_unpaid_neom_certificates = total_unpaid_damman_certificates = 0

    searching_query = request.GET.get('searching_query', '').strip()
    certificate_list = Certificate.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        certificate_list = Certificate.objects.filter(isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).order_by('-cert_no')

        # Managers only see their own city's records
        if manager_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            certificate_list = certificate_list.filter(Q(cert_no__icontains=searching_query) | Q(company_name__icontains=searching_query))

        total_unpaid_certificates = certificate_list.count()

        # Unpaid Certificate
        total_unpaid_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        certificate_list = Certificate.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

        if searching_query:
            certificate_list = certificate_list.filter(Q(cert_no__icontains=searching_query) | Q(company_name__icontains=searching_query))

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Unpaid Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_unpaid_certificates': total_unpaid_certificates,
        'total_unpaid_jeddah_certificates': total_unpaid_jeddah_certificates,
        'total_unpaid_riyadh_certificates': total_unpaid_riyadh_certificates,
        'total_unpaid_neom_certificates': total_unpaid_neom_certificates,
        'total_unpaid_damman_certificates': total_unpaid_damman_certificates,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'unpaid_certificates',
    }
    return render(request, 'certificates/unpaid_certificates.html', context)


@login_required
def update_unpaid_certificate(request, uid):
    cert = get_object_or_404(Certificate, uid=uid)
    if not can_access_record(request.user, cert):
        messages.error(request, 'You do not have permission to edit this certificate.')
        return redirect('unpaid_certificates')

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('unpaid_certificates')

        cert.lh_serial_no = request.POST.get('lh_serial_no')
        cert.cert_no = request.POST.get('cert_no')
        cert.sticker_no = request.POST.get('sticker_no')
        cert.eq_serial_no = request.POST.get('eq_serial_no')
        cert.equipment_type = request.POST.get('equipment_type')
        cert.company_name = request.POST.get('company_name')
        cert.inspection_date = request.POST.get('inspection_date')
        cert.expiry_date = request.POST.get('expiry_date')
        cert.remaining_months = request.POST.get('remaining_months')
        cert.plate_no = request.POST.get('plate_no')
        cert.manufacturer = request.POST.get('manufacturer')
        cert.inspected_by = request.POST.get('inspected_by')
        cert.requested_by = request.POST.get('requested_by')
        cert.prepared_by = request.POST.get('prepared_by')
        cert.wasted_serial = request.POST.get('wasted_serial')
        cert.invoice_no = request.POST.get('invoice_no')
        cert.total_amount = Decimal(request.POST.get('total_amount'))
        cert.amount = Decimal(request.POST.get('amount'))
        cert.cash_bank = request.POST.get('cash_bank')
        cert.client_rep_name = request.POST.get('client_rep_name')
        cert.client_rep_number = request.POST.get('client_rep_number')
        cert.email = request.POST.get('email')
        cert.remarks = request.POST.get('remarks')
        cert.summary_result_1 = request.POST.get('summary_result_1')
        cert.summary_comments_1 = request.POST.get('summary_comments_1')
        cert.summary_result_2 = request.POST.get('summary_result_2')
        cert.summary_comments_2 = request.POST.get('summary_comments_2')
        cert.summary_result_3 = request.POST.get('summary_result_3')
        cert.summary_comments_3 = request.POST.get('summary_comments_3')

        cert._request_user = request.user  # this line use for history save
        cert._request = request
        cert._activity_message = f"Manually updated certificate {cert.cert_no}"
        cert.save()

        messages.success(request, "Certificate updated successfully.")
    return redirect('unpaid_certificates')


@login_required
def paid_certificates(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_certificates = 0
    total_paid_jeddah_certificates = total_paid_riyadh_certificates = total_paid_neom_certificates = total_paid_damman_certificates = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    certificate_list = Certificate.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        certificate_list = Certificate.objects.filter(isApprove=True, isCancel=False).exclude(amount=0).order_by('-cert_no')

        # Managers only see their own city's records
        if manager_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            certificate_list = certificate_list.filter(Q(cert_no__icontains=searching_query) | Q(company_name__icontains=searching_query))

        total_paid_certificates = certificate_list.count()

        # Paid Certificate
        total_paid_jeddah_certificates = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_riyadh_certificates = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_neom_certificates = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_damman_certificates = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).count()

        # Paid Amount
        total_paid_jeddah_amount = Certificate.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Certificate.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Certificate.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Certificate.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        certificate_list = Certificate.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

        if searching_query:
            certificate_list = certificate_list.filter(Q(cert_no__icontains=searching_query) | Q(company_name__icontains=searching_query))

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_paid_certificates': total_paid_certificates,
        'total_paid_jeddah_certificates': total_paid_jeddah_certificates,
        'total_paid_riyadh_certificates': total_paid_riyadh_certificates,
        'total_paid_neom_certificates': total_paid_neom_certificates,
        'total_paid_damman_certificates': total_paid_damman_certificates,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'paid_certificates',
    }
    return render(request, 'certificates/paid_certificates.html', context)


@login_required
def report_paid_certificates(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_certificates = 0
    total_paid_jeddah_certificates = total_paid_riyadh_certificates = total_paid_neom_certificates = total_paid_damman_certificates = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount= total_paid_amount = 0

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    certificate_list = Certificate.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        certificate_list = Certificate.objects.filter(isApprove=True, isCancel=False).exclude(amount=0).order_by('-cert_no')

        # Managers only see their own city's records
        if manager_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=manager_city)

        # Apply date range filter with timezone awareness
        if from_date and to_date:
            from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
            certificate_list = certificate_list.filter(created_at__range=[from_dt, to_dt])

        total_paid_certificates = certificate_list.count()

        # Base query for city statistics
        city_queryset = Certificate.objects.filter(isApprove=True, isCancel=False).exclude(amount=0)
        if manager_city:
            city_queryset = city_queryset.filter(user__profile__city__iexact=manager_city)
        
        # Apply date range to city statistics if dates are provided
        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                city_queryset = city_queryset.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass
        
        # Paid Certificate counts with date filtering
        total_paid_jeddah_certificates = city_queryset.filter(user__profile__city__iexact="Jeddah").count()
        total_paid_riyadh_certificates = city_queryset.filter(user__profile__city__iexact="Riyadh").count()
        total_paid_neom_certificates = city_queryset.filter(user__profile__city__iexact="NEOM").count()
        total_paid_damman_certificates = city_queryset.filter(user__profile__city__iexact="Damman").count()

        # Paid Amount with date filtering
        total_paid_jeddah_amount = city_queryset.filter(
            user__profile__city__iexact="Jeddah"
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_paid_riyadh_amount = city_queryset.filter(
            user__profile__city__iexact="Riyadh"
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_paid_neom_amount = city_queryset.filter(
            user__profile__city__iexact="NEOM"
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_paid_damman_amount = city_queryset.filter(
            user__profile__city__iexact="Damman"
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_paid_amount = total_paid_jeddah_amount + total_paid_riyadh_amount + total_paid_neom_amount + total_paid_damman_amount
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        certificate_list = Certificate.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-cert_no')

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_paid_certificates': total_paid_certificates,
        'total_paid_jeddah_certificates': total_paid_jeddah_certificates,
        'total_paid_riyadh_certificates': total_paid_riyadh_certificates,
        'total_paid_neom_certificates': total_paid_neom_certificates,
        'total_paid_damman_certificates': total_paid_damman_certificates,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'total_paid_amount': total_paid_amount,
        'from_date': from_date,
        'to_date': to_date,
        'manager_city': manager_city,
        'sidebar_active': 'report_paid_certificates',
    }
    return render(request, 'certificates/report_paid_certificates.html', context)


@login_required
def cancel_certificate(request, uid):
    try:
        if request.method == 'POST':
            certificate = get_object_or_404(Certificate, uid=uid)
            if not can_manage_record(request.user, certificate):
                messages.error(request, 'You do not have permission to cancel this certificate.')
                return redirect('manage_certificates')

            # Check if certificate is already cancelled
            if certificate.isCancel:
                messages.warning(request, f'Certificate {certificate.cert_no} is already cancelled.')
                return redirect('manage_certificates')
                
            # Update certificate status
            certificate.isCancel = True
            certificate.cancel_reason = request.POST.get('cancel_reason', 'No reason provided')
            
            # Add activity message
            certificate._request_user = request.user
            certificate._request = request
            certificate._activity_message = f"Cancelled certificate {certificate.cert_no} by {request.user.get_full_name() or request.user.username}"
            certificate.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(certificate).pk,
                object_id=certificate.pk,
                object_repr=force_str(certificate),
                action_flag=CHANGE,
                change_message=f"Cancelled certificate. Reason: {certificate.cancel_reason}"
            )
            
            messages.success(request, f'Certificate {certificate.cert_no} has been cancelled successfully.')
            return redirect('manage_certificates')
            
    except Exception as e:
        messages.error(request, f'Error cancelling certificate: {str(e)}')
        
    return redirect('manage_certificates')


@login_required
def activate_certificate(request, uid):
    try:
        if request.method == 'POST':
            certificate = get_object_or_404(Certificate, uid=uid)
            if not can_manage_record(request.user, certificate):
                messages.error(request, 'You do not have permission to activate this certificate.')
                return redirect('cancelled_certificates')

            # Check if the certificate is already active
            if certificate.isApprove and not certificate.isCancel:
                messages.warning(request, f'Certificate {certificate.cert_no} is already active.')
                return redirect('cancelled_certificates')
                
            # Update certificate status
            certificate.isCancel = False
            activate_notes = request.POST.get('activate_notes', '')
            
            # Add activity message
            certificate._request_user = request.user
            certificate._request = request
            certificate._activity_message = f"Activated certificate {certificate.cert_no} by {request.user.get_full_name() or request.user.username}"
            certificate.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(certificate).pk,
                object_id=certificate.pk,
                object_repr=force_str(certificate),
                action_flag=CHANGE,
                change_message=f"Activated certificate. Notes: {activate_notes}" if activate_notes else "Activated certificate"
            )
            
            messages.success(request, f'Certificate {certificate.cert_no} has been activated successfully.')
            return redirect('cancelled_certificates')
            
    except Exception as e:
        messages.error(request, f'Error activating certificate: {str(e)}')
        
    return redirect('cancelled_certificates')

@login_required
def cancelled_certificates(request):
    # Get the current logged-in user
    current_user = request.user
    total_certificates = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    certificate_list = Certificate.objects.none()  # Default to an empty queryset

    # Check if the user is a superuser (admin)
    if current_user.is_superuser:
        # Base query for admin users
        certificate_list = Certificate.objects.filter(isCancel=True).order_by('-cert_no')

        # Apply city filter if selected
        if selected_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            certificate_list = certificate_list.filter(
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_certificates = certificate_list.count()

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Cancel Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_certificates': total_certificates,
        'searching_query': searching_query,  # Include for pre-filling the input
        'sidebar_active': 'cancelled_certificates',
    }
    return render(request, 'certificates/cancelled_certificates.html', context)


@login_required
def hold_certificate(request, uid):
    try:
        if request.method == 'POST':
            certificate = get_object_or_404(Certificate, uid=uid)
            if not can_manage_record(request.user, certificate):
                messages.error(request, 'You do not have permission to hold this certificate.')
                return redirect('manage_certificates')

            if certificate.isHold:
                messages.warning(request, f'Certificate {certificate.cert_no} is already on hold.')
                return redirect('manage_certificates')
            

                
            certificate.isHold = True
            certificate.hold_reason = request.POST.get('hold_reason', 'No reason provided')
            certificate._request_user = request.user
            certificate._request = request
            certificate._activity_message = f"Certificate {certificate.cert_no} put on hold by {request.user.get_full_name() or request.user.username}"
            certificate.save()
            
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(certificate).pk,
                object_id=certificate.pk,
                object_repr=force_str(certificate),
                action_flag=CHANGE,
                change_message=f"Certificate put on hold. Reason: {certificate.hold_reason}"
            )
            
            messages.success(request, f'Certificate {certificate.cert_no} has been put on hold successfully.')
            return redirect('manage_certificates')
            
    except Exception as e:
        messages.error(request, f'Error cancelling certificate: {str(e)}')
        
    return redirect('manage_certificates')


@login_required
def unhold_certificate(request, uid):
    try:
        if request.method == 'POST':
            certificate = get_object_or_404(Certificate, uid=uid, isHold=True)
            if not can_manage_record(request.user, certificate):
                messages.error(request, 'You do not have permission to release this certificate from hold.')
                return redirect('holded_certificates')

            # Check if the certificate is already unhold
            if not certificate.isHold:
                messages.warning(request, f'Certificate {certificate.cert_no} is already unhold.')
                return redirect('holded_certificates')
            
            activate_notes = request.POST.get('activate_notes', '')
            certificate.isHold = False
            certificate._request_user = request.user
            certificate._request = request
            certificate._activity_message = f"Certificate {certificate.cert_no} released from hold by {request.user.get_full_name() or request.user.username}"
            certificate.save()
            
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(certificate).pk,
                object_id=certificate.pk,
                object_repr=force_str(certificate),
                action_flag=CHANGE,
                change_message=f"Certificate released from hold. Notes: {activate_notes}" if activate_notes else "Certificate released from hold"
            )
            
            messages.success(request, f'Certificate {certificate.cert_no} has been released from hold successfully.')
            return redirect('holded_certificates')
            
    except Exception as e:
        messages.error(request, f'Error activating certificate: {str(e)}')
        
    return redirect('holded_certificates')


@login_required
def holded_certificates(request):
    # Get the current logged-in user
    current_user = request.user
    total_certificates = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    certificate_list = Certificate.objects.none()  # Default to an empty queryset

    # Check if the user is a superuser (admin)
    if current_user.is_superuser:
        # Base query for admin users
        certificate_list = Certificate.objects.filter(isHold=True).order_by('-cert_no')

        # Apply city filter if selected
        if selected_city:
            certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            certificate_list = certificate_list.filter(
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_certificates = certificate_list.count()

    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Holded Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_certificates': total_certificates,
        'searching_query': searching_query,  # Include for pre-filling the input
        'sidebar_active': 'holded_certificates',
    }
    return render(request, 'certificates/holded_certificates.html', context)


@login_required
def rejected_certificates(request):
    """
    Rejected certificates — previously invisible everywhere once
    isReject=True: excluded from Pending on purpose, and not shown by
    Manage (isApprove required), Cancelled (isCancel) or Hold (isHold).
    This is the only place they can be found and restored.
    """
    current_user = request.user
    if not (current_user.is_superuser or current_user.is_staff):
        messages.error(request, 'You do not have permission to view rejected certificates.')
        return redirect('index')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()

    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    certificate_list = Certificate.objects.filter(isReject=True).order_by('-updated_at')
    if selected_city:
        certificate_list = certificate_list.filter(user__profile__city__iexact=selected_city)
    if searching_query:
        certificate_list = certificate_list.filter(
            Q(cert_no__icontains=searching_query) |
            Q(company_name__icontains=searching_query)
        )

    total_certificates = certificate_list.count()
    paginator = Paginator(certificate_list, items_per_page)
    page = request.GET.get('page', '1')
    try:
        certificates = paginator.page(int(page))
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'title': 'Rejected Certificates',
        'certificates': certificates,
        'current_date': current_date,
        'total_certificates': total_certificates,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'rejected_certificates',
    }
    return render(request, 'certificates/rejected_certificates.html', context)


@login_required
@require_POST
def restore_rejected_certificate(request, uid):
    """Move a rejected certificate back to Pending."""
    cert = get_object_or_404(Certificate, uid=uid)
    if not can_manage_record(request.user, cert):
        messages.error(request, 'You do not have permission to restore this certificate.')
        return redirect_back(request, 'rejected_certificates')

    if not cert.isReject:
        messages.warning(request, f'Certificate {cert.cert_no} is not rejected.')
        return redirect_back(request, 'rejected_certificates')

    cert.isReject = False
    cert._request_user = request.user
    cert._request = request
    approver = request.user.get_full_name() or request.user.username
    cert._activity_message = f"Restored rejected certificate {cert.cert_no} to pending by {approver}"
    cert.save()

    messages.success(request, f'Certificate {cert.cert_no} has been restored to Pending.')
    return redirect_back(request, 'rejected_certificates')


@login_required
@require_POST
def delete_rejected_certificate(request, uid):
    """Permanently delete a rejected certificate after confirmation."""
    cert = get_object_or_404(Certificate, uid=uid)
    if not can_manage_record(request.user, cert):
        messages.error(request, 'You do not have permission to delete this certificate.')
        return redirect_back(request, 'rejected_certificates')

    if not cert.isReject:
        messages.warning(request, f'Certificate {cert.cert_no} is not rejected.')
        return redirect_back(request, 'rejected_certificates')

    cert_no = cert.cert_no
    log_activity(
        user=request.user,
        action=f"Permanently deleted rejected certificate {cert_no} by {request.user.get_full_name() or request.user.username}",
        request=request,
    )
    cert.delete()

    messages.success(request, f'Certificate {cert_no} has been permanently deleted.')
    return redirect_back(request, 'rejected_certificates')


@login_required
@require_POST
def update_certificate_field(request, uid):
    """Inline Total/Paid Amount edit from the Paid & Unpaid tables."""
    return handle_amount_field_update(request, Certificate, uid)

from decimal import Decimal
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.timezone import now  # Make sure this import is present
from base.utils import items_per_page, current_date, get_next_numeric_sr_no, get_manager_city
from training.models import Training
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse


@login_required
def manage_training(request):
    # Get the current logged-in user
    current_user = request.user
    total_trainings = 0
    total_jeddah_trainings = pending_jeddah_trainings = verified_jeddah_trainings = 0
    total_riyadh_trainings = pending_riyadh_trainings = verified_riyadh_trainings = 0
    total_neom_trainings = pending_neom_trainings = verified_neom_trainings = 0
    total_damman_trainings = pending_damman_trainings = verified_damman_trainings = 0
    total_paid_jeddah_trainings = total_paid_riyadh_trainings = total_paid_neom_trainings = total_paid_damman_trainings = 0
    total_unpaid_jeddah_trainings = total_unpaid_riyadh_trainings = total_unpaid_neom_trainings = total_unpaid_damman_trainings = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    unique_trades = Training.objects.exclude(
        trade__isnull=True
    ).exclude(
        trade__exact=''
    ).values_list(
        'trade', flat=True
    ).distinct().order_by('trade')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_trade = request.GET.get('trade', '').strip()
    training_list = Training.objects.none()  # Default to an empty queryset

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        training_list = Training.objects.filter(isApprove=True, isCancel=False).order_by('-card_no')
        # Apply city filter if selected
        if selected_city:
            training_list = training_list.filter(user__profile__city__iexact=selected_city)

        # Apply trade filter if selected
        if selected_trade:
            training_list = training_list.filter(trade__iexact=selected_trade)

        # Apply search query if provided
        if searching_query:
            training_list = training_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_trainings = len(training_list)

        total_jeddah_trainings = Training.objects.filter(user__profile__city__iexact="Jeddah").count()
        pending_jeddah_trainings = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=False, isCancel=False).count()
        verified_jeddah_trainings = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).count()

        total_riyadh_trainings = Training.objects.filter(user__profile__city__iexact="Riyadh").count()
        pending_riyadh_trainings = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=False, isCancel=False).count()
        verified_riyadh_trainings = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).count()

        total_neom_trainings = Training.objects.filter(user__profile__city__iexact="NEOM").count()
        pending_neom_trainings = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=False, isCancel=False).count()
        verified_neom_trainings = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).count()

        total_damman_trainings = Training.objects.filter(user__profile__city__iexact="Damman").count()
        pending_damman_trainings = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=False, isCancel=False).count()
        verified_damman_trainings = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).count()

        # Paid Training
        total_paid_jeddah_trainings = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_riyadh_trainings = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_neom_trainings = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_damman_trainings = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).count()

        # Unpaid Training
        total_unpaid_jeddah_trainings = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_trainings = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_trainings = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_trainings = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()

        # Paid Amount
        total_paid_jeddah_amount = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        training_list = Training.objects.filter(user=current_user, isApprove=False, isCancel=False, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

        if searching_query:
            training_list = training_list.filter(Q(card_no__icontains=searching_query) | Q(cert_no__icontains=searching_query))

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Manage Training',
        'trainings': trainings,
        'current_date': current_date,
        'total_trainings': total_trainings,
        'total_jeddah_trainings': total_jeddah_trainings,
        'pending_jeddah_trainings': pending_jeddah_trainings,
        'verified_jeddah_trainings': verified_jeddah_trainings,
        'total_riyadh_trainings': total_riyadh_trainings,
        'pending_riyadh_trainings': pending_riyadh_trainings,
        'verified_riyadh_trainings': verified_riyadh_trainings,
        'total_neom_trainings': total_neom_trainings,
        'pending_neom_trainings': pending_neom_trainings,
        'verified_neom_trainings': verified_neom_trainings,
        'total_damman_trainings': total_damman_trainings,
        'pending_damman_trainings': pending_damman_trainings,
        'verified_damman_trainings': verified_damman_trainings,
        'total_paid_jeddah_trainings': total_paid_jeddah_trainings,
        'total_paid_riyadh_trainings': total_paid_riyadh_trainings,
        'total_paid_neom_trainings': total_paid_neom_trainings,
        'total_paid_damman_trainings': total_paid_damman_trainings,
        'total_unpaid_jeddah_trainings': total_unpaid_jeddah_trainings,
        'total_unpaid_riyadh_trainings': total_unpaid_riyadh_trainings,
        'total_unpaid_neom_trainings': total_unpaid_neom_trainings,
        'total_unpaid_damman_trainings': total_unpaid_damman_trainings,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,  # Include for pre-filling the input
        'unique_trades': unique_trades,
        'manager_city': manager_city,
        'sidebar_active': 'manage_training',
    }
    return render(request, 'training/manage_training.html', context)


@login_required
def report_training(request):
    current_user = request.user
    total_training = 0

    # Get filter parameters
    # Keep original date strings for the template
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    trade = request.GET.get('trade', '').strip()

    training_list = Training.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # For admin users (superuser or manager)
    if current_user.is_superuser or current_user.is_staff:
        training_list = Training.objects.all().order_by('-card_no')

        # Apply status filter
        if status == 'True':
            training_list = training_list.filter(isApprove=True, isCancel=False)
        elif status == 'False':
            training_list = training_list.filter(isApprove=False, isCancel=False)

        # Apply date range filter with timezone awareness
        if from_date and to_date:
            from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
            training_list = training_list.filter(created_at__range=[from_dt, to_dt])

        # Apply city filter
        if selected_city:
            training_list = training_list.filter(user__profile__city__iexact=selected_city)
            
        # Apply company name filter
        if company_name:
            training_list = training_list.filter(company_name__icontains=company_name)
            
        # Apply trade filter
        if trade:
            training_list = training_list.filter(trade__icontains=trade)

    # For regular users
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        training_list = Training.objects.filter(
            user=current_user,
            isApprove=False, isCancel=False,
            created_at__gte=twenty_four_hours_ago
        ).order_by('-card_no')

    # Pagination
    paginator = Paginator(training_list, 50)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        trainings = paginator.page(1)

    context = {
        'title': 'Report Trainings',
        'trainings': trainings,
        'current_date': timezone.now().date(),
        'total_trainings': training_list.count(),
        'from_date': from_date,
        'to_date': to_date,
        'selected_city': selected_city,
        'selected_status': status,
        'company_name': company_name,
        'trade': trade,
        'manager_city': manager_city,
        'sidebar_active': 'report_training',
    }
    return render(request, 'training/report_training.html', context)


@login_required
def export_training_csv(request):
    # Get filter parameters from the request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    trade = request.GET.get('trade', '').strip()

    # Start with base queryset
    training_list = Training.objects.all()

    # Apply filters
    if status == 'True':
        training_list = training_list.filter(isApprove=True, isCancel=False)
    elif status == 'False':
        training_list = training_list.filter(isApprove=False, isCancel=False)

    if from_date and to_date:
        from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
        to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
        training_list = training_list.filter(created_at__range=[from_dt, to_dt])

    if selected_city:
        training_list = training_list.filter(user__profile__city__iexact=selected_city)
        
    # Apply company name filter
    if company_name:
        training_list = training_list.filter(company_name__icontains=company_name)
        
    # Apply trade filter
    if trade:
        training_list = training_list.filter(trade__icontains=trade)

    # Create the HttpResponse object with the appropriate Excel header
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="trainings_export.xlsx"'

    # Create a new Excel workbook and add a worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Trainings"

    # Define headers based on the template
    headers = [
        'S.No', 'Name', 'City', 'Card No', 'Certificate No', 'Name of Trainee',
        'Company Name', 'Iqama No', 'Issue Date', 'Expiry Date', 'Remaining Months',
        'Trade', 'Hologram No', 'Assessed By Resource Person', 'Status', 'Note',
        'Wasted Serial', 'Requested By', 'Prepared By', 'Invoice No', 'Invoice Date',
        'Total Amount', 'Paid Amount', 'Cash/Bank', 'Client Representative Name',
        'Client Representative Number', 'Email', 'Remarks'
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
            if isinstance(date_value, str):
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S'):
                    try:
                        dt = datetime.strptime(str(date_value).split(' ')[0], fmt)
                        return dt.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        continue
            return str(date_value).split(' ')[0]
        except Exception:
            return str(date_value) if date_value else ''

    # Write data rows
    for row_num, training in enumerate(training_list, 2):  # Start from row 2 (after header)
        user = getattr(training, 'user', None)
        row_data = [
            row_num - 1,  # S.No
            f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip() or 'N/A',
            getattr(training.user.profile, 'city', '') if hasattr(training.user, 'profile') else '',
            getattr(training, 'card_no', '') or '',
            getattr(training, 'cert_no', '') or '',
            getattr(training, 'name_of_trainee', '') or '',
            getattr(training, 'company_name', '') or '',
            getattr(training, 'iqama_no', '') or '',
            format_date(getattr(training, 'issue_date', None)),
            format_date(getattr(training, 'expiry_date', None)),
            getattr(training, 'remaining_months', '') or '',
            getattr(training, 'trade', '') or '',
            getattr(training, 'holo_gram_no', '') or '',
            getattr(training, 'assessed_by_resource_person', '') or '',
            'Approved' if getattr(training, 'isApprove', False) else 'Pending',
            getattr(training, 'note', '') or '',
            getattr(training, 'wasted_serial', '') or '',
            getattr(training, 'requested_by', '') or '',
            getattr(training, 'prepared_by', '') or '',
            getattr(training, 'invoice_no', '') or '',
            format_date(getattr(training, 'invoice_date', None)),
            float(getattr(training, 'total_amount', 0) or 0),
            float(getattr(training, 'amount', 0) or 0),
            getattr(training, 'cash_bank', '') or '',
            getattr(training, 'client_rep_name', '') or '',
            getattr(training, 'client_rep_number', '') or '',
            getattr(training, 'email', '') or '',
            getattr(training, 'remarks', '') or ''
        ]

        # Write each cell in the row
        for col_num, cell_value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num, value=cell_value)

    # Auto-size columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        ws.column_dimensions[column].width = min(adjusted_width, 30)

    # Save the workbook to the response
    output = BytesIO()
    wb.save(output)
    response.write(output.getvalue())
    output.close()
    return response


from django.db import IntegrityError
@login_required
@require_http_methods(["GET", "POST"])
def add_training_manual(request):
    if request.method == 'GET':
        messages.warning(request, "This form must be submitted through the Manage Cards page.")
        return redirect('manage_training')

    if request.method == 'POST':
        try:
            cert_no = request.POST.get('cert_no') or None
            card_no = request.POST.get('card_no') or None

            # Ensure at least one of the two is present
            if not cert_no and not card_no:
                messages.error(request, "Either Certificate No or Card No must be provided.")
                return redirect('manage_training')

            # Check uniqueness if provided
            if cert_no and Training.objects.filter(cert_no=cert_no).exists():
                messages.warning(request, f"Training with Certificate No '{cert_no}' already exists.")
                return redirect('manage_training')

            if card_no and Training.objects.filter(card_no=card_no).exists():
                messages.warning(request, f"Training with Card No '{card_no}' already exists.")
                return redirect('manage_training')

            # Validate amount logic
            amount = Decimal(request.POST.get('amount') or '0')
            total_amount = Decimal(request.POST.get('total_amount') or '0')

            if amount > total_amount:
                messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                return redirect('manage_training')

            # Parse dates
            inspection_date_str = request.POST.get('issue_date')
            expiry_date_str = request.POST.get('expiry_date')
            inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date() if inspection_date_str else None
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

            remaining_months = None
            if inspection_date and expiry_date:
                delta = relativedelta(expiry_date, inspection_date)
                remaining_months = delta.years * 12 + delta.months

            # Create and save training record
            training = Training(
                user=request.user,
                sr_no=get_next_numeric_sr_no(),
                card_no=card_no,
                cert_no=cert_no,
                name_of_trainee=request.POST.get('name_of_trainee'),
                company_name=request.POST.get('company_name'),
                iqama_no=request.POST.get('iqama_no'),
                issue_date=inspection_date,
                expiry_date=expiry_date,
                remaining_months=remaining_months,
                trade=request.POST.get('trade'),
                holo_gram_no=request.POST.get('holo_gram_no'),
                assessed_by_resource_person=request.POST.get('assessed_by_resource_person'),
                wasted_serial=request.POST.get('wasted_serial'),
                requested_by=request.POST.get('requested_by'),
                prepared_by=request.POST.get('prepared_by'),
                invoice_no=request.POST.get('invoice_no'),
                invoice_date=datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date()
                if request.POST.get('invoice_date') else now().date(),
                total_amount=total_amount,
                amount=amount,
                cash_bank=request.POST.get('cash_bank'),
                client_rep_name=request.POST.get('client_rep_name'),
                client_rep_number=request.POST.get('client_rep_number'),
                email=request.POST.get('email'),
                remarks=request.POST.get('remarks'),
            )

            training._request_user = request.user
            training._request = request
            training._activity_message = f"Created Training card {training.card_no}"
            try:
                training.save()
                messages.success(request, "Training added successfully.")
            except IntegrityError:
                messages.warning(request, "This training number was just added by another user. Please try again with a different training number.")
                return redirect('manage_training')

        except Exception as e:
            messages.error(request, f"Error adding training: {str(e)}")
            return redirect('manage_training')

    return redirect('manage_training')


@login_required
def update_training(request, uid):
    training = get_object_or_404(Training, uid=uid)

    if request.method == 'POST':
        cert_no = request.POST.get('cert_no') or None
        card_no = request.POST.get('card_no') or None

        # Ensure at least one of the two is present
        if not cert_no and not card_no:
            messages.error(request, "Either Certificate No or Card No must be provided.")
            return redirect('manage_training')

        # Check uniqueness (excluding current record)
        if cert_no and Training.objects.exclude(uid=uid).filter(cert_no=cert_no).exists():
            messages.warning(request, f"Another record with Certificate No '{cert_no}' already exists.")
            return redirect('manage_training')

        if card_no and Training.objects.exclude(uid=uid).filter(card_no=card_no).exists():
            messages.warning(request, f"Another record with Card No '{card_no}' already exists.")
            return redirect('manage_training')

        # Validate amount
        amount = Decimal(request.POST.get('amount') or '0')
        total_amount = Decimal(request.POST.get('total_amount') or '0')
        if amount > total_amount:
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('manage_training')

        # Parse date fields
        inspection_date_str = request.POST.get('issue_date')
        expiry_date_str = request.POST.get('expiry_date')
        inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date() if inspection_date_str else None
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

        # Remaining months
        remaining_months = None
        if inspection_date and expiry_date:
            delta = relativedelta(expiry_date, inspection_date)
            remaining_months = delta.years * 12 + delta.months

        # Update fields
        training.sr_no = request.POST.get('sr_no')
        training.card_no = card_no
        training.cert_no = cert_no
        training.name_of_trainee = request.POST.get('name_of_trainee')
        training.company_name = request.POST.get('company_name')
        training.iqama_no = request.POST.get('iqama_no')
        training.issue_date = inspection_date
        training.expiry_date = expiry_date
        training.remaining_months = remaining_months
        training.trade = request.POST.get('trade')
        training.holo_gram_no = request.POST.get('holo_gram_no')
        training.assessed_by_resource_person = request.POST.get('assessed_by_resource_person')
        training.wasted_serial = request.POST.get('wasted_serial')
        training.requested_by = request.POST.get('requested_by')
        training.prepared_by = request.POST.get('prepared_by')
        training.invoice_no = request.POST.get('invoice_no')
        training.invoice_date = datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date() if request.POST.get('invoice_date') else now().date()
        training.total_amount = total_amount
        training.amount = amount
        training.cash_bank = request.POST.get('cash_bank')
        training.client_rep_name = request.POST.get('client_rep_name')
        training.client_rep_number = request.POST.get('client_rep_number')
        training.email = request.POST.get('email')
        training.remarks = request.POST.get('remarks')

        training._request_user = request.user
        training._request = request
        training._activity_message = f"Updated Training card {training.card_no}"
        training.save()

        messages.success(request, "Training updated successfully.")

    return redirect('manage_training')


@login_required
def pending_training(request):
    # Get the current logged-in user
    current_user = request.user

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    training_list = Training.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        training_list = Training.objects.filter(isApprove=False, isCancel=False, isReject=False).order_by('-card_no')
        # Apply city filter if selected
        if selected_city:
            training_list = training_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            training_list = training_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        training_list = Training.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago, isApprove=False, isCancel=False, isReject=False).order_by('-card_no')
        if searching_query:
            training_list = training_list.filter(Q(card_no__icontains=searching_query) | Q(cert_no__icontains=searching_query))

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Pending Training',
        'trainings': trainings,
        'current_date': current_date,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'pending_training',
    }
    return render(request, 'training/pending_training.html', context)


@login_required
def approve_reject_training(request, uid):
    training = get_object_or_404(Training, uid=uid)

    if request.method == 'POST':
        # Check which button was clicked
        action = request.POST.get('action')
        if action == 'approve':
            training.isApprove = True
            training.isReject = False
            messages.success(request, 'Training approved and updated successfully.')
        elif action == 'reject':
            training.isApprove = False
            training.isReject = True
            messages.warning(request, 'Training rejected and updated successfully.')

        approver = request.user.get_full_name() or request.user.username
        owner = training.user.get_full_name() or training.user.username
        verdict = 'Approved' if training.isApprove else 'Rejected'
        training._request_user = request.user
        training._request = request
        training._activity_message = f"{verdict} training card {training.card_no} (owner: {owner}) by {approver}"
        training.save()
    return redirect('pending_training')


@login_required
def export_training_data_excel(request, model_name, city):
    if model_name != "training":
        return HttpResponse("Invalid category", status=400)

    queryset = Training.objects.filter(user__profile__city__iexact=city)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{model_name.title()} - {city.title()}"

    # Define full headers
    headers = [
        "S.No", "Card No", "Certificate No", "Name of Trainee", "Company Name", "Iqama No",
        "Issue Date", "Expiry Date", "Remaining Months", "Trade", "Hologram No",
        "Assessed By Resource Person", "Status", "Note", "Wasted Serial", "Requested By",
        "Prepared By", "Invoice No", "Amount", "Cash/Bank", "Client Representative Name",
        "Client Representative Number", "Email", "Remarks"
    ]
    ws.append(headers)

    # Style header row
    header_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")  # Dark gray
    header_font = Font(color="FFFFFF", bold=True)  # White bold font
    for col_num, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Add rows
    for idx, obj in enumerate(queryset, start=1):
        ws.append([
            idx,
            obj.card_no,
            obj.cert_no,
            obj.name_of_trainee,
            obj.company_name,
            obj.iqama_no,
            obj.issue_date,
            obj.expiry_date,
            obj.remaining_months,
            obj.trade,
            obj.holo_gram_no,
            obj.assessed_by_resource_person,
            obj.status,
            obj.note,
            obj.wasted_serial,
            obj.requested_by,
            obj.prepared_by,
            obj.invoice_no,
            obj.amount,
            obj.cash_bank,
            obj.client_rep_name,
            obj.client_rep_number,
            obj.email,
            obj.remarks,
        ])

    # Return response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{model_name}_{city}_export.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@login_required
def unpaid_training(request):
    # Get the current logged-in user
    current_user = request.user
    total_unpaid_training = 0
    total_unpaid_jeddah_training = total_unpaid_riyadh_training = total_unpaid_neom_training = total_unpaid_damman_training = 0

    searching_query = request.GET.get('searching_query', '').strip()
    training_list = Training.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        training_list = Training.objects.filter(isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).order_by('-card_no')

        # Managers only see their own city's records
        if manager_city:
            training_list = training_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            training_list = training_list.filter(Q(card_no__icontains=searching_query) | Q(cert_no__icontains=searching_query))

        total_unpaid_training = training_list.count()

        # Unpaid Training
        total_unpaid_jeddah_training = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_training = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_training = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_training = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        training_list = Training.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

        if searching_query:
            training_list = training_list.filter(Q(card_no__icontains=searching_query) | Q(cert_no__icontains=searching_query))

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Unpaid Trainings',
        'trainings': trainings,
        'current_date': current_date,
        'total_unpaid_training': total_unpaid_training,
        'total_unpaid_jeddah_training': total_unpaid_jeddah_training,
        'total_unpaid_riyadh_training': total_unpaid_riyadh_training,
        'total_unpaid_neom_training': total_unpaid_neom_training,
        'total_unpaid_damman_training': total_unpaid_damman_training,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'unpaid_training',
    }
    return render(request, 'training/unpaid_training.html', context)


@login_required
def update_unpaid_training(request, uid):
    training = get_object_or_404(Training, uid=uid)

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('unpaid_training')
        training.sr_no = request.POST.get('sr_no')
        training.card_no = request.POST.get('card_no')
        training.cert_no = request.POST.get('cert_no')
        training.name_of_trainee = request.POST.get('name_of_trainee')
        training.company_name = request.POST.get('company_name')
        training.iqama_no = request.POST.get('iqama_no')
        training.issue_date = request.POST.get('issue_date')
        training.expiry_date = request.POST.get('expiry_date')
        training.remaining_months = request.POST.get('remaining_months')
        training.trade = request.POST.get('trade')
        training.holo_gram_no = request.POST.get('holo_gram_no')
        training.assessed_by_resource_person = request.POST.get('assessed_by_resource_person')
        training.wasted_serial = request.POST.get('wasted_serial')
        training.requested_by = request.POST.get('requested_by')
        training.prepared_by = request.POST.get('prepared_by')
        training.invoice_no = request.POST.get('invoice_no')
        training.amount = request.POST.get('amount')
        training.cash_bank = request.POST.get('cash_bank')
        training.client_rep_name = request.POST.get('client_rep_name')
        training.client_rep_number = request.POST.get('client_rep_number')
        training.email = request.POST.get('email')
        training.remarks = request.POST.get('remarks')

        training._request_user = request.user
        training._request = request
        training._activity_message = f"Updated Training card {training.card_no}"
        training.save()

        messages.success(request, "Training updated successfully.")
    return redirect('unpaid_training')


@login_required
def paid_training(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_training = 0
    total_paid_jeddah_training = total_paid_riyadh_training = total_paid_neom_training = total_paid_damman_training = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()

    training_list = Training.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        training_list = Training.objects.filter(isApprove=True, isCancel=False).exclude(amount=0).order_by('-card_no')

        # Managers only see their own city's records
        if manager_city:
            training_list = training_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            training_list = training_list.filter(Q(card_no__icontains=searching_query) | Q(cert_no__icontains=searching_query))

        total_paid_training = training_list.count()

        # Paid Training
        total_paid_jeddah_training = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_riyadh_training = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_neom_training = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).count()
        total_paid_damman_training = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).count()

        # Paid Amount
        total_paid_jeddah_amount = Training.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Training.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Training.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Training.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        training_list = Training.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

        if searching_query:
            training_list = training_list.filter(Q(card_no__icontains=searching_query) | Q(cert_no__icontains=searching_query))

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Trainings',
        'trainings': trainings,
        'current_date': current_date,
        'total_paid_training': total_paid_training,
        'total_paid_jeddah_training': total_paid_jeddah_training,
        'total_paid_riyadh_training': total_paid_riyadh_training,
        'total_paid_neom_training': total_paid_neom_training,
        'total_paid_damman_training': total_paid_damman_training,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'paid_training',
    }
    return render(request, 'training/paid_training.html', context)



@login_required
def report_paid_training(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_training = 0
    total_paid_jeddah_training = total_paid_riyadh_training = total_paid_neom_training = total_paid_damman_training = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = total_paid_amount = 0

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    training_list = Training.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        training_list = Training.objects.filter(isApprove=True, isCancel=False).exclude(amount=0).order_by('-card_no')

        # Managers only see their own city's records
        if manager_city:
            training_list = training_list.filter(user__profile__city__iexact=manager_city)

        # Apply date range filter with timezone awareness
        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                training_list = training_list.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass

        total_paid_training = training_list.count()

        # Base query for city statistics
        city_queryset = Training.objects.filter(isApprove=True, isCancel=False).exclude(amount=0)
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

        # Paid Training counts with date filtering
        total_paid_jeddah_training = city_queryset.filter(
            user__profile__city__iexact="Jeddah"
        ).count()
        total_paid_riyadh_training = city_queryset.filter(
            user__profile__city__iexact="Riyadh"
        ).count()
        total_paid_neom_training = city_queryset.filter(
            user__profile__city__iexact="NEOM"
        ).count()
        total_paid_damman_training = city_queryset.filter(
            user__profile__city__iexact="Damman"
        ).count()

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

        total_paid_amount = (total_paid_jeddah_amount + total_paid_riyadh_amount + 
                           total_paid_neom_amount + total_paid_damman_amount)
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        training_list = Training.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Trainings',
        'trainings': trainings,
        'current_date': current_date,
        'total_paid_training': total_paid_training,
        'total_paid_jeddah_training': total_paid_jeddah_training,
        'total_paid_riyadh_training': total_paid_riyadh_training,
        'total_paid_neom_training': total_paid_neom_training,
        'total_paid_damman_training': total_paid_damman_training,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'total_paid_amount': total_paid_amount,
        'from_date': from_date,
        'to_date': to_date,
        'manager_city': manager_city,
        'sidebar_active': 'report_paid_training',
    }
    return render(request, 'training/report_paid_training.html', context)


@login_required
def cancel_training(request, uid):
    try:
        if request.method == 'POST':
            training = get_object_or_404(Training, uid=uid)
            
            # Check if training is already cancelled
            if training.isCancel:
                messages.warning(request, f'Training {training.card_no} is already cancelled.')
                return redirect('manage_training')
                
            # Update training status
            training.isCancel = True
            training.cancel_reason = request.POST.get('cancel_reason', 'No reason provided')
            
            training._request_user = request.user
            training._request = request
            training._activity_message = f"Cancelled training {training.card_no} by {request.user.get_full_name() or request.user.username}"
            training.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(training).pk,
                object_id=training.pk,
                object_repr=force_str(training),
                action_flag=CHANGE,
                change_message=f"Cancelled training. Reason: {training.cancel_reason}"
            )
            
            messages.success(request, f'Training {training.card_no} has been cancelled successfully.')
            return redirect('manage_training')
            
    except Exception as e:
        messages.error(request, f'Error cancelling training: {str(e)}')
        
    return redirect('manage_training')


@login_required
def activate_training(request, uid):
    try:
        if request.method == 'POST':
            training = get_object_or_404(Training, uid=uid)
            
            # Check if training is already active
            if training.isApprove and not training.isCancel:
                messages.warning(request, f'Training {training.card_no} is already active.')
                return redirect('cancelled_training')
                
            # Update training status
            training.isCancel = False
            activate_notes = request.POST.get('activate_notes', '')
            
            training._request_user = request.user
            training._request = request
            training._activity_message = f"Activated training {training.card_no} by {request.user.get_full_name() or request.user.username}"
            training.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(training).pk,
                object_id=training.pk,
                object_repr=force_str(training),
                action_flag=CHANGE,
                change_message=f"Activated training. Notes: {activate_notes}" if activate_notes else "Activated training"
            )
            
            messages.success(request, f'Training {training.card_no} has been activated successfully.')
            return redirect('cancelled_training')
            
    except Exception as e:
        messages.error(request, f'Error activating training: {str(e)}')
        
    return redirect('cancelled_training')

@login_required
def cancelled_training(request):
    # Get the current logged-in user
    current_user = request.user
    total_trainings = 0

    unique_trades = Training.objects.exclude(
        trade__isnull=True
    ).exclude(
        trade__exact=''
    ).values_list(
        'trade', flat=True
    ).distinct().order_by('trade')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_trade = request.GET.get('trade', '').strip()

    training_list = Training.objects.none()  # Default to an empty queryset

    # Check if the user is a superuser (admin)
    if current_user.is_superuser:
        # Base query for admin users
        training_list = Training.objects.filter(isApprove=False, isCancel=True).order_by('-card_no')

        # Apply city filter if selected
        if selected_city:
            training_list = training_list.filter(user__profile__city__iexact=selected_city)

        # Apply trade filter if selected
        if selected_trade:
            training_list = training_list.filter(trade__iexact=selected_trade)

        # Apply search query if provided
        if searching_query:
            training_list = training_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_trainings = training_list.count()

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Cancel Trainings',
        'trainings': trainings,
        'current_date': current_date,
        'total_trainings': total_trainings,
        'searching_query': searching_query,  # Include for pre-filling the input
        'unique_trades': unique_trades,
        'sidebar_active': 'cancelled_training',
    }
    return render(request, 'training/cancelled_training.html', context)


@login_required
def hold_training(request, uid):
    try:
        if request.method == 'POST':
            training = get_object_or_404(Training, uid=uid)
            
            if training.isHold:
                messages.warning(request, f'Training {training.card_no} is already on hold.')
                return redirect('manage_training')
                
            if training.isCancel:
                messages.warning(request, f'Cannot put a cancelled training on hold.')
                return redirect('manage_training')
                
            training.isHold = True
            training.hold_reason = request.POST.get('hold_reason', 'No reason provided')
            training._request_user = request.user
            training._request = request
            training._activity_message = f"Training {training.card_no} put on hold by {request.user.get_full_name() or request.user.username}"
            training.save()
            
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(training).pk,
                object_id=training.pk,
                object_repr=force_str(training),
                action_flag=CHANGE,
                change_message=f"Training put on hold. Reason: {training.hold_reason}"
            )
            
            messages.success(request, f'Training {training.card_no} has been put on hold successfully.')
            return redirect('manage_training')
            
    except Exception as e:
        messages.error(request, f'Error cancelling training: {str(e)}')
        
    return redirect('manage_training')


@login_required
def unhold_training(request, uid):
    try:
        if request.method == 'POST':
            training = get_object_or_404(Training, uid=uid, isHold=True)
            
            activate_notes = request.POST.get('activate_notes', '')
            training.isHold = False
            training._request_user = request.user
            training._request = request
            training._activity_message = f"Training {training.card_no} released from hold by {request.user.get_full_name() or request.user.username}"
            training.save()
            
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(training).pk,
                object_id=training.pk,
                object_repr=force_str(training),
                action_flag=CHANGE,
                change_message=f"Training released from hold. Notes: {activate_notes}" if activate_notes else "Training released from hold"
            )
            
            messages.success(request, f'Training {training.card_no} has been released from hold successfully.')
            return redirect('holded_training')
            
    except Exception as e:
        messages.error(request, f'Error activating training: {str(e)}')
        
    return redirect('holded_training')

@login_required
def holded_training(request):
    # Get the current logged-in user
    current_user = request.user
    total_trainings = 0

    unique_trades = Training.objects.exclude(
        trade__isnull=True
    ).exclude(
        trade__exact=''
    ).values_list(
        'trade', flat=True
    ).distinct().order_by('trade')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_trade = request.GET.get('trade', '').strip()

    training_list = Training.objects.none()  # Default to an empty queryset

    # Check if the user is a superuser (admin)
    if current_user.is_superuser:
        # Base query for admin users
        training_list = Training.objects.filter(isHold=True).order_by('-card_no')

        # Apply city filter if selected
        if selected_city:
            training_list = training_list.filter(user__profile__city__iexact=selected_city)

        # Apply trade filter if selected
        if selected_trade:
            training_list = training_list.filter(trade__iexact=selected_trade)

        # Apply search query if provided
        if searching_query:
            training_list = training_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(cert_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_trainings = training_list.count()

    paginator = Paginator(training_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        trainings = paginator.page(int(page))
    except PageNotAnInteger:
        trainings = paginator.page(1)
    except EmptyPage:
        trainings = paginator.page(paginator.num_pages)

    context = {
        'title': 'Holded Trainings',
        'trainings': trainings,
        'current_date': current_date,
        'total_trainings': total_trainings,
        'searching_query': searching_query,  # Include for pre-filling the input
        'unique_trades': unique_trades,
        'sidebar_active': 'holded_training',
    }
    return render(request, 'training/holded_training.html', context)
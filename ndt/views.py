from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.timezone import now  # Make sure this import is present
from base.utils import items_per_page, current_date, get_next_numeric_sr_no, get_manager_city
from ndt.models import NonDestructiveTesting
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse


@login_required
def manage_ndt(request):
    # Get the current logged-in user
    current_user = request.user
    total_ndts = 0
    total_jeddah_ndts = pending_jeddah_ndts = verified_jeddah_ndts = 0
    total_riyadh_ndts = pending_riyadh_ndts = verified_riyadh_ndts = 0
    total_neom_ndts = pending_neom_ndts = verified_neom_ndts = 0
    total_damman_ndts = pending_damman_ndts = verified_damman_ndts = 0
    total_paid_jeddah_ndts = total_paid_riyadh_ndts = total_paid_neom_ndts = total_paid_damman_ndts = 0
    total_unpaid_jeddah_ndts = total_unpaid_riyadh_ndts = total_unpaid_neom_ndts = total_unpaid_damman_ndts = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    ndt_list = NonDestructiveTesting.objects.none()  # Default to an empty queryset

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        ndt_list = NonDestructiveTesting.objects.filter(isApprove=True).order_by('-report_no')
        # Apply city filter if selected
        if selected_city:
            ndt_list = ndt_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            ndt_list = ndt_list.filter(
                Q(report_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_ndts = len(ndt_list)

        total_jeddah_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah").count()
        pending_jeddah_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=False).count()
        verified_jeddah_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).count()

        total_riyadh_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh").count()
        pending_riyadh_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=False).count()
        verified_riyadh_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).count()

        total_neom_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM").count()
        pending_neom_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=False).count()
        verified_neom_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).count()

        total_damman_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman").count()
        pending_damman_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=False).count()
        verified_damman_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).count()

        # Paid NonDestructiveTesting
        total_paid_jeddah_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).count()
        total_paid_riyadh_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).count()
        total_paid_neom_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).count()
        total_paid_damman_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).count()

        # Unpaid NonDestructiveTesting
        total_unpaid_jeddah_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_ndts = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()

        # Paid Amount
        total_paid_jeddah_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        ndt_list = NonDestructiveTesting.objects.filter(user=current_user, isApprove=False, created_at__gte=twenty_four_hours_ago).order_by('-report_no')

        if searching_query:
            ndt_list = ndt_list.filter(Q(report_no__icontains=searching_query))

    paginator = Paginator(ndt_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        ndts = paginator.page(int(page))
    except PageNotAnInteger:
        ndts = paginator.page(1)
    except EmptyPage:
        ndts = paginator.page(paginator.num_pages)

    context = {
        'title': 'Manage Non Destructive Testing',
        'ndts': ndts,
        'current_date': current_date,
        'total_ndts': total_ndts,
        'total_jeddah_ndts': total_jeddah_ndts,
        'pending_jeddah_ndts': pending_jeddah_ndts,
        'verified_jeddah_ndts': verified_jeddah_ndts,
        'total_riyadh_ndts': total_riyadh_ndts,
        'pending_riyadh_ndts': pending_riyadh_ndts,
        'verified_riyadh_ndts': verified_riyadh_ndts,
        'total_neom_ndts': total_neom_ndts,
        'pending_neom_ndts': pending_neom_ndts,
        'verified_neom_ndts': verified_neom_ndts,
        'total_damman_ndts': total_damman_ndts,
        'pending_damman_ndts': pending_damman_ndts,
        'verified_damman_ndts': verified_damman_ndts,
        'total_paid_jeddah_ndts': total_paid_jeddah_ndts,
        'total_paid_riyadh_ndts': total_paid_riyadh_ndts,
        'total_paid_neom_ndts': total_paid_neom_ndts,
        'total_paid_damman_ndts': total_paid_damman_ndts,
        'total_unpaid_jeddah_ndts': total_unpaid_jeddah_ndts,
        'total_unpaid_riyadh_ndts': total_unpaid_riyadh_ndts,
        'total_unpaid_neom_ndts': total_unpaid_neom_ndts,
        'total_unpaid_damman_ndts': total_unpaid_damman_ndts,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,  # Include for pre-filling the input
        'manager_city': manager_city,
        'sidebar_active': 'manage_ndt',
    }
    return render(request, 'ndt/manage_ndt.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_ndt_manual(request):
    if request.method == 'GET':
        messages.warning(request, "This form must be submitted through the Manage Ndts page.")
        return redirect('manage_ndt')

    if request.method == 'POST':
        try:
            report_no = request.POST.get('report_no')
            if NonDestructiveTesting.objects.filter(report_no=report_no).exists():
                messages.warning(request, "NDT with this Report No already exists.")
                return redirect('manage_ndt')

            # Parse date strings
            inspection_date_str = request.POST.get('inspection_date')
            expiry_date_str = request.POST.get('expiry_date')
            inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date() if inspection_date_str else None
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

            # Calculate the remaining months
            remaining_months = None
            if inspection_date and expiry_date:
                delta = relativedelta(expiry_date, inspection_date)
                remaining_months = delta.years * 12 + delta.months

            if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
                messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                return redirect('manage_ndt')

            ndt = NonDestructiveTesting(
                user=request.user,
                sr_no=get_next_numeric_sr_no(),
                lh_serial_no=request.POST.get('lh_serial_no'),
                report_no=report_no,
                id_serial_no=request.POST.get('id_serial_no'),
                material=request.POST.get('material'),
                structure_description=request.POST.get('structure_description'),
                inspection_type=request.POST.get('inspection_type'),
                inspection_date=inspection_date_str,
                expiry_date=expiry_date_str,
                remaining_months=remaining_months,
                company_name=request.POST.get('company_name'),
                joint_type=request.POST.get('joint_type'),
                inspected_by=request.POST.get('inspected_by'),
                requested_by=request.POST.get('requested_by'),
                prepared_by=request.POST.get('prepared_by'),
                wasted_serial=request.POST.get('wasted_serial'),
                approved_by=request.POST.get('approved_by'),
                received_by=request.POST.get('received_by'),
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

            ndt._request_user = request.user
            ndt._request = request
            ndt._activity_message = f"Created NDT report {ndt.report_no}"
            ndt.save()
            messages.success(request, "NDT Report added successfully.")
        except Exception as e:
            messages.error(request, f"Error adding NDT: {e}")
            return redirect('manage_ndt')

    return redirect('manage_ndt')


@login_required
def update_ndt(request, uid):
    ndt = get_object_or_404(NonDestructiveTesting, uid=uid)

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('manage_ndt')
        ndt.sr_no = request.POST.get('sr_no')
        ndt.lh_serial_no = request.POST.get('lh_serial_no')
        ndt.report_no = request.POST.get('report_no')
        ndt.id_serial_no = request.POST.get('id_serial_no')
        ndt.material = request.POST.get('material')
        ndt.structure_description = request.POST.get('structure_description')
        ndt.inspection_type = request.POST.get('inspection_type')
        ndt.inspection_date = request.POST.get('inspection_date')
        ndt.expiry_date = request.POST.get('expiry_date')
        ndt.remaining_months = request.POST.get('remaining_months')
        ndt.company_name = request.POST.get('company_name')
        ndt.joint_type = request.POST.get('joint_type')
        ndt.inspected_by = request.POST.get('inspected_by')
        ndt.requested_by = request.POST.get('requested_by')
        ndt.prepared_by = request.POST.get('prepared_by')
        ndt.wasted_serial = request.POST.get('wasted_serial')
        ndt.approved_by = request.POST.get('approved_by')
        ndt.received_by = request.POST.get('received_by')
        ndt.invoice_no = request.POST.get('invoice_no')
        ndt.invoice_date = datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date() if request.POST.get('invoice_date') else now().date()
        ndt.total_amount = Decimal(request.POST.get('total_amount'))
        ndt.amount = Decimal(request.POST.get('amount'))
        ndt.cash_bank = request.POST.get('cash_bank')
        ndt.client_rep_name = request.POST.get('client_rep_name')
        ndt.client_rep_number = request.POST.get('client_rep_number')
        ndt.email = request.POST.get('email')
        ndt.remarks = request.POST.get('remarks')

        ndt._request_user = request.user
        ndt._request = request
        ndt._activity_message = f"Updated NDT report {ndt.report_no}"
        ndt.save()

        messages.success(request, "NDT Report updated successfully.")

    return redirect('manage_ndt')


@login_required
def pending_ndt(request):
    # Get the current logged-in user
    current_user = request.user

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    ndt_list = NonDestructiveTesting.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        ndt_list = NonDestructiveTesting.objects.filter(isApprove=False, isReject=False).order_by('-report_no')
        # Apply city filter if selected
        if selected_city:
            ndt_list = ndt_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            ndt_list = ndt_list.filter(
                Q(report_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        ndt_list = NonDestructiveTesting.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago, isApprove=False, isReject=False).order_by('-report_no')

        if searching_query:
            ndt_list = ndt_list.filter(Q(report_no__icontains=searching_query))

    paginator = Paginator(ndt_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        ndts = paginator.page(int(page))
    except PageNotAnInteger:
        ndts = paginator.page(1)
    except EmptyPage:
        ndts = paginator.page(paginator.num_pages)

    context = {
        'title': 'Pending NDT',
        'ndts': ndts,
        'current_date': current_date,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'pending_ndt',
    }
    return render(request, 'ndt/pending_ndt.html', context)


@login_required
def approve_reject_ndt(request, uid):
    ndt = get_object_or_404(NonDestructiveTesting, uid=uid)

    if request.method == 'POST':
        # Check which button was clicked
        action = request.POST.get('action')
        if action == 'approve':
            ndt.isApprove = True
            ndt.isReject = False
            messages.success(request, 'NonDestructiveTesting approved and updated successfully.')
        elif action == 'reject':
            ndt.isApprove = False
            ndt.isReject = True
            messages.warning(request, 'NonDestructiveTesting rejected and updated successfully.')

        approver = request.user.get_full_name() or request.user.username
        owner = ndt.user.get_full_name() or ndt.user.username
        verdict = 'Approved' if ndt.isApprove else 'Rejected'
        ndt._request_user = request.user
        ndt._request = request
        ndt._activity_message = f"{verdict} NDT report {ndt.report_no} (owner: {owner}) by {approver}"
        ndt.save()
    return redirect('pending_ndt')


@login_required
def export_ndt_data_excel(request, model_name, city):
    if model_name != "ndt":
        return HttpResponse("Invalid category", status=400)

    queryset = NonDestructiveTesting.objects.select_related('user', 'user__profile').filter(user__profile__city__iexact=city)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{model_name.title()} - {city.title()}"

    headers = [
        "S.No", "LH Serial No", "Report No", "ID/Serial No", "Material", "Structure Description", "Inspection Type",
        "Inspection Date", "Expiry Date", "Remaining Months", "Company Name", "Joint Type",
        "Inspected By", "Status", "Note", "Prepared By", "Wasted Serial No", "Approved By", "Received By",
        "Invoice No", "Amount", "Cash/Bank", "Client Representative Name",
        "Client Representative Number", "Email", "Remarks"
    ]
    ws.append(headers)

    # Style header
    header_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Fill rows with data
    for idx, obj in enumerate(queryset, start=1):
        ws.append([
            idx,
            obj.lh_serial_no,
            obj.report_no,
            obj.id_serial_no,
            obj.material,
            obj.structure_description,
            obj.inspection_type,
            obj.inspection_date,
            obj.expiry_date,
            obj.remaining_months,
            obj.company_name,
            obj.joint_type,
            obj.inspected_by,
            obj.status,
            obj.note,
            obj.prepared_by,
            obj.wasted_serial,
            obj.approved_by,
            obj.received_by,
            obj.invoice_no,
            obj.amount,
            obj.cash_bank,
            obj.client_rep_name,
            obj.client_rep_number,
            obj.email,
            obj.remarks,
        ])

    # Export as Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{model_name}_{city}_export.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@login_required
def unpaid_ndt(request):
    # Get the current logged-in user
    current_user = request.user
    total_unpaid_ndt = 0
    total_unpaid_jeddah_ndt = total_unpaid_riyadh_ndt = total_unpaid_neom_ndt = total_unpaid_damman_ndt = 0

    searching_query = request.GET.get('searching_query', '').strip()
    ndt_list = NonDestructiveTesting.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        ndt_list = NonDestructiveTesting.objects.filter(isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).order_by('-report_no')

        # Managers only see their own city's records
        if manager_city:
            ndt_list = ndt_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            ndt_list = ndt_list.filter(Q(report_no__icontains=searching_query))

        total_unpaid_ndt = ndt_list.count()

        # Unpaid NDT
        total_unpaid_jeddah_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).filter(Q(amount__isnull=True) | Q(amount=0)).count()
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        ndt_list = NonDestructiveTesting.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-report_no')

        if searching_query:
            ndt_list = ndt_list.filter(Q(report_no__icontains=searching_query))

    paginator = Paginator(ndt_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        ndts = paginator.page(int(page))
    except PageNotAnInteger:
        ndts = paginator.page(1)
    except EmptyPage:
        ndts = paginator.page(paginator.num_pages)

    context = {
        'title': 'Unpaid NDT',
        'ndts': ndts,
        'current_date': current_date,
        'total_unpaid_ndt': total_unpaid_ndt,
        'total_unpaid_jeddah_ndt': total_unpaid_jeddah_ndt,
        'total_unpaid_riyadh_ndt': total_unpaid_riyadh_ndt,
        'total_unpaid_neom_ndt': total_unpaid_neom_ndt,
        'total_unpaid_damman_ndt': total_unpaid_damman_ndt,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'unpaid_ndt',
    }
    return render(request, 'ndt/unpaid_ndt.html', context)


@login_required
def update_unpaid_ndt(request, uid):
    ndt = get_object_or_404(NonDestructiveTesting, uid=uid)

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('unpaid_ndt')
        ndt.sr_no = request.POST.get('sr_no')
        ndt.lh_serial_no = request.POST.get('lh_serial_no')
        ndt.report_no = request.POST.get('report_no')
        ndt.id_serial_no = request.POST.get('id_serial_no')
        ndt.material = request.POST.get('material')
        ndt.structure_description = request.POST.get('structure_description')
        ndt.inspection_type = request.POST.get('inspection_type')
        ndt.inspection_date = request.POST.get('inspection_date')
        ndt.expiry_date = request.POST.get('expiry_date')
        ndt.remaining_months = request.POST.get('remaining_months')
        ndt.company_name = request.POST.get('company_name')
        ndt.joint_type = request.POST.get('joint_type')
        ndt.inspected_by = request.POST.get('inspected_by')
        ndt.requested_by = request.POST.get('requested_by')
        ndt.prepared_by = request.POST.get('prepared_by')
        ndt.wasted_serial = request.POST.get('wasted_serial')
        ndt.approved_by = request.POST.get('approved_by')
        ndt.received_by = request.POST.get('received_by')
        ndt.invoice_no = request.POST.get('invoice_no')
        ndt.amount = request.POST.get('amount')
        ndt.cash_bank = request.POST.get('cash_bank')
        ndt.client_rep_name = request.POST.get('client_rep_name')
        ndt.client_rep_number = request.POST.get('client_rep_number')
        ndt.email = request.POST.get('email')
        ndt.remarks = request.POST.get('remarks')

        ndt._request_user = request.user
        ndt._request = request
        ndt._activity_message = f"Updated NDT report {ndt.report_no}"
        ndt.save()

        messages.success(request, "NDT Report updated successfully.")
    return redirect('unpaid_ndt')


@login_required
def paid_ndt(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_ndt = 0
    total_paid_jeddah_ndt = total_paid_riyadh_ndt = total_paid_neom_ndt = total_paid_damman_ndt = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    ndt_list = NonDestructiveTesting.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        ndt_list = NonDestructiveTesting.objects.filter(isApprove=True).exclude(amount=0).order_by('-report_no')

        # Managers only see their own city's records
        if manager_city:
            ndt_list = ndt_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            ndt_list = ndt_list.filter(Q(report_no__icontains=searching_query))

        total_paid_ndt = ndt_list.count()

        # Paid Certificate
        total_paid_jeddah_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).count()
        total_paid_riyadh_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).count()
        total_paid_neom_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).count()
        total_paid_damman_ndt = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).count()

        # Paid Amount
        total_paid_jeddah_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="NEOM", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = NonDestructiveTesting.objects.filter(user__profile__city__iexact="Damman", isApprove=True).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        ndt_list = NonDestructiveTesting.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-report_no')

        if searching_query:
            ndt_list = ndt_list.filter(Q(report_no__icontains=searching_query))

    paginator = Paginator(ndt_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        ndts = paginator.page(int(page))
    except PageNotAnInteger:
        ndts = paginator.page(1)
    except EmptyPage:
        ndts = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid NDT',
        'ndts': ndts,
        'current_date': current_date,
        'total_paid_ndt': total_paid_ndt,
        'total_paid_jeddah_ndt': total_paid_jeddah_ndt,
        'total_paid_riyadh_ndt': total_paid_riyadh_ndt,
        'total_paid_neom_ndt': total_paid_neom_ndt,
        'total_paid_damman_ndt': total_paid_damman_ndt,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'paid_ndt',
    }
    return render(request, 'ndt/paid_ndt.html', context)


@login_required
def report_ndt(request):
    current_user = request.user

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    inspection_type = request.GET.get('inspection_type', '').strip()

    ndt_list = NonDestructiveTesting.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # For admin users (superuser or manager)
    if current_user.is_superuser or current_user.is_staff:
        ndt_list = NonDestructiveTesting.objects.all().order_by('-report_no')

        if status == 'True':
            ndt_list = ndt_list.filter(isApprove=True)
        elif status == 'False':
            ndt_list = ndt_list.filter(isApprove=False)

        if from_date and to_date:
            from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
            ndt_list = ndt_list.filter(created_at__range=[from_dt, to_dt])

        if selected_city:
            ndt_list = ndt_list.filter(user__profile__city__iexact=selected_city)

        if company_name:
            ndt_list = ndt_list.filter(company_name__icontains=company_name)

        if inspection_type:
            ndt_list = ndt_list.filter(inspection_type__icontains=inspection_type)
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        ndt_list = NonDestructiveTesting.objects.filter(
            user=current_user, isApprove=False, created_at__gte=twenty_four_hours_ago
        ).order_by('-report_no')

    paginator = Paginator(ndt_list, 50)
    page = request.GET.get('page', '1')

    try:
        ndts = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        ndts = paginator.page(1)

    context = {
        'title': 'Report NDT',
        'ndts': ndts,
        'current_date': timezone.now().date(),
        'total_ndts': ndt_list.count(),
        'from_date': from_date,
        'to_date': to_date,
        'selected_city': selected_city,
        'selected_status': status,
        'company_name': company_name,
        'inspection_type': inspection_type,
        'manager_city': manager_city,
        'sidebar_active': 'report_ndt',
    }
    return render(request, 'ndt/report_ndt.html', context)


@login_required
def report_paid_ndt(request):
    current_user = request.user
    total_paid_ndt = 0
    total_paid_jeddah_ndt = total_paid_riyadh_ndt = total_paid_neom_ndt = total_paid_damman_ndt = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = total_paid_amount = 0

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    ndt_list = NonDestructiveTesting.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    if current_user.is_superuser or current_user.is_staff:
        ndt_list = NonDestructiveTesting.objects.filter(isApprove=True).exclude(amount=0).order_by('-report_no')

        # Managers only see their own city's records
        if manager_city:
            ndt_list = ndt_list.filter(user__profile__city__iexact=manager_city)

        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                ndt_list = ndt_list.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass

        total_paid_ndt = ndt_list.count()

        # Base query for city statistics
        city_queryset = NonDestructiveTesting.objects.filter(isApprove=True).exclude(amount=0)
        if manager_city:
            city_queryset = city_queryset.filter(user__profile__city__iexact=manager_city)

        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                city_queryset = city_queryset.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass

        total_paid_jeddah_ndt = city_queryset.filter(user__profile__city__iexact="Jeddah").count()
        total_paid_riyadh_ndt = city_queryset.filter(user__profile__city__iexact="Riyadh").count()
        total_paid_neom_ndt = city_queryset.filter(user__profile__city__iexact="NEOM").count()
        total_paid_damman_ndt = city_queryset.filter(user__profile__city__iexact="Damman").count()

        total_paid_jeddah_amount = city_queryset.filter(user__profile__city__iexact="Jeddah").aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = city_queryset.filter(user__profile__city__iexact="Riyadh").aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = city_queryset.filter(user__profile__city__iexact="NEOM").aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = city_queryset.filter(user__profile__city__iexact="Damman").aggregate(Sum('amount'))['amount__sum'] or 0

        total_paid_amount = total_paid_jeddah_amount + total_paid_riyadh_amount + total_paid_neom_amount + total_paid_damman_amount
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        ndt_list = NonDestructiveTesting.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-report_no')

    paginator = Paginator(ndt_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        ndts = paginator.page(int(page))
    except PageNotAnInteger:
        ndts = paginator.page(1)
    except EmptyPage:
        ndts = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid NDT',
        'ndts': ndts,
        'current_date': current_date,
        'total_paid_ndt': total_paid_ndt,
        'total_paid_jeddah_ndt': total_paid_jeddah_ndt,
        'total_paid_riyadh_ndt': total_paid_riyadh_ndt,
        'total_paid_neom_ndt': total_paid_neom_ndt,
        'total_paid_damman_ndt': total_paid_damman_ndt,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'total_paid_amount': total_paid_amount,
        'from_date': from_date,
        'to_date': to_date,
        'manager_city': manager_city,
        'sidebar_active': 'report_paid_ndt',
    }
    return render(request, 'ndt/report_paid_ndt.html', context)
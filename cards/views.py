from decimal import Decimal
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods

from base.utils import (
    items_per_page, current_date, get_manager_city,
    can_access_record, can_manage_record, assert_city_allowed, safe_cell,
    handle_amount_field_update, redirect_back, can_approve_reject,
)
from cards.models import Card
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now  # Make sure this import is present
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from django.http import HttpResponse

from django.http import JsonResponse
import json
from decimal import Decimal, InvalidOperation



@login_required
def manage_cards(request):
    # Get the current logged-in user
    current_user = request.user
    total_cards = 0
    total_jeddah_card = pending_jeddah_card = verified_jeddah_card = 0
    total_riyadh_card = pending_riyadh_card = verified_riyadh_card = 0
    total_neom_card = pending_neom_card = verified_neom_card = 0
    total_damman_card = pending_damman_card = verified_damman_card = 0
    total_paid_jeddah_card = total_paid_riyadh_card = total_paid_neom_card = total_paid_damman_card = 0
    total_unpaid_jeddah_card = total_unpaid_riyadh_card = total_unpaid_neom_card = total_unpaid_damman_card = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    card_list = Card.objects.none()  # Default to an empty queryset

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        card_list = Card.objects.filter(isApprove=True, isCancel=False, isHold = False).order_by('-card_no')
        # Apply city filter if selected
        if selected_city:
            card_list = card_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            card_list = card_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_cards = card_list.count()

        total_jeddah_card = Card.objects.filter(user__profile__city__iexact="Jeddah").count()
        pending_jeddah_card = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=False, isCancel=False, isHold = False).count()
        verified_jeddah_card = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).count()

        total_riyadh_card = Card.objects.filter(user__profile__city__iexact="Riyadh").count()
        pending_riyadh_card = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=False, isCancel=False, isHold = False).count()
        verified_riyadh_card = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).count()

        total_neom_card = Card.objects.filter(user__profile__city__iexact="NEOM").count()
        pending_neom_card = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=False, isCancel=False, isHold = False).count()
        verified_neom_card = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).count()

        total_damman_card = Card.objects.filter(user__profile__city__iexact="Damman").count()
        pending_damman_card = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=False, isCancel=False, isHold = False).count()
        verified_damman_card = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).count()

        # Paid Cards
        total_paid_jeddah_card = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()
        total_paid_riyadh_card = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()
        total_paid_neom_card = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()
        total_paid_damman_card = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()

        # Unpaid Cards
        total_unpaid_jeddah_card = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_card = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_card = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_card = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()

        # Paid Amount
        total_paid_jeddah_amount = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        card_list = Card.objects.filter(user=current_user, isApprove=False, isCancel=False, isHold = False, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

        if searching_query:
            card_list = card_list.filter(Q(card_no__icontains=searching_query))

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Manage Cards',
        'cards': cards,
        'current_date': current_date,
        'total_cards': total_cards,
        'total_jeddah_card': total_jeddah_card,
        'pending_jeddah_card': pending_jeddah_card,
        'verified_jeddah_card': verified_jeddah_card,
        'total_riyadh_card': total_riyadh_card,
        'pending_riyadh_card': pending_riyadh_card,
        'verified_riyadh_card': verified_riyadh_card,
        'total_neom_card': total_neom_card,
        'pending_neom_card': pending_neom_card,
        'verified_neom_card': verified_neom_card,
        'total_damman_card': total_damman_card,
        'pending_damman_card': pending_damman_card,
        'verified_damman_card': verified_damman_card,
        'total_paid_jeddah_card': total_paid_jeddah_card,
        'total_paid_riyadh_card': total_paid_riyadh_card,
        'total_paid_neom_card': total_paid_neom_card,
        'total_paid_damman_card': total_paid_damman_card,
        'total_unpaid_jeddah_card': total_unpaid_jeddah_card,
        'total_unpaid_riyadh_card': total_unpaid_riyadh_card,
        'total_unpaid_neom_card': total_unpaid_neom_card,
        'total_unpaid_damman_card': total_unpaid_damman_card,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,  # Include for pre-filling the input
        'manager_city': manager_city,
        'sidebar_active': 'manage_cards',
    }
    return render(request, 'cards/manage_cards.html', context)


@login_required
def report_cards(request):
    current_user = request.user
    total_cards = 0

    # Get filter parameters
    # Keep original date strings for the template
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    trade = request.GET.get('trade', '').strip()

    card_list = Card.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # For admin users (superuser or manager)
    if current_user.is_superuser or current_user.is_staff:
        card_list = Card.objects.all().order_by('-card_no')

        # Apply status filter
        if status == 'True':
            card_list = card_list.filter(isApprove=True, isCancel=False, isHold = False)
        elif status == 'False':
            card_list = card_list.filter(isApprove=False, isCancel=False, isHold = False)

        # Apply date range filter with timezone awareness
        if from_date and to_date:
            from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
            card_list = card_list.filter(created_at__range=[from_dt, to_dt])

        # Apply city filter
        if selected_city:
            card_list = card_list.filter(user__profile__city__iexact=selected_city)

        # Apply company name filter
        if company_name:
            card_list = card_list.filter(company_name__icontains=company_name)

        # Apply trade filter
        if trade:
            card_list = card_list.filter(trade__icontains=trade)

    # For regular users
    else:
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        card_list = Card.objects.filter(
            user=current_user,
            isApprove=False, isCancel=False, isHold = False,
            created_at__gte=twenty_four_hours_ago
        ).order_by('-card_no')

    # Pagination
    paginator = Paginator(card_list, 50)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except (PageNotAnInteger, EmptyPage):
        cards = paginator.page(1)

    context = {
        'title': 'Report Cards',
        'cards': cards,
        'current_date': timezone.now().date(),
        'total_cards': card_list.count(),
        'from_date': from_date,
        'to_date': to_date,
        'selected_city': selected_city,
        'selected_status': status,
        'company_name': company_name,
        'trade': trade,
        'manager_city': manager_city,
        'sidebar_active': 'report_cards',
    }
    return render(request, 'cards/report_cards.html', context)


@login_required
def export_cards_csv(request):
    # Only staff/superusers may bulk-export; managers are locked to their own city
    manager_city = get_manager_city(request.user)
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'You do not have permission to export cards.')
        return redirect('manage_cards')

    # Get filter parameters from the request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_city = request.GET.get('city', '').strip()
    status = request.GET.get('status')
    company_name = request.GET.get('company_name', '').strip()
    trade = request.GET.get('trade', '').strip()

    if manager_city:
        selected_city = manager_city

    # Start with base queryset — select_related avoids N+1 on user/profile per row
    card_list = Card.objects.select_related('user', 'user__profile').all()

    # Apply filters
    if status == 'True':
        card_list = card_list.filter(isApprove=True, isCancel=False, isHold = False)
    elif status == 'False':
        card_list = card_list.filter(isApprove=False, isCancel=False, isHold = False)

    if from_date and to_date:
        from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
        to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
        card_list = card_list.filter(created_at__range=[from_dt, to_dt])

    if selected_city:
        card_list = card_list.filter(user__profile__city__iexact=selected_city)
        
    # Apply company name filter
    if company_name:
        card_list = card_list.filter(company_name__icontains=company_name)
        
    # Apply trade filter
    if trade:
        card_list = card_list.filter(trade__icontains=trade)

    # Create the HttpResponse object with the appropriate Excel header
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="cards_export.xlsx"'

    # Create a new Excel workbook and add a worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cards"

    # Define headers based on your template
    headers = [
        'S.No', 'Name', 'City', 'Card Type', 'Card No', 'Iqama No',
        'Operator Name', 'Company Name', 'Issue Date', 'Expiry Date',
        'Remaining Months', 'Trade', 'Holo Gram #', 'Assessed By', 'Status',
        'Note', 'Wasted Serial', 'Requested By', 'Prepared By', 'Invoice No',
        'Invoice Date', 'Total Amount', 'Paid Amount', 'Cash/Bank',
        'Client Representative Name', 'Client Representative Number',
        'Email', 'Remarks'
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
                        dt = datetime.strptime(str(date_value).split(' ')[0], fmt)
                        return dt.strftime('%Y-%m-%d')
                    except (ValueError, AttributeError):
                        continue
            return str(date_value).split(' ')[0]  # Return just the date part if parsing fails
        except Exception:
            return str(date_value) if date_value else ''

    # Write data rows
    for row_num, card in enumerate(card_list, 2):  # Start from row 2 (after header)
        row_data = [
            row_num - 1,  # S.No
            f"{getattr(card.user, 'first_name', '') or ''}_{getattr(card.user, 'last_name', '') or ''}",
            getattr(card, 'city', '') or '',
            getattr(card, 'card_type', '') or '',
            getattr(card, 'card_no', '') or '',
            getattr(card, 'iqama_no', '') or '',
            getattr(card, 'operator_name', '') or '',
            getattr(card, 'company_name', '') or '',
            format_date(getattr(card, 'issue_date', None)),
            format_date(getattr(card, 'expiry_date', None)),
            getattr(card, 'remaining_months', '') or '',
            getattr(card, 'trade', '') or '',
            getattr(card, 'holo_gram_no', '') or '',
            getattr(card, 'assessed_by', '') or '',
            getattr(card, 'status', '') or '',
            getattr(card, 'note', '') or '',
            getattr(card, 'wasted_serial', '') or '',
            getattr(card, 'requested_by', '') or '',
            getattr(card, 'prepared_by', '') or '',
            getattr(card, 'invoice_no', '') or '',
            format_date(getattr(card, 'invoice_date', None)),
            float(getattr(card, 'total_amount', 0) or 0),
            float(getattr(card, 'amount', 0) or 0),
            getattr(card, 'cash_bank', '') or '',
            getattr(card, 'client_rep_name', '') or '',
            getattr(card, 'client_rep_number', '') or '',
            getattr(card, 'email', '') or '',
            getattr(card, 'remarks', '') or ''
        ]

        # Write each cell in the row
        for col_num, cell_value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num, value=safe_cell(cell_value))

    # Auto-size columns based on actual data
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
def add_card_manual(request):
    if request.method == 'GET':
        messages.warning(request, "This form must be submitted through the Manage Cards page.")
        return redirect('manage_cards')

    if request.method == 'POST':
        try:
            # Get and validate card number
            card_no = request.POST.get('card_no', '').strip()
            if not card_no:
                messages.error(request, "Card number cannot be empty.")
                return redirect('manage_cards')
            
            # Check for duplicate card number (case-insensitive)
            if Card.objects.filter(card_no__iexact=card_no).exists():
                existing = Card.objects.filter(card_no__iexact=card_no).first()
                messages.warning(request, f"A card with number '{existing.card_no}' already exists (case-insensitive match).")
                return redirect('manage_cards')

            # Parse dates if provided
            issue_date_str = request.POST.get('issue_date')
            expiry_date_str = request.POST.get('expiry_date')
            issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

            # Calculate remaining months if both dates are present
            remaining_months = None
            if issue_date and expiry_date:
                delta = relativedelta(expiry_date, issue_date)
                remaining_months = delta.years * 12 + delta.months

            # Check amount validity
            total_amount = Decimal(request.POST.get('total_amount') or '0')
            paid_amount = Decimal(request.POST.get('amount') or '0')
            if paid_amount > total_amount:
                messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                return redirect('manage_cards')

            # Create and save Card instance with the trimmed card_no
            card = Card(
                user=request.user,
                sr_no=request.POST.get('sr_no'),
                card_type=request.POST.get('card_type'),
                card_no=card_no,  # Using the already trimmed card_no
                iqama_no=request.POST.get('iqama_no'),
                operator_name=request.POST.get('operator_name'),
                company_name=request.POST.get('company_name'),
                issue_date=issue_date,
                expiry_date=expiry_date,
                remaining_months=remaining_months,
                trade=request.POST.get('trade'),
                holo_gram_no=request.POST.get('holo_gram_no'),
                assessed_by=request.POST.get('assessed_by'),
                wasted_serial=request.POST.get('wasted_serial'),
                requested_by=request.POST.get('requested_by'),
                prepared_by=request.POST.get('prepared_by'),
                invoice_no=request.POST.get('invoice_no'),
                invoice_date=datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date() if request.POST.get('invoice_date') else now().date(),
                total_amount=total_amount,
                amount=paid_amount,
                cash_bank=request.POST.get('cash_bank'),
                client_rep_name=request.POST.get('client_rep_name'),
                client_rep_number=request.POST.get('client_rep_number'),
                email=request.POST.get('email'),
                remarks=request.POST.get('remarks'),
            )

            # Optional: log user activity for auditing
            card._request_user = request.user
            card._request = request
            card._activity_message = f"Created new card {card.card_no}"
            try:
                card.save()
                messages.success(request, "Card added successfully.")
            except IntegrityError as e:
                if 'unique' in str(e).lower():
                    messages.error(request, "This card number was just added by another user. Please try a different number.")
                else:
                    messages.error(request, f"Database error while saving: {str(e)}")
                return redirect('manage_cards')

        except Exception as e:
            messages.error(request, f"Error adding card: {str(e)}")
            return redirect('manage_cards')
    return redirect('manage_cards')


@login_required
def update_card(request, uid):
    card = get_object_or_404(Card, uid=uid)
    if not can_access_record(request.user, card):
        messages.error(request, 'You do not have permission to edit this card.')
        return redirect('manage_cards')

    if request.method == 'POST':
        try:
            # Validate amounts
            if Decimal(request.POST.get('amount', 0)) > Decimal(request.POST.get('total_amount', 0)):
                messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
                return redirect('manage_cards')

            # Get and validate card number
            card_no = request.POST.get('card_no', '').strip()
            if not card_no:
                messages.error(request, "Card number cannot be empty.")
                return redirect('manage_cards')
                
            # Check for duplicate (case-insensitive, excluding current record)
            if Card.objects.exclude(uid=uid).filter(card_no__iexact=card_no).exists():
                existing = Card.objects.filter(card_no__iexact=card_no).first()
                messages.warning(request, f"Another card with number '{existing.card_no}' already exists (case-insensitive match).")
                return redirect('manage_cards')

            # Update card fields
            card.sr_no = request.POST.get('sr_no')
            card.card_no = card_no
            card.card_type = request.POST.get('card_type')
            card.iqama_no = request.POST.get('iqama_no')
            card.operator_name = request.POST.get('operator_name')
            card.company_name = request.POST.get('company_name')
            card.issue_date = request.POST.get('issue_date')
            card.expiry_date = request.POST.get('expiry_date')
            card.remaining_months = request.POST.get('remaining_months')
            card.trade = request.POST.get('trade')
            card.holo_gram_no = request.POST.get('holo_gram_no')
            card.assessed_by = request.POST.get('assessed_by')
            card.wasted_serial = request.POST.get('wasted_serial')
            card.requested_by = request.POST.get('requested_by')
            card.prepared_by = request.POST.get('prepared_by')
            card.invoice_no = request.POST.get('invoice_no')
            card.invoice_date = datetime.strptime(request.POST.get('invoice_date'), '%Y-%m-%d').date() if request.POST.get('invoice_date') else now().date()
            card.total_amount = Decimal(request.POST.get('total_amount', 0))
            card.amount = Decimal(request.POST.get('amount', 0))
            card.cash_bank = request.POST.get('cash_bank')
            card.client_rep_name = request.POST.get('client_rep_name')
            card.client_rep_number = request.POST.get('client_rep_number')
            card.email = request.POST.get('email')
            card.remarks = request.POST.get('remarks')

            # Set audit fields
            card._request_user = request.user
            card._request = request
            card._activity_message = f"Updated card {card.card_no}"

            try:
                card.save()
                messages.success(request, "Card updated successfully.")
            except IntegrityError as e:
                if 'unique' in str(e).lower():
                    messages.error(request, "This card number was just updated by another user. Please try again.")
                else:
                    messages.error(request, f"Database error while saving: {str(e)}")
                return redirect('manage_cards')

        except Exception as e:
            messages.error(request, f"Error updating card: {str(e)}")
            return redirect('manage_cards')

    return redirect('manage_cards')


@login_required
def pending_cards(request):
    # Get the current logged-in user
    current_user = request.user

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    card_list = Card.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        card_list = Card.objects.filter(isApprove=False, isCancel=False, isHold = False, isReject=False).order_by('-card_no')
        # Apply city filter if selected
        if selected_city:
            card_list = card_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            card_list = card_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        card_list = Card.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago, isApprove=False, isCancel=False, isHold = False, isReject=False).order_by('-card_no')

        if searching_query:
            card_list = card_list.filter(Q(card_no__icontains=searching_query))

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Pending Cards',
        'cards': cards,
        'current_date': current_date,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'pending_cards',
    }
    return render(request, 'cards/pending_cards.html', context)


@login_required
def approve_reject_cards(request, uid):
    card = get_object_or_404(Card, uid=uid)
    if not can_approve_reject(request.user, card):
        messages.error(request, 'You do not have permission to approve or reject cards. Ask an admin to grant it from Manage Accounts.')
        return redirect_back(request, 'pending_cards')

    if request.method == 'POST':
        # Check which button was clicked
        action = request.POST.get('action')
        if action == 'approve':
            card.isApprove = True
            card.isReject = False
            messages.success(request, 'Card approved and updated successfully.')
        elif action == 'reject':
            card.isApprove = False
            card.isReject = True
            messages.warning(request, 'Card rejected and updated successfully.')

        approver = request.user.get_full_name() or request.user.username
        owner = card.user.get_full_name() or card.user.username
        verdict = 'Approved' if card.isApprove else 'Rejected'
        card._request_user = request.user
        card._request = request
        card._activity_message = f"{verdict} card {card.card_no} (owner: {owner}) by {approver}"
        card.save()
    return redirect_back(request, 'pending_cards')


@login_required
def export_card_and_city_excel(request, model_name, city):
    if model_name != "card":
        return HttpResponse("Invalid category", status=400)
    if not assert_city_allowed(request.user, city):
        messages.error(request, 'You do not have permission to export this city.')
        return redirect('manage_cards')

    queryset = Card.objects.filter(user__profile__city__iexact=city)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{model_name.title()} - {city.title()}"

    # Updated headers to match requested <th> columns
    headers = [
        "S.No", "Card No", "Iqama No", "Operator Name", "Company Name",
        "Issue Date", "Expiry Date", "Remaining Months", "Trade", "Holo Gram #",
        "Assessed By", "Status", "Note", "Wasted Serial", "Requested By",
        "Prepared By", "Invoice No", "Total Amount", "Paid Amount", "Cash/Bank",
        "Client Representative Name", "Client Representative Number",
        "Email", "Remarks"
    ]
    ws.append(headers)

    # Style header row (dark background with white bold text)
    header_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Populate data rows
    for idx, obj in enumerate(queryset, start=1):
        ws.append([safe_cell(v) for v in [
            idx,
            obj.card_no,
            obj.iqama_no,
            obj.operator_name,
            obj.company_name,
            obj.issue_date,
            obj.expiry_date,
            obj.remaining_months,
            obj.trade,
            obj.holo_gram_no,
            obj.assessed_by,
            obj.status,
            obj.note,
            obj.wasted_serial,
            obj.requested_by,
            obj.prepared_by,
            obj.invoice_no,
            obj.total_amount,
            obj.amount,
            obj.cash_bank,
            obj.client_rep_name,
            obj.client_rep_number,
            obj.email,
            obj.remarks,
        ]])

    # Return Excel file as HTTP response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"{model_name}_{city}_export.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@login_required
def unpaid_cards(request):
    # Get the current logged-in user
    current_user = request.user
    total_unpaid_cards = 0
    total_unpaid_jeddah_cards = total_unpaid_riyadh_cards = total_unpaid_neom_cards = total_unpaid_damman_cards = 0

    searching_query = request.GET.get('searching_query', '').strip()
    card_list = Card.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        card_list = Card.objects.filter(isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).order_by('-card_no')

        # Managers only see their own city's records
        if manager_city:
            card_list = card_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            card_list = card_list.filter(Q(card_no__icontains=searching_query))

        total_unpaid_cards = card_list.count()

        # Unpaid Card
        total_unpaid_jeddah_cards = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_riyadh_cards = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_neom_cards = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
        total_unpaid_damman_cards = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).filter(Q(amount__isnull=True) | Q(amount=0)).count()
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        card_list = Card.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

        if searching_query:
            card_list = card_list.filter(Q(card_no__icontains=searching_query))

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Unpaid Cards',
        'cards': cards,
        'current_date': current_date,
        'total_unpaid_cards': total_unpaid_cards,
        'total_unpaid_jeddah_cards': total_unpaid_jeddah_cards,
        'total_unpaid_riyadh_cards': total_unpaid_riyadh_cards,
        'total_unpaid_neom_cards': total_unpaid_neom_cards,
        'total_unpaid_damman_cards': total_unpaid_damman_cards,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'unpaid_cards',
    }
    return render(request, 'cards/unpaid_cards.html', context)


@login_required
def update_unpaid_card(request, uid):
    card = get_object_or_404(Card, uid=uid)
    if not can_access_record(request.user, card):
        messages.error(request, 'You do not have permission to edit this card.')
        return redirect('unpaid_cards')

    if request.method == 'POST':
        if Decimal(request.POST.get('amount')) > Decimal(request.POST.get('total_amount')):
            messages.error(request, "Paid amount is greater than Total amount. Please check the form data.")
            return redirect('unpaid_cards')
        card.sr_no = request.POST.get('sr_no')
        card.card_type = request.POST.get('card_type')
        card.card_no = request.POST.get('card_no')
        card.iqama_no = request.POST.get('iqama_no')
        card.operator_name = request.POST.get('operator_name')
        card.company_name = request.POST.get('company_name')
        card.issue_date = request.POST.get('issue_date')
        card.expiry_date = request.POST.get('expiry_date')
        card.remaining_months = request.POST.get('remaining_months')
        card.trade = request.POST.get('trade')
        card.holo_gram_no = request.POST.get('holo_gram_no')
        card.assessed_by = request.POST.get('assessed_by')
        card.wasted_serial = request.POST.get('wasted_serial')
        card.requested_by = request.POST.get('requested_by')
        card.prepared_by = request.POST.get('prepared_by')
        card.invoice_no = request.POST.get('invoice_no')
        card.amount = request.POST.get('amount')
        card.cash_bank = request.POST.get('cash_bank')
        card.client_rep_name = request.POST.get('client_rep_name')
        card.client_rep_number = request.POST.get('client_rep_number')
        card.email = request.POST.get('email')
        card.remarks = request.POST.get('remarks')

        card._request_user = request.user
        card._request = request
        card._activity_message = f"Updated card {card.card_no}"
        card.save()

        messages.success(request, "Card updated successfully.")
    return redirect('unpaid_cards')


@login_required
@require_POST
def update_card_field(request, uid):
    """Inline Total/Paid Amount edit from the Paid & Unpaid tables."""
    return handle_amount_field_update(request, Card, uid)


@login_required
def paid_cards(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_cards = 0
    total_paid_jeddah_cards = total_paid_riyadh_cards = total_paid_neom_cards = total_paid_damman_cards = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = 0

    searching_query = request.GET.get('searching_query', '').strip()
    card_list = Card.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        card_list = Card.objects.filter(isApprove=True, isCancel=False, isHold = False).exclude(amount=0).order_by('-card_no')

        # Managers only see their own city's records
        if manager_city:
            card_list = card_list.filter(user__profile__city__iexact=manager_city)

        if searching_query:
            card_list = card_list.filter(Q(card_no__icontains=searching_query))

        total_paid_cards = card_list.count()

        # Paid cards
        total_paid_jeddah_cards = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()
        total_paid_riyadh_cards = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()
        total_paid_neom_cards = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()
        total_paid_damman_cards = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).count()

        # Paid Amount
        total_paid_jeddah_amount = Card.objects.filter(user__profile__city__iexact="Jeddah", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_riyadh_amount = Card.objects.filter(user__profile__city__iexact="Riyadh", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_neom_amount = Card.objects.filter(user__profile__city__iexact="NEOM", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid_damman_amount = Card.objects.filter(user__profile__city__iexact="Damman", isApprove=True, isCancel=False, isHold = False).exclude(amount=0).aggregate(Sum('amount'))['amount__sum'] or 0
    else:
        # Get the current time
        now = timezone.now()
        # Show only the current user's records created in the last 24 hours
        twenty_four_hours_ago = now - timedelta(hours=24)
        card_list = Card.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

        if searching_query:
            card_list = card_list.filter(Q(card_no__icontains=searching_query))

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Cards',
        'cards': cards,
        'current_date': current_date,
        'total_paid_cards': total_paid_cards,
        'total_paid_jeddah_cards': total_paid_jeddah_cards,
        'total_paid_riyadh_cards': total_paid_riyadh_cards,
        'total_paid_neom_cards': total_paid_neom_cards,
        'total_paid_damman_cards': total_paid_damman_cards,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'paid_cards',
    }
    return render(request, 'cards/paid_cards.html', context)


@login_required
def report_paid_cards(request):
    # Get the current logged-in user
    current_user = request.user
    total_paid_cards = 0
    total_paid_jeddah_cards = total_paid_riyadh_cards = total_paid_neom_cards = total_paid_damman_cards = 0
    total_paid_jeddah_amount = total_paid_riyadh_amount = total_paid_neom_amount = total_paid_damman_amount = total_paid_amount = 0

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    card_list = Card.objects.none()

    # Managers (is_staff) act as admins limited to their own city
    manager_city = get_manager_city(current_user)

    # Check if the user is a superuser (admin) or a manager
    if current_user.is_superuser or current_user.is_staff:
        # Show all records for admin
        card_list = Card.objects.filter(isApprove=True, isCancel=False, isHold = False).exclude(amount=0).order_by('-card_no')

        # Managers only see their own city's records
        if manager_city:
            card_list = card_list.filter(user__profile__city__iexact=manager_city)

        # Apply date range filter with timezone awareness
        if from_date and to_date:
            try:
                from_dt = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
                to_dt = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
                card_list = card_list.filter(created_at__range=[from_dt, to_dt])
            except (ValueError, TypeError):
                pass

        total_paid_cards = card_list.count()

        # Base query for city statistics
        city_queryset = Card.objects.filter(isApprove=True, isCancel=False, isHold = False).exclude(amount=0)
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

        # Paid Cards counts with date filtering
        total_paid_jeddah_cards = city_queryset.filter(user__profile__city__iexact="Jeddah").count()
        total_paid_riyadh_cards = city_queryset.filter(user__profile__city__iexact="Riyadh").count()
        total_paid_neom_cards = city_queryset.filter(user__profile__city__iexact="NEOM").count()
        total_paid_damman_cards = city_queryset.filter(user__profile__city__iexact="Damman").count()

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
        card_list = Card.objects.filter(user=current_user, created_at__gte=twenty_four_hours_ago).order_by('-card_no')

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Paid Cards',
        'cards': cards,
        'current_date': current_date,
        'total_paid_cards': total_paid_cards,
        'total_paid_jeddah_cards': total_paid_jeddah_cards,
        'total_paid_riyadh_cards': total_paid_riyadh_cards,
        'total_paid_neom_cards': total_paid_neom_cards,
        'total_paid_damman_cards': total_paid_damman_cards,
        'total_paid_jeddah_amount': total_paid_jeddah_amount,
        'total_paid_riyadh_amount': total_paid_riyadh_amount,
        'total_paid_neom_amount': total_paid_neom_amount,
        'total_paid_damman_amount': total_paid_damman_amount,
        'total_paid_amount': total_paid_amount,
        'from_date': from_date,
        'to_date': to_date,
        'manager_city': manager_city,
        'sidebar_active': 'report_paid_cards',
    }
    return render(request, 'cards/report_paid_cards.html', context)


@login_required
def cancel_card(request, uid):
    try:
        if request.method == 'POST':
            card = get_object_or_404(Card, uid=uid)
            if not can_manage_record(request.user, card):
                messages.error(request, 'You do not have permission to cancel this card.')
                return redirect('manage_cards')

            # Check if cards is already cancelled
            if card.isCancel:
                messages.warning(request, f'Card {card.card_no} is already cancelled.')
                return redirect('manage_cards')
                
            # Update cards status
            card.isCancel = True
            card.cancel_reason = request.POST.get('cancel_reason', 'No reason provided')
            
            card._request_user = request.user
            card._request = request
            card._activity_message = f"Cancelled card {card.card_no} by {request.user.get_full_name() or request.user.username}"
            card.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(card).pk,
                object_id=card.pk,
                object_repr=force_str(card),
                action_flag=CHANGE,
                change_message=f"Cancelled card. Reason: {card.cancel_reason}"
            )
            
            messages.success(request, f'Card {card.card_no} has been cancelled successfully.')
            return redirect('manage_cards')
            
    except Exception as e:
        messages.error(request, f'Error cancelling card: {str(e)}')
        
    return redirect('manage_cards')


@login_required
def activate_card(request, uid):
    try:
        if request.method == 'POST':
            card = get_object_or_404(Card, uid=uid)
            if not can_manage_record(request.user, card):
                messages.error(request, 'You do not have permission to activate this card.')
                return redirect('cancelled_cards')

            # Check if cards is already active
            if card.isApprove and not card.isCancel:
                messages.warning(request, f'Card {card.card_no} is already active.')
                return redirect('cancelled_cards')
                
            # Update cards status
            card.isCancel = False
            activate_notes = request.POST.get('activate_notes', '')
            
            card._request_user = request.user
            card._request = request
            card._activity_message = f"Activated card {card.card_no} by {request.user.get_full_name() or request.user.username}"
            card.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(card).pk,
                object_id=card.pk,
                object_repr=force_str(card),
                action_flag=CHANGE,
                change_message=f"Activated card. Notes: {activate_notes}" if activate_notes else "Activated card"
            )
            
            messages.success(request, f'Card {card.card_no} has been activated successfully.')
            return redirect('cancelled_cards')
            
    except Exception as e:
        messages.error(request, f'Error activating card: {str(e)}')
        
    return redirect('cancelled_cards')

@login_required
def cancelled_cards(request):
    # Get the current logged-in user
    current_user = request.user
    total_cards = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    card_list = Card.objects.none()  # Default to an empty queryset

    # Check if the user is a superuser (admin)
    if current_user.is_superuser:
        # Base query for admin users
        card_list = Card.objects.filter(isCancel=True).order_by('-card_no')

        # Apply city filter if selected
        if selected_city:
            card_list = card_list.filter(user__profile__city__iexact=selected_city)

        # Apply search query if provided
        if searching_query:
            card_list = card_list.filter(
                Q(card_no__icontains=searching_query) |
                Q(company_name__icontains=searching_query)
            )

        total_cards = card_list.count()

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Cancel Cards',
        'cards': cards,
        'current_date': current_date,
        'total_cards': total_cards,
        'searching_query': searching_query,  # Include for pre-filling the input
        'sidebar_active': 'cancelled_cards',
    }
    return render(request, 'cards/cancelled_cards.html', context)


@login_required
def hold_card(request, uid):
    try:
        if request.method == 'POST':
            card = get_object_or_404(Card, uid=uid)
            if not can_manage_record(request.user, card):
                messages.error(request, 'You do not have permission to hold this card.')
                return redirect('manage_cards')

            if card.isHold:
                messages.warning(request, f'Card {card.card_no} is already on hold.')
                return redirect('manage_cards')
                
            card.isHold = True
            card.hold_reason = request.POST.get('hold_reason', 'No reason provided')
            card._request_user = request.user
            card._request = request
            card._activity_message = f"Card {card.card_no} put on hold by {request.user.get_full_name() or request.user.username}"
            card.save()
            
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(card).pk,
                object_id=card.pk,
                object_repr=force_str(card),
                action_flag=CHANGE,
                change_message=f"Card put on hold. Reason: {card.hold_reason}"
            )
            
            messages.success(request, f'Card {card.card_no} has been put on hold successfully.')
            return redirect('manage_cards')
            
    except Exception as e:
        messages.error(request, f'Error cancelling card: {str(e)}')
        
    return redirect('manage_cards')


@login_required
def unhold_card(request, uid):
    try:
        if request.method == 'POST':
            card = get_object_or_404(Card, uid=uid, isHold=True)
            if not can_manage_record(request.user, card):
                messages.error(request, 'You do not have permission to release this card from hold.')
                return redirect('holded_cards')

            # Update card status
            card.isHold = False
            activate_notes = request.POST.get('activate_notes', '')
            
            card._request_user = request.user
            card._request = request
            card._activity_message = f"Released hold on card {card.card_no} by {request.user.get_full_name() or request.user.username}"
            card.save()
            
            # Log the activity
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            from django.utils.encoding import force_str
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(card).pk,
                object_id=card.pk,
                object_repr=force_str(card),
                action_flag=CHANGE,
                change_message=f"Hold released. Notes: {activate_notes}" if activate_notes else "Hold released"
            )
            
            messages.success(request, f'Card {card.card_no} has been released from hold successfully.')
            return redirect('holded_cards')
            
    except Exception as e:
        messages.error(request, f'Error activating card: {str(e)}')
        
    return redirect('holded_cards')

@login_required
def holded_cards(request):
    # Get the current logged-in user
    current_user = request.user
    total_cards = 0

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    
    # Base query for cards on hold
    card_list = Card.objects.filter(isHold=True).order_by('-updated_at')

    # Apply city filter if selected
    if selected_city:
        card_list = card_list.filter(user__profile__city__iexact=selected_city)

    # Apply search query if provided
    if searching_query:
        card_list = card_list.filter(
            Q(card_no__icontains=searching_query) |
            Q(company_name__icontains=searching_query) |
            Q(operator_name__icontains=searching_query) |
            Q(iqama_no__icontains=searching_query)
        )

    total_cards = card_list.count()

    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')

    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Holded Cards',
        'cards': cards,
        'current_date': current_date,
        'total_cards': total_cards,
        'searching_query': searching_query,  # Include for pre-filling the input
        'sidebar_active': 'holded_cards',
    }
    return render(request, 'cards/holded_cards.html', context)


@login_required
def rejected_cards(request):
    """
    Rejected cards — previously invisible everywhere once isReject=True:
    excluded from Pending (on purpose), and not shown by Manage (isApprove
    required), Cancelled (isCancel) or Hold (isHold) either. This is the
    only place they can be found and restored.
    """
    current_user = request.user
    if not (current_user.is_superuser or current_user.is_staff):
        messages.error(request, 'You do not have permission to view rejected cards.')
        return redirect('index')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()

    manager_city = get_manager_city(current_user)
    if manager_city:
        selected_city = manager_city

    card_list = Card.objects.filter(isReject=True).order_by('-updated_at')
    if selected_city:
        card_list = card_list.filter(user__profile__city__iexact=selected_city)
    if searching_query:
        card_list = card_list.filter(
            Q(card_no__icontains=searching_query) |
            Q(company_name__icontains=searching_query) |
            Q(operator_name__icontains=searching_query) |
            Q(iqama_no__icontains=searching_query)
        )

    total_cards = card_list.count()
    paginator = Paginator(card_list, items_per_page)
    page = request.GET.get('page', '1')
    try:
        cards = paginator.page(int(page))
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)

    context = {
        'title': 'Rejected Cards',
        'cards': cards,
        'current_date': current_date,
        'total_cards': total_cards,
        'searching_query': searching_query,
        'manager_city': manager_city,
        'sidebar_active': 'rejected_cards',
    }
    return render(request, 'cards/rejected_cards.html', context)


@login_required
@require_POST
def restore_rejected_card(request, uid):
    """Move a rejected card back to Pending."""
    card = get_object_or_404(Card, uid=uid)
    if not can_manage_record(request.user, card):
        messages.error(request, 'You do not have permission to restore this card.')
        return redirect_back(request, 'rejected_cards')

    if not card.isReject:
        messages.warning(request, f'Card {card.card_no} is not rejected.')
        return redirect_back(request, 'rejected_cards')

    card.isReject = False
    card._request_user = request.user
    card._request = request
    approver = request.user.get_full_name() or request.user.username
    card._activity_message = f"Restored rejected card {card.card_no} to pending by {approver}"
    card.save()

    messages.success(request, f'Card {card.card_no} has been restored to Pending.')
    return redirect_back(request, 'rejected_cards')


@login_required
@require_POST
def delete_rejected_card(request, uid):
    """Permanently delete a rejected card after confirmation."""
    card = get_object_or_404(Card, uid=uid)
    if not can_manage_record(request.user, card):
        messages.error(request, 'You do not have permission to delete this card.')
        return redirect_back(request, 'rejected_cards')

    if not card.isReject:
        messages.warning(request, f'Card {card.card_no} is not rejected.')
        return redirect_back(request, 'rejected_cards')

    card_no = card.card_no
    card._request_user = request.user
    card._request = request
    card._activity_message = f"Permanently deleted rejected card {card_no} by {request.user.get_full_name() or request.user.username}"
    card.delete()

    messages.success(request, f'Card {card_no} has been permanently deleted.')
    return redirect_back(request, 'rejected_cards')
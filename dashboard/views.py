from datetime import datetime
from functools import reduce
from operator import or_

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render
from django.contrib import messages
from base.utils import current_date, items_per_page
from certificates.models import Certificate
from cards.models import Card
from ndt.models import NonDestructiveTesting
from training.models import Training
from calibration.models import Calibration
from django.shortcuts import redirect
from django.utils import timezone
from django.db.models import Count, Q, Sum


@login_required
def index(request):
    today = timezone.now().date()
    current_month = timezone.now().month
    current_user = request.user

    try:
        total_pending_certificates = Certificate.objects.filter(isApprove=False, isReject=False, isCancel=False, isHold=False).count()
        total_pending_cards = Card.objects.filter(isApprove=False, isReject=False, isCancel=False, isHold=False).count()
        total_pending_ndt = NonDestructiveTesting.objects.filter(isApprove=False, isReject=False, isCancel=False, isHold=False).count()
        total_pending_training = Training.objects.filter(isApprove=False, isReject=False, isCancel=False, isHold=False).count()
        total_pending_calibration = Calibration.objects.filter(isApprove=False, isReject=False, isCancel=False, isHold=False).count()

        if current_user.is_superuser:
            total_certificates = Certificate.objects.filter(isApprove=True).count()
            total_cards = Card.objects.filter(isApprove=True).count()
            total_ndt = NonDestructiveTesting.objects.filter(isApprove=True).count()
            total_training = Training.objects.filter(isApprove=True).count()
            total_calibration = Calibration.objects.filter(isApprove=True).count()

            today_certificates = Certificate.objects.filter(created_at__date=today, isApprove=True).count()
            today_cards = Card.objects.filter(created_at__date=today, isApprove=True).count()
            today_ndt = NonDestructiveTesting.objects.filter(created_at__date=today, isApprove=True).count()
            today_training = Training.objects.filter(created_at__date=today, isApprove=True).count()
            today_calibration = Calibration.objects.filter(created_at__date=today, isApprove=True).count()

            month_certificates = Certificate.objects.filter(created_at__month=current_month, isApprove=True).count()
            month_cards = Card.objects.filter(created_at__month=current_month, isApprove=True).count()
            month_ndt = NonDestructiveTesting.objects.filter(created_at__month=current_month, isApprove=True).count()
            month_training = Training.objects.filter(created_at__month=current_month, isApprove=True).count()
            month_calibration = Calibration.objects.filter(created_at__month=current_month, isApprove=True).count()

            # Get user activity — 10 queries total regardless of user count
            thirty_days_ago = today - timezone.timedelta(days=30)

            today_per_user = {}
            last30_per_user = {}
            for model in [Certificate, Card, NonDestructiveTesting, Training, Calibration]:
                for uid, cnt in (model.objects
                                 .filter(created_at__date=today)
                                 .values('user')
                                 .annotate(cnt=Count('uid'))
                                 .values_list('user', 'cnt')):
                    today_per_user[uid] = today_per_user.get(uid, 0) + cnt

                for uid, cnt in (model.objects
                                 .filter(created_at__date__gte=thirty_days_ago)
                                 .values('user')
                                 .annotate(cnt=Count('uid'))
                                 .values_list('user', 'cnt')):
                    last30_per_user[uid] = last30_per_user.get(uid, 0) + cnt

            from django.contrib.auth import get_user_model
            User = get_user_model()
            active_ids = set(today_per_user) | set(last30_per_user)
            username_map = dict(User.objects.filter(id__in=active_ids, is_active=True).values_list('id', 'username'))

            user_activity = [
                {
                    'username': username_map[uid],
                    'today_count': today_per_user.get(uid, 0),
                    'last_30_days_count': last30_per_user.get(uid, 0),
                }
                for uid in active_ids
                if uid in username_map
            ]
            user_activity.sort(key=lambda x: x['today_count'], reverse=True)

            max_entries = max(1, max((a['last_30_days_count'] for a in user_activity), default=1))
            for activity in user_activity:
                activity['activity_percent'] = min(100, int((activity['last_30_days_count'] / max_entries) * 100))

        else:
            total_certificates = Certificate.objects.filter(user=current_user, isApprove=True).count()
            total_cards = Card.objects.filter(user=current_user, isApprove=True).count()
            total_ndt = NonDestructiveTesting.objects.filter(user=current_user, isApprove=True).count()
            total_training = Training.objects.filter(user=current_user, isApprove=True).count()
            total_calibration = Calibration.objects.filter(user=current_user, isApprove=True).count()

            today_certificates = Certificate.objects.filter(user=current_user, created_at__date=today, isApprove=True).count()
            today_cards = Card.objects.filter(user=current_user, created_at__date=today, isApprove=True).count()
            today_ndt = NonDestructiveTesting.objects.filter(user=current_user, created_at__date=today, isApprove=True).count()
            today_training = Training.objects.filter(user=current_user, created_at__date=today, isApprove=True).count()
            today_calibration = Calibration.objects.filter(user=current_user, created_at__date=today, isApprove=True).count()

            month_certificates = Certificate.objects.filter(user=current_user, created_at__month=current_month, isApprove=True).count()
            month_cards = Card.objects.filter(user=current_user, created_at__month=current_month, isApprove=True).count()
            month_ndt = NonDestructiveTesting.objects.filter(user=current_user, created_at__month=current_month, isApprove=True).count()
            month_training = Training.objects.filter(user=current_user, created_at__month=current_month, isApprove=True).count()
            month_calibration = Calibration.objects.filter(user=current_user, created_at__month=current_month, isApprove=True).count()

    except Exception as e:
        messages.error(request, f"Error loading dashboard data: {e}")
        total_pending_certificates = total_pending_cards = total_pending_ndt = total_pending_training = total_pending_calibration = 0
        total_certificates = total_cards = total_ndt = total_training = total_calibration = 0
        today_certificates = today_cards = today_ndt = today_training = today_calibration = 0
        month_certificates = month_cards = month_ndt = month_training = month_calibration = 0

    context = {
        'page_name': 'Dashboard',
        'sidebar_active': 'dashboard',
        'current_date': today,
        'total_pending_certificates': total_pending_certificates,
        'total_pending_cards': total_pending_cards,
        'total_pending_ndt': total_pending_ndt,
        'total_pending_training': total_pending_training,
        'total_pending_calibration': total_pending_calibration,
        'total_certificates': total_certificates,
        'total_cards': total_cards,
        'total_ndt': total_ndt,
        'total_training': total_training,
        'total_calibration': total_calibration,
        'today_certificates': today_certificates,
        'today_cards': today_cards,
        'today_ndt': today_ndt,
        'today_training': today_training,
        'today_calibration': today_calibration,
        'month_certificates': month_certificates,
        'month_cards': month_cards,
        'month_ndt': month_ndt,
        'month_training': month_training,
        'month_calibration': month_calibration,
        'user_activity': user_activity if current_user.is_superuser else [],
    }

    return render(request, 'dashboard/index.html', context)


UNIVERSAL_MODULES = {
    'certificate': (Certificate, 'Certificate', ['cert_no'], 'Certificate No', 'update_certificate'),
    'card': (Card, 'Card', ['card_no'], 'Card No', 'update_card'),
    'training': (Training, 'Training', ['card_no', 'cert_no'], 'Card/Cert No', 'update_training'),
    'ndt': (NonDestructiveTesting, 'NDT', ['report_no'], 'Report No', 'update_ndt'),
    'calibration': (Calibration, 'Calibration', ['cert_no'], 'Cert No', 'update_calibration'),
}

UNIVERSAL_STATUS_FILTERS = {
    'pending': {'isApprove': False, 'isReject': False, 'isCancel': False, 'isHold': False},
    'approved': {'isApprove': True, 'isCancel': False},
    'rejected': {'isReject': True},
    'cancelled': {'isCancel': True},
    'held': {'isHold': True},
}


@login_required
def universal_records(request):
    """
    Superuser-only combined view across all 5 modules (Certificates, Cards,
    Training, NDT, Calibration), normalized to a common set of columns, with
    search/city/module/status filters.
    """
    current_user = request.user
    if not current_user.is_superuser:
        messages.error(request, 'You do not have permission to view universal records.')
        return redirect('index')

    searching_query = request.GET.get('searching_query', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_module = request.GET.get('module', '').strip()
    selected_status = request.GET.get('status', '').strip()

    modules_to_query = [selected_module] if selected_module in UNIVERSAL_MODULES else list(UNIVERSAL_MODULES.keys())

    records = []
    for key in modules_to_query:
        model, label, number_fields, number_label, update_url_name = UNIVERSAL_MODULES[key]
        qs = model.objects.select_related('user__profile').all()

        if selected_status in UNIVERSAL_STATUS_FILTERS:
            qs = qs.filter(**UNIVERSAL_STATUS_FILTERS[selected_status])
        if selected_city:
            qs = qs.filter(user__profile__city__iexact=selected_city)
        if searching_query:
            number_lookups = [Q(**{f'{f}__icontains': searching_query}) for f in number_fields]
            search_q = reduce(or_, number_lookups)
            search_q |= Q(company_name__icontains=searching_query)
            search_q |= Q(requested_by__icontains=searching_query)
            search_q |= Q(invoice_no__icontains=searching_query)
            qs = qs.filter(search_q)

        for obj in qs:
            if obj.isReject:
                status_label, status_class = 'Rejected', 'danger'
            elif obj.isCancel:
                status_label, status_class = 'Cancelled', 'dark'
            elif obj.isHold:
                status_label, status_class = 'Hold', 'warning'
            elif obj.isApprove:
                status_label, status_class = 'Approved', 'success'
            else:
                status_label, status_class = 'Pending', 'info'

            number_value = next((getattr(obj, f) for f in number_fields if getattr(obj, f, None)), '-')

            records.append({
                'module_label': label,
                'module_key': key,
                'number': number_value,
                'number_label': number_label,
                'company_name': obj.company_name,
                'requested_by': obj.requested_by,
                'total_amount': obj.total_amount,
                'amount': obj.amount,
                'city': obj.city,
                'status_label': status_label,
                'status_class': status_class,
                'created_at': obj.created_at,
                'uid': obj.uid,
                'update_url_name': update_url_name,
            })

    records.sort(key=lambda r: r['created_at'], reverse=True)
    total_records = len(records)

    paginator = Paginator(records, items_per_page)
    page = request.GET.get('page', '1')
    try:
        page_records = paginator.page(int(page))
    except (PageNotAnInteger, ValueError):
        page_records = paginator.page(1)
    except EmptyPage:
        page_records = paginator.page(paginator.num_pages)

    context = {
        'title': 'Universal Records',
        'page_name': 'Universal Records',
        'sidebar_active': 'universal_records',
        'page_records': page_records,
        'total_records': total_records,
        'searching_query': searching_query,
        'selected_city': selected_city,
        'selected_module': selected_module,
        'selected_status': selected_status,
        'modules': UNIVERSAL_MODULES,
    }
    return render(request, 'dashboard/universal_records.html', context)


@login_required
def upload_all_data(request):
    import pandas as pd
    from decimal import Decimal, InvalidOperation
    import os
    from django.conf import settings
    from datetime import datetime

    if request.method == 'POST':
        file = request.FILES.get('file')

        if not file.name.endswith(('.xls', '.xlsx')):
            messages.error(request, 'Invalid file format. Please upload an Excel file.')
            return redirect('index')

        xl = pd.ExcelFile(file)
        log_data = {}
        results = []

        def clean(val):
            if pd.isna(val):
                return ''
            val_str = str(val).strip()
            return val_str[:-2] if val_str.endswith('.0') else val_str

        def parse_date(date_val):
            if pd.isna(date_val) or not date_val:
                return None
            if isinstance(date_val, (datetime, pd.Timestamp)):
                return date_val.date()
            date_str = str(date_val).strip()
            formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%b-%y', '%d-%b-%Y', '%d/%m/%y', '%d-%m-%y']
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            try:
                return pd.to_datetime(date_str, dayfirst=False).date()
            except Exception:
                raise ValueError(f"Date format for '{date_val}' is not supported.")

        def process_training_sheet(sheet_name, model, field_map):
            if sheet_name not in xl.sheet_names:
                return f"❌ Sheet '{sheet_name}' missing."

            data = pd.read_excel(file, sheet_name=sheet_name).fillna('')
            created = skipped = 0
            log_data[sheet_name] = []
            date_fields = ['inspection_date', 'expiry_date', 'issue_date', 'received_on', 'date_of_calibration']

            cert_index = next((i for i, f in field_map.items() if f == 'cert_no'), None)
            card_index = next((i for i, f in field_map.items() if f == 'card_no'), None)
            existing_cert_nos = set(model.objects.values_list('cert_no', flat=True))
            existing_card_nos = set(model.objects.values_list('card_no', flat=True))
            seen_cert_nos = set()
            seen_card_nos = set()
            to_create = []

            # First pass: insert by cert_no
            for index, row in data.iterrows():
                # Read and clean values
                cert_val = clean(row.iloc[cert_index]) if cert_index is not None else ''
                if cert_val == '':
                    cert_val = None
                card_val = clean(row.iloc[card_index]) if card_index is not None else ''
                if card_val == '':
                    card_val = None

                # Condition 4 – Skip if both cert_no and card_no are missing
                if not cert_val and not card_val:
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Skipped – Both cert_no and card_no are missing")
                    continue
                # Condition 2 and 1 (handled in pass 1) – cert_no must be available
                if not cert_val or cert_val in existing_cert_nos or cert_val in seen_cert_nos:
                    skipped += 1
                    if not cert_val:
                        log_data[sheet_name].append(f"Row {index + 2}: Skipped – Missing cert_no (Case C or D)")
                    else:
                        log_data[sheet_name].append(f"Row {index + 2}: Skipped – Duplicate cert_no '{cert_val}' (Case C or D)")
                    continue
                # Condition 1 – Skip if card_no already used
                if card_val in seen_card_nos or card_val in existing_card_nos:
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Skipped card_no (in cert_no pass) – '{card_val}'")
                    continue

                obj_data = {'user': request.user}
                for i, field in field_map.items():
                    cell_value = clean(row.iloc[i])
                    if field in date_fields:
                        try:
                            obj_data[field] = parse_date(cell_value)
                        except ValueError:
                            log_data[sheet_name].append(f"Row {index + 2}: Invalid date in field '{field}' – '{cell_value}'")
                            obj_data[field] = None
                    elif field in ['amount', 'total_amount']:
                        try:
                            obj_data[field] = Decimal(cell_value) if cell_value else Decimal('0')
                        except InvalidOperation:
                            log_data[sheet_name].append(f"Row {index + 2}: Invalid decimal in field '{field}' – '{cell_value}'")
                            obj_data[field] = Decimal('0')
                    else:
                        if field == 'cert_no' and cell_value == '':
                            obj_data[field] = None
                        else:
                            obj_data[field] = cell_value

                to_create.append(model(**obj_data))
                seen_cert_nos.add(cert_val)
                seen_card_nos.add(card_val)
                created += 1

            # 🚨 Remove any remaining duplicates by cert_no or card_no before insert
            unique_cert_nos = set()
            unique_card_nos = set()
            final_batch = []
            for obj in to_create:
                c_no = getattr(obj, 'cert_no', None)
                card = getattr(obj, 'card_no', None)
                if (c_no and c_no in unique_cert_nos) or (card and card in unique_card_nos):
                    skipped += 1
                    log_data[sheet_name].append(
                        f"Skipped duplicate in final batch: cert_no={c_no or 'NULL'}, card_no={card or 'NULL'}"
                    )
                    continue

                if c_no: unique_cert_nos.add(c_no)
                if card: unique_card_nos.add(card)
                final_batch.append(obj)

            try:
                model.objects.bulk_create(final_batch, batch_size=1000)
            except Exception as e:
                log_data[sheet_name].append(f"❌ Bulk insert failed: {str(e)}")

            # Second pass: insert remaining by card_no
            to_create.clear()
            for index, row in data.iterrows():
                # Read and clean values
                cert_val = clean(row.iloc[cert_index]) if cert_index is not None else ''
                if cert_val == '':
                    cert_val = None
                card_val = clean(row.iloc[card_index]) if card_index is not None else ''
                if card_val == '':
                    card_val = None

                # Condition 4 – Skip if both cert_no and card_no are missing
                if not cert_val and not card_val:
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Skipped – Both cert_no and card_no are missing")
                    continue
                if not card_val or card_val in existing_card_nos or card_val in seen_card_nos:
                    skipped += 1
                    if not card_val:
                        log_data[sheet_name].append(f"Row {index + 2}: Skipped – Missing card_no (Case B or D)")
                    else:
                        log_data[sheet_name].append(f"Row {index + 2}: Skipped – Duplicate card_no '{card_val}' (Case B or D)")
                    continue
                if cert_val in seen_cert_nos:
                    continue

                if any(card_val == getattr(obj, 'card_no', None) for obj in to_create):
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Skipped duplicate card_no inside batch – '{card_val}'")
                    continue

                obj_data = {'user': request.user}
                for i, field in field_map.items():
                    cell_value = clean(row.iloc[i])
                    if field in date_fields:
                        try:
                            obj_data[field] = parse_date(cell_value)
                        except ValueError:
                            log_data[sheet_name].append(f"Row {index + 2}: Invalid date in field '{field}' – '{cell_value}'")
                            obj_data[field] = None
                    elif field in ['amount', 'total_amount']:
                        try:
                            obj_data[field] = Decimal(cell_value) if cell_value else Decimal('0')
                        except InvalidOperation:
                            log_data[sheet_name].append(f"Row {index + 2}: Invalid decimal in field '{field}' – '{cell_value}'")
                            obj_data[field] = Decimal('0')
                    else:
                        if field == 'cert_no' and cell_value == '':
                            obj_data[field] = None
                        else:
                            obj_data[field] = cell_value

                to_create.append(model(**obj_data))
                seen_card_nos.add(card_val)
                created += 1

            # 🚨 Remove any remaining duplicates by cert_no or card_no before insert
            unique_cert_nos = set()
            unique_card_nos = set()
            final_batch = []
            for obj in to_create:
                c_no = getattr(obj, 'cert_no', None)
                card = getattr(obj, 'card_no', None)
                if (c_no and c_no in unique_cert_nos) or (card and card in unique_card_nos):
                    skipped += 1
                    log_data[sheet_name].append(
                        f"Skipped duplicate in final batch: cert_no={c_no or 'NULL'}, card_no={card or 'NULL'}"
                    )
                    continue
                if c_no: unique_cert_nos.add(c_no)
                if card: unique_card_nos.add(card)
                final_batch.append(obj)

            try:
                model.objects.bulk_create(final_batch, batch_size=1000)
            except Exception as e:
                log_data[sheet_name].append(f"❌ Bulk insert failed: {str(e)}")
            return f"✅ {sheet_name}: Imported {created}, Skipped {skipped}"

        def process_generic_sheet(sheet_name, model, unique_index, field_map):
            if sheet_name not in xl.sheet_names:
                return f"❌ Sheet '{sheet_name}' missing."

            data = pd.read_excel(file, sheet_name=sheet_name).fillna('')
            created = skipped = 0
            log_data[sheet_name] = []
            to_create = []
            seen_unique_vals = set()
            date_fields = ['inspection_date', 'expiry_date', 'issue_date', 'received_on', 'date_of_calibration']

            field_name = field_map[unique_index]

            for index, row in data.iterrows():
                unique_val = clean(row.iloc[unique_index])

                if not unique_val:
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Skipped – Missing unique '{field_name}'")
                    continue
                if unique_val in seen_unique_vals:
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Duplicate in sheet – {field_name}='{unique_val}'")
                    continue
                if model.objects.filter(**{field_name: unique_val}).exists():
                    skipped += 1
                    log_data[sheet_name].append(f"Row {index + 2}: Already in DB – {field_name}='{unique_val}'")
                    continue
                seen_unique_vals.add(unique_val)

                obj_data = {'user': request.user}
                for i, field in field_map.items():
                    cell_value = clean(row.iloc[i])
                    if field in date_fields:
                        try:
                            obj_data[field] = parse_date(cell_value)
                        except ValueError:
                            log_data[sheet_name].append(f"Row {index + 2}: Invalid date in field '{field}' – '{cell_value}'")
                            obj_data[field] = None
                    elif field in ['amount', 'total_amount']:
                        try:
                            obj_data[field] = Decimal(cell_value) if cell_value else Decimal('0')
                        except InvalidOperation:
                            log_data[sheet_name].append(f"Row {index + 2}: Invalid decimal in field '{field}' – '{cell_value}'")
                            obj_data[field] = Decimal('0')
                    else:
                        if field == 'cert_no' and cell_value == '':
                            obj_data[field] = None
                        else:
                            obj_data[field] = cell_value

                to_create.append(model(**obj_data))
                created += 1

            model.objects.bulk_create(to_create, batch_size=1000)
            return f"✅ {sheet_name}: Imported {created}, Skipped {skipped}"

        from certificates.models import Certificate
        from cards.models import Card
        from training.models import Training
        from ndt.models import NonDestructiveTesting
        from calibration.models import Calibration

        results.append(process_generic_sheet('Certificates', Certificate, 2, {
            0: 'sr_no', 1: 'lh_serial_no', 2: 'cert_no', 3: 'sticker_no', 4: 'eq_serial_no', 5: 'equipment_type',
            6: 'company_name', 7: 'inspection_date', 8: 'expiry_date', 9: 'remaining_months', 10: 'plate_no',
            11: 'manufacturer', 12: 'inspected_by', 13: 'status', 14: 'note', 15: 'prepared_by',
            16: 'wasted_serial', 17: 'invoice_no', 18: 'amount', 19: 'cash_bank', 20: 'client_rep_name',
            21: 'client_rep_number', 22: 'email', 23: 'remarks'
        }))

        results.append(process_generic_sheet('Cards', Card, 1, {
            0: 'sr_no', 1: 'card_no', 2: 'iqama_no', 3: 'operator_name', 4: 'company_name', 5: 'issue_date',
            6: 'expiry_date', 7: 'remaining_months', 8: 'trade', 9: 'holo_gram_no', 10: 'assessed_by',
            11: 'status', 12: 'note', 13: 'wasted_serial', 14: 'requested_by', 15: 'prepared_by',
            16: 'invoice_no', 17: 'amount', 18: 'cash_bank', 19: 'client_rep_name', 20: 'client_rep_number',
            21: 'email', 22: 'remarks'
        }))

        results.append(process_training_sheet('Training', Training, {
            0: 'sr_no', 1: 'card_no', 2: 'cert_no', 3: 'name_of_trainee', 4: 'company_name', 5: 'iqama_no',
            6: 'issue_date', 7: 'expiry_date', 8: 'remaining_months', 9: 'trade', 10: 'holo_gram_no',
            11: 'assessed_by_resource_person', 12: 'status', 13: 'note', 14: 'wasted_serial', 15: 'requested_by',
            16: 'prepared_by', 17: 'invoice_no', 18: 'amount', 19: 'cash_bank', 20: 'client_rep_name',
            21: 'client_rep_number', 22: 'email', 23: 'remarks'
        }))

        results.append(process_generic_sheet('NDT', NonDestructiveTesting, 2, {
            0: 'sr_no', 1: 'lh_serial_no', 2: 'report_no', 3: 'id_serial_no', 4: 'material', 5: 'structure_description',
            6: 'inspection_type', 7: 'inspection_date', 8: 'expiry_date', 9: 'remaining_months', 10: 'company_name',
            11: 'joint_type', 12: 'inspected_by', 13: 'status', 14: 'note', 15: 'prepared_by', 16: 'wasted_serial',
            17: 'approved_by', 18: 'received_by', 19: 'invoice_no', 20: 'amount', 21: 'cash_bank', 22: 'client_rep_name',
            23: 'client_rep_number', 24: 'email', 25: 'remarks'
        }))

        results.append(process_generic_sheet('Calibration', Calibration, 2, {
            0: 'sr_no', 1: 'lh_serial_no', 2: 'cert_no', 3: 'sticker_no', 4: 'equipment_name',
            5: 'company_name', 6: 'received_on', 7: 'technician', 8: 'date_of_calibration',
            9: 'expiry_date', 10: 'validity', 11: 'status', 12: 'note', 13: 'prepared_by',
            14: 'wasted_serial', 15: 'invoice_no', 16: 'amount', 17: 'cash_bank', 18: 'client_rep_name',
            19: 'client_rep_number', 20: 'email', 21: 'remarks'
        }))

        # Write skipped logs to file
        log_file_path = os.path.join(settings.MEDIA_ROOT, 'import_logs.txt')
        with open(log_file_path, 'w', encoding='utf-8') as f:
            for sheet, logs in log_data.items():
                if logs:
                    f.write(f"Sheet: {sheet}\n")
                    for entry in logs:
                        f.write(f"  - {entry}\n")
                    f.write("\n")

        for result in results:
            messages.success(request, f"{result} ✅ Upload complete.")

        messages.info(request, "⚠️ Some rows were skipped. Log saved as 'import_logs.txt' in media folder.")
        return redirect('index')

    return redirect('index')


# Orignal Extra code
# @login_required
# def upload_all_data(request):
#     import pandas as pd
#     from decimal import Decimal, InvalidOperation
#     import os
#     from django.conf import settings
#     from datetime import datetime
#
#     if request.method == 'POST':
#         file = request.FILES.get('file')
#
#         if not file.name.endswith(('.xls', '.xlsx')):
#             messages.error(request, 'Invalid file format. Please upload an Excel file.')
#             return redirect('index')
#
#         xl = pd.ExcelFile(file)
#         log_data = {}
#         results = []
#
#         def clean(val):
#             if pd.isna(val):
#                 return ''
#             val_str = str(val).strip()
#             return val_str[:-2] if val_str.endswith('.0') else val_str
#
#         def parse_date(date_val):
#             if pd.isna(date_val) or not date_val:
#                 return None
#             if isinstance(date_val, (datetime, pd.Timestamp)):
#                 return date_val.date()
#             date_str = str(date_val).strip()
#             formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%b-%y', '%d-%b-%Y', '%d/%m/%y', '%d-%m-%y']
#             for fmt in formats:
#                 try:
#                     return datetime.strptime(date_str, fmt).date()
#                 except ValueError:
#                     continue
#             try:
#                 return pd.to_datetime(date_str, dayfirst=False).date()
#             except Exception:
#                 raise ValueError(f"Date format for '{date_val}' is not supported.")
#
#         def process_training_sheet(sheet_name, model, field_map):
#             if sheet_name not in xl.sheet_names:
#                 return f"❌ Sheet '{sheet_name}' missing."
#
#             data = pd.read_excel(file, sheet_name=sheet_name).fillna('')
#             created = skipped = 0
#             log_data[sheet_name] = []
#             date_fields = ['inspection_date', 'expiry_date', 'issue_date', 'received_on', 'date_of_calibration']
#
#             cert_index = next((i for i, f in field_map.items() if f == 'cert_no'), None)
#             card_index = next((i for i, f in field_map.items() if f == 'card_no'), None)
#             existing_cert_nos = set(model.objects.values_list('cert_no', flat=True))
#             existing_card_nos = set(model.objects.values_list('card_no', flat=True))
#             seen_cert_nos = set()
#             seen_card_nos = set()
#             to_create = []
#
#             # First pass: insert by cert_no
#             for index, row in data.iterrows():
#                 cert_val = clean(row.iloc[cert_index]) if cert_index is not None else ''
#                 if cert_val == '':
#                     cert_val = None
#                 card_val = clean(row.iloc[card_index]) if card_index is not None else ''
#                 if not cert_val or cert_val in existing_cert_nos or cert_val in seen_cert_nos:
#                     skipped += 1
#                     if not cert_val:
#                         log_data[sheet_name].append(f"Row {index + 2}: Skipped – Missing cert_no (Case C or D)")
#                     else:
#                         log_data[sheet_name].append(f"Row {index + 2}: Skipped – Duplicate cert_no '{cert_val}' (Case C or D)")
#                     continue
#
#                 if card_val in seen_card_nos or card_val in existing_card_nos:
#                     skipped += 1
#                     log_data[sheet_name].append(f"Row {index + 2}: Skipped card_no (in cert_no pass) – '{card_val}'")
#                     continue
#
#                 obj_data = {'user': request.user}
#                 for i, field in field_map.items():
#                     cell_value = clean(row.iloc[i])
#                     if field in date_fields:
#                         try:
#                             obj_data[field] = parse_date(cell_value)
#                         except ValueError:
#                             log_data[sheet_name].append(f"Row {index + 2}: Invalid date in field '{field}' – '{cell_value}'")
#                             obj_data[field] = None
#                     elif field in ['amount', 'total_amount']:
#                         try:
#                             obj_data[field] = Decimal(cell_value) if cell_value else Decimal('0')
#                         except InvalidOperation:
#                             log_data[sheet_name].append(f"Row {index + 2}: Invalid decimal in field '{field}' – '{cell_value}'")
#                             obj_data[field] = Decimal('0')
#                     else:
#                         if field == 'cert_no' and cell_value == '':
#                             obj_data[field] = None
#                         else:
#                             obj_data[field] = cell_value
#
#                 to_create.append(model(**obj_data))
#                 seen_cert_nos.add(cert_val)
#                 seen_card_nos.add(card_val)
#                 created += 1
#
#             # 🚨 Remove any remaining duplicates by cert_no or card_no before insert
#             unique_cert_nos = set()
#             unique_card_nos = set()
#             final_batch = []
#             for obj in to_create:
#                 c_no = getattr(obj, 'cert_no', None)
#                 card = getattr(obj, 'card_no', None)
#                 if (c_no and c_no in unique_cert_nos) or (card and card in unique_card_nos):
#                     skipped += 1
#                     log_data[sheet_name].append(
#                         f"Skipped duplicate in final batch: cert_no={c_no or 'NULL'}, card_no={card or 'NULL'}"
#                     )
#                     continue
#
#                 if c_no: unique_cert_nos.add(c_no)
#                 if card: unique_card_nos.add(card)
#                 final_batch.append(obj)
#
#             try:
#                 model.objects.bulk_create(final_batch, batch_size=1000)
#             except Exception as e:
#                 log_data[sheet_name].append(f"❌ Bulk insert failed: {str(e)}")
#
#             # Second pass: insert remaining by card_no
#             to_create.clear()
#             for index, row in data.iterrows():
#                 cert_val = clean(row.iloc[cert_index]) if cert_index is not None else ''
#                 if cert_val == '':
#                     cert_val = None
#                 card_val = clean(row.iloc[card_index]) if card_index is not None else ''
#                 if not card_val or card_val in existing_card_nos or card_val in seen_card_nos:
#                     skipped += 1
#                     if not card_val:
#                         log_data[sheet_name].append(f"Row {index + 2}: Skipped – Missing card_no (Case B or D)")
#                     else:
#                         log_data[sheet_name].append(f"Row {index + 2}: Skipped – Duplicate card_no '{card_val}' (Case B or D)")
#                     continue
#                 if cert_val in seen_cert_nos:
#                     continue
#
#                 if any(card_val == getattr(obj, 'card_no', None) for obj in to_create):
#                     skipped += 1
#                     log_data[sheet_name].append(f"Row {index + 2}: Skipped duplicate card_no inside batch – '{card_val}'")
#                     continue
#
#                 obj_data = {'user': request.user}
#                 for i, field in field_map.items():
#                     cell_value = clean(row.iloc[i])
#                     if field in date_fields:
#                         try:
#                             obj_data[field] = parse_date(cell_value)
#                         except ValueError:
#                             log_data[sheet_name].append(f"Row {index + 2}: Invalid date in field '{field}' – '{cell_value}'")
#                             obj_data[field] = None
#                     elif field in ['amount', 'total_amount']:
#                         try:
#                             obj_data[field] = Decimal(cell_value) if cell_value else Decimal('0')
#                         except InvalidOperation:
#                             log_data[sheet_name].append(f"Row {index + 2}: Invalid decimal in field '{field}' – '{cell_value}'")
#                             obj_data[field] = Decimal('0')
#                     else:
#                         if field == 'cert_no' and cell_value == '':
#                             obj_data[field] = None
#                         else:
#                             obj_data[field] = cell_value
#
#                 to_create.append(model(**obj_data))
#                 seen_card_nos.add(card_val)
#                 created += 1
#
#             # 🚨 Remove any remaining duplicates by cert_no or card_no before insert
#             unique_cert_nos = set()
#             unique_card_nos = set()
#             final_batch = []
#             for obj in to_create:
#                 c_no = getattr(obj, 'cert_no', None)
#                 card = getattr(obj, 'card_no', None)
#                 if (c_no and c_no in unique_cert_nos) or (card and card in unique_card_nos):
#                     skipped += 1
#                     log_data[sheet_name].append(
#                         f"Skipped duplicate in final batch: cert_no={c_no or 'NULL'}, card_no={card or 'NULL'}"
#                     )
#                     continue
#                 if c_no: unique_cert_nos.add(c_no)
#                 if card: unique_card_nos.add(card)
#                 final_batch.append(obj)
#
#             try:
#                 model.objects.bulk_create(final_batch, batch_size=1000)
#             except Exception as e:
#                 log_data[sheet_name].append(f"❌ Bulk insert failed: {str(e)}")
#             return f"✅ {sheet_name}: Imported {created}, Skipped {skipped}"
#
#         def process_generic_sheet(sheet_name, model, unique_index, field_map):
#             if sheet_name not in xl.sheet_names:
#                 return f"❌ Sheet '{sheet_name}' missing."
#
#             data = pd.read_excel(file, sheet_name=sheet_name).fillna('')
#             created = skipped = 0
#             log_data[sheet_name] = []
#             to_create = []
#             seen_unique_vals = set()
#             date_fields = ['inspection_date', 'expiry_date', 'issue_date', 'received_on', 'date_of_calibration']
#
#             field_name = field_map[unique_index]
#
#             for index, row in data.iterrows():
#                 unique_val = clean(row.iloc[unique_index])
#
#                 if not unique_val:
#                     skipped += 1
#                     log_data[sheet_name].append(f"Row {index + 2}: Skipped – Missing unique '{field_name}'")
#                     continue
#                 if unique_val in seen_unique_vals:
#                     skipped += 1
#                     log_data[sheet_name].append(f"Row {index + 2}: Duplicate in sheet – {field_name}='{unique_val}'")
#                     continue
#                 if model.objects.filter(**{field_name: unique_val}).exists():
#                     skipped += 1
#                     log_data[sheet_name].append(f"Row {index + 2}: Already in DB – {field_name}='{unique_val}'")
#                     continue
#                 seen_unique_vals.add(unique_val)
#
#                 obj_data = {'user': request.user}
#                 for i, field in field_map.items():
#                     cell_value = clean(row.iloc[i])
#                     if field in date_fields:
#                         try:
#                             obj_data[field] = parse_date(cell_value)
#                         except ValueError:
#                             log_data[sheet_name].append(f"Row {index + 2}: Invalid date in field '{field}' – '{cell_value}'")
#                             obj_data[field] = None
#                     elif field in ['amount', 'total_amount']:
#                         try:
#                             obj_data[field] = Decimal(cell_value) if cell_value else Decimal('0')
#                         except InvalidOperation:
#                             log_data[sheet_name].append(f"Row {index + 2}: Invalid decimal in field '{field}' – '{cell_value}'")
#                             obj_data[field] = Decimal('0')
#                     else:
#                         if field == 'cert_no' and cell_value == '':
#                             obj_data[field] = None
#                         else:
#                             obj_data[field] = cell_value
#
#                 to_create.append(model(**obj_data))
#                 created += 1
#
#             model.objects.bulk_create(to_create, batch_size=1000)
#             return f"✅ {sheet_name}: Imported {created}, Skipped {skipped}"
#
#         from certificates.models import Certificate
#         from cards.models import Card
#         from training.models import Training
#         from ndt.models import NonDestructiveTesting
#         from calibration.models import Calibration
#
#         # results.append(process_generic_sheet('Certificates', Certificate, 2, {
#         #     0: 'sr_no', 1: 'lh_serial_no', 2: 'cert_no', 3: 'sticker_no', 4: 'eq_serial_no', 5: 'equipment_type',
#         #     6: 'company_name', 7: 'inspection_date', 8: 'expiry_date', 9: 'remaining_months', 10: 'plate_no',
#         #     11: 'manufacturer', 12: 'inspected_by', 13: 'status', 14: 'note', 15: 'prepared_by',
#         #     16: 'wasted_serial', 17: 'invoice_no', 18: 'amount', 19: 'cash_bank', 20: 'client_rep_name',
#         #     21: 'client_rep_number', 22: 'email', 23: 'remarks'
#         # }))
#         #
#         # results.append(process_generic_sheet('Cards', Card, 1, {
#         #     0: 'sr_no', 1: 'card_no', 2: 'iqama_no', 3: 'operator_name', 4: 'company_name', 5: 'issue_date',
#         #     6: 'expiry_date', 7: 'remaining_months', 8: 'trade', 9: 'holo_gram_no', 10: 'assessed_by',
#         #     11: 'status', 12: 'note', 13: 'wasted_serial', 14: 'requested_by', 15: 'prepared_by',
#         #     16: 'invoice_no', 17: 'amount', 18: 'cash_bank', 19: 'client_rep_name', 20: 'client_rep_number',
#         #     21: 'email', 22: 'remarks'
#         # }))
#
#         results.append(process_training_sheet('Training', Training, {
#             0: 'sr_no', 1: 'card_no', 2: 'cert_no', 3: 'name_of_trainee', 4: 'company_name', 5: 'iqama_no',
#             6: 'issue_date', 7: 'expiry_date', 8: 'remaining_months', 9: 'trade', 10: 'holo_gram_no',
#             11: 'assessed_by_resource_person', 12: 'status', 13: 'note', 14: 'wasted_serial', 15: 'requested_by',
#             16: 'prepared_by', 17: 'invoice_no', 18: 'amount', 19: 'cash_bank', 20: 'client_rep_name',
#             21: 'client_rep_number', 22: 'email', 23: 'remarks'
#         }))
#
#         # results.append(process_generic_sheet('NDT', NonDestructiveTesting, 2, {
#         #     0: 'sr_no', 1: 'lh_serial_no', 2: 'report_no', 3: 'id_serial_no', 4: 'material', 5: 'structure_description',
#         #     6: 'inspection_type', 7: 'inspection_date', 8: 'expiry_date', 9: 'remaining_months', 10: 'company_name',
#         #     11: 'joint_type', 12: 'inspected_by', 13: 'status', 14: 'note', 15: 'prepared_by', 16: 'wasted_serial',
#         #     17: 'approved_by', 18: 'received_by', 19: 'invoice_no', 20: 'amount', 21: 'cash_bank', 22: 'client_rep_name',
#         #     23: 'client_rep_number', 24: 'email', 25: 'remarks'
#         # }))
#         #
#         # results.append(process_generic_sheet('Calibration', Calibration, 2, {
#         #     0: 'sr_no', 1: 'lh_serial_no', 2: 'cert_no', 3: 'sticker_no', 4: 'equipment_name',
#         #     5: 'company_name', 6: 'received_on', 7: 'technician', 8: 'date_of_calibration',
#         #     9: 'expiry_date', 10: 'validity', 11: 'status', 12: 'note', 13: 'prepared_by',
#         #     14: 'wasted_serial', 15: 'invoice_no', 16: 'amount', 17: 'cash_bank', 18: 'client_rep_name',
#         #     19: 'client_rep_number', 20: 'email', 21: 'remarks'
#         # }))
#
#         # Write skipped logs to file
#         log_file_path = os.path.join(settings.MEDIA_ROOT, 'import_logs.txt')
#         with open(log_file_path, 'w', encoding='utf-8') as f:
#             for sheet, logs in log_data.items():
#                 if logs:
#                     f.write(f"Sheet: {sheet}\n")
#                     for entry in logs:
#                         f.write(f"  - {entry}\n")
#                     f.write("\n")
#
#         for result in results:
#             messages.success(request, f"{result} ✅ Upload complete.")
#
#         messages.info(request, "⚠️ Some rows were skipped. Log saved as 'import_logs.txt' in media folder.")
#         return redirect('index')
#
#     return redirect('index')
# views.py
from datetime import datetime, date

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.shortcuts import render

from authentication.models import Note
from calibration.models import Calibration
from certificates.models import Certificate
from cards.models import Card
from training.models import Training
from ndt.models import NonDestructiveTesting

def verify_data(request):
    search_value = None
    result = None
    result_type = None
    calculated_remaining_months = None
    search_type = request.POST.get('search_type') if request.method == 'POST' else request.GET.get('search_type', '')

    if request.method == 'POST':
        search_value = request.POST.get('search_value', '').strip()  # ✅ Strip whitespace

        common_filter = {
            'isApprove': True,
            'isActive': True,
            'isReject': False,
            'isCancel': False,
            'isHold': False,
        }

        # pick the right model & lookup field
        if search_type == 'certificates':
            sticker_no = request.POST.get('sticker_no', '').strip()
            
            # If sticker_no is provided, search by sticker_no only
            if sticker_no:
                result = Certificate.objects.filter(
                    sticker_no__iexact=sticker_no,
                    **common_filter
                ).first()
                
                # If no exact match, try contains
                if not result:
                    result = Certificate.objects.filter(
                        sticker_no__icontains=sticker_no,
                        **common_filter
                    ).first()
            else:
                # Search by cert_no if no sticker_no provided
                # First try exact match on cert_no (case-insensitive)
                result = Certificate.objects.filter(
                    cert_no__iexact=search_value.strip(),
                    **common_filter
                ).first()
                
                # If no exact match, try contains on cert_no
                if not result:
                    result = Certificate.objects.filter(
                        cert_no__icontains=search_value.strip(),
                        **common_filter
                    ).first()
                    
                # Removed fallback search for sticker_no using search_value
            
            result_type = 'certificate'

        elif search_type == 'cards':
            # First try exact match on card_no
            result = Card.objects.filter(
                card_no__iexact=search_value.strip(),
                **common_filter
            ).first()
            
            # If no exact match, try contains
            if not result:
                result = Card.objects.filter(
                    card_no__icontains=search_value.strip(),
                    **common_filter
                ).first()
            result_type = 'card'

        elif search_type == 'training':
            # First, try exact matches in Training table
            query = Q(cert_no__iexact=search_value.strip()) | Q(card_no__iexact=search_value.strip())
            result = Training.objects.filter(
                query,
                **common_filter
            ).first()

            # If not found, try contains in Training table
            if not result:
                query = Q(cert_no__icontains=search_value.strip()) | Q(card_no__icontains=search_value.strip())
                result = Training.objects.filter(
                    query,
                    **common_filter
                ).first()

            # If still not found, fallback to Cards with specific types
            if not result:
                result = Card.objects.filter(
                    Q(card_no__iexact=search_value.strip()) | Q(card_no__icontains=search_value.strip()),
                    card_type__in=["Welder Card", "Training Card"],
                    **common_filter
                ).first()
            result_type = 'training'

        elif search_type == 'ndt':
            # Try exact match first, then contains
            result = NonDestructiveTesting.objects.filter(
                report_no__iexact=search_value.strip(),
                **common_filter
            ).first()
            
            if not result:
                result = NonDestructiveTesting.objects.filter(
                    report_no__icontains=search_value.strip(),
                    **common_filter
                ).first()
            result_type = 'ndt'

        elif search_type == 'calibration':
            # First try exact match on cert_no
            result = Calibration.objects.filter(
                cert_no__iexact=search_value.strip(),
                **common_filter
            ).first()
            
            # If no exact match, try contains on cert_no
            if not result:
                result = Calibration.objects.filter(
                    cert_no__icontains=search_value.strip(),
                    **common_filter
                ).first()
                
            # If still no match, try sticker_no
            if not result:
                result = Calibration.objects.filter(
                    sticker_no__icontains=search_value.strip(),
                    **common_filter
                ).first()
            result_type = 'calibration'

        # Use improved logic to compute the remaining months
        if result and result.expiry_date:
            try:
                exp_date = datetime.strptime(result.expiry_date, "%Y-%m-%d").date()
                today = date.today()

                if exp_date < today:
                    calculated_remaining_months = "Expired"
                else:
                    delta = relativedelta(exp_date, today)
                    calculated_remaining_months = delta.years * 12 + delta.months
            except Exception as e:
                calculated_remaining_months = None

    # Pull the note for this category from the Note model (one note per type)
    type_note = Note.objects.filter(type=result_type).first() if result_type else None

    return render(request, 'frontend/verify_data.html', {
        'data': result,
        'type': result_type,
        'type_note': type_note,
        'search': search_value,
        'search_type': search_type,
        'calculated_remaining_months': calculated_remaining_months,
    })
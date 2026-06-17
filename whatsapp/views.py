import functools
import logging

import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from base.utils import log_activity
from .models import WhatsAppContact, WhatsAppMessage, WhatsAppMessageLog

logger = logging.getLogger(__name__)


def superuser_required(view_func):
    @functools.wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Access denied. Admin only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped


@superuser_required
def whatsapp_contacts(request):
    search = request.GET.get('search', '').strip()
    qs = WhatsAppContact.objects.all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))

    paginator = Paginator(qs, 25)
    page = request.GET.get('page', 1)
    try:
        contacts_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        contacts_page = paginator.page(1)

    return render(request, 'whatsapp/contacts.html', {
        'sidebar_active': 'whatsapp_contacts',
        'contacts': contacts_page,
        'total_contacts': WhatsAppContact.objects.count(),
        'search': search,
    })


@superuser_required
@require_POST
def upload_contacts_excel(request):
    excel_file = request.FILES.get('excel_file')
    if not excel_file:
        messages.error(request, 'Please select an Excel file.')
        return redirect('whatsapp_contacts')

    if not excel_file.name.lower().endswith(('.xlsx', '.xls')):
        messages.error(request, 'Only Excel files (.xlsx, .xls) are supported.')
        return redirect('whatsapp_contacts')

    try:
        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active

        created = updated = skipped = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue

            name = str(row[0]).strip()
            phone_raw = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ''

            if not name or not phone_raw or phone_raw == 'None':
                skipped += 1
                continue

            # Normalize: remove spaces/dashes, ensure leading +
            phone = phone_raw.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not phone.startswith('+'):
                phone = '+' + phone

            _, was_created = WhatsAppContact.objects.update_or_create(
                phone=phone,
                defaults={'name': name, 'created_by': request.user},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        wb.close()
        log_activity(
            user=request.user,
            action=f"Uploaded WhatsApp contacts Excel: {created} created, {updated} updated, {skipped} skipped",
            request=request,
        )
        messages.success(request, f'Import complete — {created} added, {updated} updated, {skipped} skipped.')

    except Exception as e:
        logger.error(f"WhatsApp Excel upload failed: {e}")
        messages.error(request, f'Error reading Excel file: {e}')

    return redirect('whatsapp_contacts')


@superuser_required
@require_POST
def delete_contact(request, contact_id):
    contact = get_object_or_404(WhatsAppContact, id=contact_id)
    name = contact.name
    contact.delete()
    log_activity(user=request.user, action=f"Deleted WhatsApp contact: {name}", request=request)
    messages.success(request, f'Contact "{name}" deleted.')
    return redirect('whatsapp_contacts')


@superuser_required
@require_POST
def add_contact(request):
    name = request.POST.get('name', '').strip()
    phone_raw = request.POST.get('phone', '').strip()

    if not name or not phone_raw:
        messages.error(request, 'Name and phone number are required.')
        return redirect('whatsapp_contacts')

    phone = phone_raw.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    if WhatsAppContact.objects.filter(phone=phone).exists():
        messages.warning(request, f'A contact with phone {phone} already exists.')
        return redirect('whatsapp_contacts')

    WhatsAppContact.objects.create(name=name, phone=phone, created_by=request.user)
    log_activity(user=request.user, action=f"Added WhatsApp contact: {name} ({phone})", request=request)
    messages.success(request, f'Contact "{name}" added successfully.')
    return redirect('whatsapp_contacts')


@superuser_required
@require_POST
def edit_contact(request, contact_id):
    contact = get_object_or_404(WhatsAppContact, id=contact_id)
    name = request.POST.get('name', '').strip()
    phone_raw = request.POST.get('phone', '').strip()

    if not name or not phone_raw:
        messages.error(request, 'Name and phone number are required.')
        return redirect('whatsapp_contacts')

    phone = phone_raw.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    # Check duplicate phone — allow same contact to keep its own phone
    if WhatsAppContact.objects.filter(phone=phone).exclude(id=contact_id).exists():
        messages.warning(request, f'Another contact already uses {phone}.')
        return redirect('whatsapp_contacts')

    old_name = contact.name
    contact.name = name
    contact.phone = phone
    contact.save()
    log_activity(user=request.user, action=f"Edited WhatsApp contact: {old_name} → {name} ({phone})", request=request)
    messages.success(request, f'Contact updated successfully.')
    return redirect('whatsapp_contacts')


@superuser_required
def send_message(request):
    contacts = WhatsAppContact.objects.all().order_by('name')
    history = WhatsAppMessage.objects.prefetch_related('logs').order_by('-sent_at')[:30]

    if request.method == 'POST':
        mode = request.POST.get('mode', 'text')          # text | template
        msg_type = request.POST.get('message_type', 'single')  # single | bulk
        body = request.POST.get('body', '').strip()
        content_sid = request.POST.get('content_sid', '').strip()
        content_variables = request.POST.get('content_variables', '').strip()

        # prebuilt mode is just custom text (editable template body)
        if mode == 'prebuilt':
            mode = 'text'

        # Validate
        if mode == 'text' and not body:
            messages.error(request, 'Message body is required.')
            return redirect('whatsapp_send')
        if mode == 'template' and not content_sid:
            messages.error(request, 'Template SID is required.')
            return redirect('whatsapp_send')

        # Handle image upload → save and build public URL
        image_url = None
        image_https_warning = False
        uploaded_image = request.FILES.get('message_image')
        if uploaded_image:
            try:
                import os
                import uuid
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile

                ext = os.path.splitext(uploaded_image.name)[1].lower()
                filename = f"whatsapp_images/{uuid.uuid4().hex}{ext}"
                default_storage.save(filename, ContentFile(uploaded_image.read()))

                # Use WHATSAPP_BASE_URL from env (must be HTTPS for Twilio media delivery)
                base_url = getattr(settings, 'WHATSAPP_BASE_URL', '').rstrip('/')
                if not base_url:
                    domain = getattr(settings, 'DOMAIN_NAME', '147.93.90.97')
                    base_url = f"http://{domain}"
                image_url = f"{base_url}/media/{filename}"

                if not image_url.startswith('https://'):
                    image_https_warning = True  # image saved but can't send via Twilio
                    logger.warning(f"WhatsApp image URL is not HTTPS — image won't be sent via Twilio: {image_url}")

            except Exception as e:
                logger.error(f"WhatsApp image upload failed: {e}")

        # Resolve recipients
        if msg_type == 'single':
            contact_id = request.POST.get('contact_id', '').strip()
            if not contact_id:
                messages.error(request, 'Please select a contact.')
                return redirect('whatsapp_send')
            recipient_qs = WhatsAppContact.objects.filter(id=contact_id)
        else:
            selected_ids = request.POST.getlist('bulk_contacts')
            recipient_qs = WhatsAppContact.objects.filter(id__in=selected_ids) if selected_ids else WhatsAppContact.objects.all()

        if not recipient_qs.exists():
            messages.error(request, 'No contacts to send to.')
            return redirect('whatsapp_send')

        wa_message = WhatsAppMessage.objects.create(
            sent_by=request.user,
            message_type=msg_type,
            mode=mode,
            body=body if mode == 'text' else None,
            image_url=image_url,
            content_sid=content_sid if mode == 'template' else None,
            content_variables=content_variables if mode == 'template' else None,
        )

        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

            total_sent = total_failed = 0
            for contact in recipient_qs:
                try:
                    kwargs = {
                        'from_': settings.TWILIO_WHATSAPP_NUMBER,
                        'to': f'whatsapp:{contact.phone}',
                    }
                    if mode == 'template':
                        kwargs['content_sid'] = content_sid
                        if content_variables:
                            kwargs['content_variables'] = content_variables
                    else:
                        kwargs['body'] = body
                        # Only pass media_url if HTTPS — Twilio WhatsApp rejects HTTP
                        # and will fail the entire message, not just the image
                        if image_url and image_url.startswith('https://'):
                            kwargs['media_url'] = [image_url]

                    msg = client.messages.create(**kwargs)
                    WhatsAppMessageLog.objects.create(
                        message=wa_message,
                        contact=contact,
                        phone=contact.phone,
                        contact_name=contact.name,
                        sid=msg.sid,
                        status='sent',
                    )
                    total_sent += 1

                except Exception as e:
                    logger.error(f"WhatsApp send to {contact.phone} failed: {e}")
                    WhatsAppMessageLog.objects.create(
                        message=wa_message,
                        contact=contact,
                        phone=contact.phone,
                        contact_name=contact.name,
                        status='failed',
                        error=str(e),
                    )
                    total_failed += 1

            wa_message.total_sent = total_sent
            wa_message.total_failed = total_failed
            if total_failed == 0:
                wa_message.status = 'sent'
            elif total_sent == 0:
                wa_message.status = 'failed'
            else:
                wa_message.status = 'partial'
            wa_message.save()

            log_activity(
                user=request.user,
                action=f"WhatsApp message sent — {total_sent} delivered, {total_failed} failed ({msg_type})",
                request=request,
            )

            if total_failed == 0:
                messages.success(request, f'Message sent to {total_sent} contact(s).')
            elif total_sent == 0:
                messages.error(request, f'All {total_failed} messages failed. Check Twilio credentials.')
            else:
                messages.warning(request, f'Sent to {total_sent}, failed for {total_failed}.')

            if image_https_warning:
                messages.warning(
                    request,
                    'Image was saved but NOT sent via WhatsApp — Twilio requires an HTTPS URL for images. '
                    'Set WHATSAPP_BASE_URL=https://yourdomain.com in your .env file to enable image sending.'
                )

        except Exception as e:
            logger.error(f"Twilio client init failed: {e}")
            wa_message.status = 'failed'
            wa_message.save()
            messages.error(request, f'Twilio error: {e}')

        return redirect('whatsapp_send')

    return render(request, 'whatsapp/send_message.html', {
        'sidebar_active': 'whatsapp_send',
        'contacts': contacts,
        'history': history,
        'total_contacts': contacts.count(),
    })

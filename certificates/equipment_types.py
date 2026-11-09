"""The Equipment Type list (Settings page) and the certificate forms' dropdown."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from base.utils import log_activity
from whatsapp.views import superuser_required

from .models import EquipmentType, normalize_equipment_type

MAX_LENGTH = EquipmentType._meta.get_field('name').max_length


def _valid_name(raw):
    """(name, error): the cleaned name, or why it can't be used."""
    name = normalize_equipment_type(raw)
    if not name:
        return '', 'Please enter an equipment type.'
    if len(name) > MAX_LENGTH:
        return '', f'Equipment type is too long (maximum {MAX_LENGTH} characters).'
    return name, ''


@superuser_required
def equipment_types_page(request):
    q = request.GET.get('q', '').strip()
    types = EquipmentType.objects.all()
    if q:
        types = types.filter(name__icontains=q)
    return render(request, 'certificates/equipment_types.html', {
        'title': 'Equipment Type',
        'sidebar_active': 'equipment_types',
        'types': Paginator(types, 50).get_page(request.GET.get('page')),
        'total_types': EquipmentType.objects.count(),
        'q': q,
    })


@superuser_required
@require_POST
def equipment_type_add(request):
    name, error = _valid_name(request.POST.get('name'))
    if error:
        messages.error(request, error)
    elif EquipmentType.objects.filter(name__iexact=name).exists():
        messages.warning(request, f'"{name}" is already in the list.')
    else:
        EquipmentType.objects.create(name=name, created_by=request.user)
        log_activity(user=request.user, action=f'Added equipment type {name}', request=request)
        messages.success(request, f'"{name}" added.')
    return redirect('equipment_types')


@superuser_required
@require_POST
def equipment_type_edit(request, pk):
    item = get_object_or_404(EquipmentType, pk=pk)
    name, error = _valid_name(request.POST.get('name'))
    if error:
        messages.error(request, error)
    elif EquipmentType.objects.exclude(pk=pk).filter(name__iexact=name).exists():
        messages.warning(request, f'"{name}" is already in the list.')
    else:
        old, item.name = item.name, name
        item.save(update_fields=['name'])
        log_activity(user=request.user, action=f'Renamed equipment type {old} to {name}', request=request)
        messages.success(request, f'Renamed to "{name}".')
    return redirect('equipment_types')


@superuser_required
@require_POST
def equipment_type_delete(request, pk):
    item = get_object_or_404(EquipmentType, pk=pk)
    name = item.name
    item.delete()
    log_activity(user=request.user, action=f'Deleted equipment type {name}', request=request)
    messages.success(request, f'"{name}" removed from the list. Existing certificates keep their value.')
    return redirect('equipment_types')


@login_required
def equipment_type_options(request):
    return JsonResponse({'types': list(EquipmentType.objects.values_list('name', flat=True))})


@login_required
@require_POST
def equipment_type_quick_add(request):
    """The dropdown's "Add new Type". Anyone who can fill in a certificate may use it."""
    name, error = _valid_name(request.POST.get('name'))
    if error:
        return JsonResponse({'error': error}, status=400)
    existing = EquipmentType.objects.filter(name__iexact=name).first()
    if existing:
        return JsonResponse({'name': existing.name, 'created': False})
    EquipmentType.objects.create(name=name, created_by=request.user)
    log_activity(user=request.user, action=f'Added equipment type {name}', request=request)
    return JsonResponse({'name': name, 'created': True})

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def seed_from_certificates(apps, schema_editor):
    # The Docker sync migrates throwaway snapshots of the live database too:
    # only the real database needs the list.
    if schema_editor.connection.alias != 'default':
        return
    Certificate = apps.get_model('certificates', 'Certificate')
    EquipmentType = apps.get_model('certificates', 'EquipmentType')
    names = set()
    for value in Certificate.objects.values_list('equipment_type', flat=True).distinct().iterator():
        name = ' '.join((value or '').split()).upper().strip(' "\'')
        if name and name != 'NONE' and len(name) <= 200:
            names.add(name)
    EquipmentType.objects.bulk_create(
        [EquipmentType(name=n) for n in sorted(names)], batch_size=500, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('certificates', '0021_long_serial_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.RunPython(seed_from_certificates, migrations.RunPython.noop),
    ]

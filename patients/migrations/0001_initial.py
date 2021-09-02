# Generated by Django 3.2.4 on 2021-09-02 17:23

from django.db import migrations, models
import django.db.models.deletion
import lymph_interface.loggers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hash_value', models.CharField(max_length=200, unique=True)),
                ('gender', models.CharField(choices=[('female', 'female'), ('male', 'male')], max_length=10)),
                ('age', models.IntegerField()),
                ('diagnose_date', models.DateField()),
                ('alcohol_abuse', models.BooleanField(blank=True, null=True)),
                ('nicotine_abuse', models.BooleanField(blank=True, null=True)),
                ('hpv_status', models.BooleanField(blank=True, null=True)),
                ('neck_dissection', models.BooleanField(blank=True, null=True)),
                ('t_stage', models.PositiveSmallIntegerField(choices=[(1, 'T1'), (2, 'T2'), (3, 'T3'), (4, 'T4')], default=0)),
                ('n_stage', models.PositiveSmallIntegerField(choices=[(0, 'N0'), (1, 'N1'), (2, 'N2'), (3, 'N3')])),
                ('m_stage', models.PositiveSmallIntegerField(choices=[(0, 'M0'), (1, 'M1'), (2, 'MX')])),
                ('institution', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, to='accounts.institution')),
            ],
            bases=(lymph_interface.loggers.ModeLoggerMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Tumor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(choices=[('oral cavity', 'Oral Cavity'), ('oropharynx', 'Oropharynx'), ('hypopharynx', 'Hypopharynx'), ('larynx', 'Larynx')], max_length=20)),
                ('subsite', models.CharField(choices=[('oral cavity', (('C03.0', 'upper gum'), ('C03.1', 'lower gum'), ('C03.9', 'gum, nos'), ('C04.0', 'anterior floor of mouth'), ('C04.1', 'lateral floor of mouth'), ('C04.8', 'overlapping lesion of floor of mouth'), ('C04.9', 'floor of mouth, nos'), ('C05.0', 'hard palate'), ('C05.1', 'soft palate, nos'), ('C05.2', 'uvula'), ('C05.8', 'overlapping lesion of palate'), ('C05.9', 'palate, nos'), ('C06.0', 'cheeck mucosa'), ('C06.1', 'vestibule of mouth'), ('C06.2', 'retromolar area'), ('C06.8', 'overlapping lesion(s) of NOS parts of mouth'), ('C06.9', 'mouth, nos'))), ('oropharynx', (('C01.9', 'base of tongue, nos'), ('C09.0', 'tonsillar fossa'), ('C09.1', 'tonsillar pillar'), ('C09.8', 'overlapping lesion of tonsil'), ('C09.9', 'tonsil, nos'), ('C10.0', 'vallecula'), ('C10.1', 'anterior surface of epiglottis'), ('C10.2', 'lateral wall of oropharynx'), ('C10.3', 'posterior wall of oropharynx'), ('C10.4', 'branchial cleft'), ('C10.8', 'overlapping lesions of oropharynx'), ('C10.9', 'oropharynx, nos'))), ('hypopharynx', (('C12.9', 'pyriform sinus'), ('C13.0', 'postcricoid region'), ('C13.1', 'hypopharyngeal aspect of aryepiglottic fold'), ('C13.2', 'posterior wall of hypopharynx'), ('C13.8', 'overlapping lesion of hypopharynx'), ('C13.9', 'hypopharynx, nos'))), ('larynx', (('C32.0', 'glottis'), ('C32.1', 'supraglottis'), ('C32.2', 'subglottis'), ('C32.3', 'laryngeal cartilage'), ('C32.8', 'overlapping lesion of larynx'), ('C32.9', 'larynx, nos')))], max_length=10)),
                ('side', models.CharField(choices=[('left', 'left'), ('right', 'right'), ('central', 'central')], max_length=10)),
                ('extension', models.BooleanField(blank=True, null=True)),
                ('volume', models.FloatField(blank=True, null=True)),
                ('t_stage', models.PositiveSmallIntegerField(choices=[(1, 'T1'), (2, 'T2'), (3, 'T3'), (4, 'T4')])),
                ('stage_prefix', models.CharField(choices=[('c', 'c'), ('p', 'p')], max_length=1)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='patients.patient')),
            ],
            bases=(lymph_interface.loggers.ModeLoggerMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Diagnose',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modality', models.PositiveSmallIntegerField(choices=[(0, 'CT'), (1, 'MRI'), (2, 'PET'), (3, 'FNA'), (4, 'path'), (5, 'pCT')])),
                ('diagnose_date', models.DateField(blank=True, null=True)),
                ('side', models.CharField(choices=[('left', 'left'), ('right', 'right')], max_length=10)),
                ('I', models.BooleanField(blank=True, null=True)),
                ('Ia', models.BooleanField(blank=True, null=True)),
                ('Ib', models.BooleanField(blank=True, null=True)),
                ('II', models.BooleanField(blank=True, null=True)),
                ('IIa', models.BooleanField(blank=True, null=True)),
                ('IIb', models.BooleanField(blank=True, null=True)),
                ('III', models.BooleanField(blank=True, null=True)),
                ('IV', models.BooleanField(blank=True, null=True)),
                ('V', models.BooleanField(blank=True, null=True)),
                ('VII', models.BooleanField(blank=True, null=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='patients.patient')),
            ],
        ),
    ]

# Generated by Django 4.2.11 on 2024-08-02 02:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('botmanager', '0004_alter_discordbasiccommand_command_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discordcustomperiodicmsg',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='discordperiodicmsg',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='twitchcustomperiodicmsg',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
        migrations.AlterField(
            model_name='twitchperiodicmsg',
            name='name',
            field=models.CharField(max_length=256, unique=True),
        ),
    ]

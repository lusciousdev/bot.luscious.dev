# Generated by Django 4.2.11 on 2024-06-22 18:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('botmanager', '0002_twitchchat_channel_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='chatbot',
            old_name='Only post in listed channels?',
            new_name='discord_restrict_channels',
        ),
    ]
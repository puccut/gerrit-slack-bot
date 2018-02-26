# Generated by Django 2.0.2 on 2018-02-26 02:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Crontab',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_name', models.CharField(max_length=100)),
                ('channel_id', models.CharField(blank=True, max_length=30)),
                ('gerrit_query', models.CharField(max_length=255)),
                ('crontab', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='SentMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ts', models.CharField(max_length=30)),
                ('channel_id', models.CharField(max_length=30)),
                ('message', models.TextField(help_text='JSON serialized slack response "message" field to a chat.PostMessage')),
                ('crontab', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_messages', to='slackbot.Crontab')),
            ],
        ),
    ]

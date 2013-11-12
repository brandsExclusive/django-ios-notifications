# -*- coding: utf-8 -*-

try:
    from django.conf.urls import patterns, url
except ImportError:  # deprecated since Django 1.4
    from django.conf.urls.defaults import patterns, url

from django.contrib import admin
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from .models import Device, Notification, APNService, FeedbackService
from .forms import APNServiceForm
from .exceptions import InvalidPassPhrase

from bex.tasks.tasks import send_push_notification


class APNServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'hostname')
    form = APNServiceForm


class DeviceAdmin(admin.ModelAdmin):
    fields = ('token', 'is_active', 'service')
    list_display = ('token', 'is_active', 'service', 'last_notified_at', 'platform', 'display', 'os_version', 'added_at', 'deactivated_at')
    list_filter = ('is_active', 'last_notified_at', 'added_at', 'deactivated_at')
    search_fields = ('token', 'platform')


class NotificationAdmin(admin.ModelAdmin):
    exclude = ('last_sent_at',)
    list_display = ('message', 'badge', 'sound', 'custom_payload', 'created_at', 'last_sent_at',)
    list_filter = ('created_at', 'last_sent_at')
    search_fields = ('message', 'custom_payload')
    list_display_links = ('message', 'custom_payload',)

    def get_urls(self):
        urls = super(NotificationAdmin, self).get_urls()
        notification_urls = patterns('',
                                     url(r'^(?P<id>\d+)/push-notification/$', self.admin_site.admin_view(self.admin_push_notification),
                                     name='admin_push_notification'),)
        return notification_urls + urls

    def admin_push_notification(self, request, **kwargs):
        notification = get_object_or_404(Notification, **kwargs)
        num_devices = 0
        if request.method == 'POST':
            service = notification.service
            num_devices = service.device_set.filter(is_active=True).count()

            send_push_notification.delay(notification, request.user.email)
        return TemplateResponse(request, 'admin/ios_notifications/notification/push_notification.html',
                                {'notification': notification, 'num_devices': num_devices, 'sent': request.method == 'POST'},
                                current_app='ios_notifications')


class FeedbackServiceAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super(FeedbackServiceAdmin, self).get_urls()
        feedbackservice_urls = patterns('',
                                     url(r'^(?P<id>\d+)/feedback-service/$', self.admin_site.admin_view(self.admin_feedback_service),
                                     name='admin_feedback_service'),)
        return feedbackservice_urls + urls

    def admin_feedback_service(self, request, **kwargs):
        service = get_object_or_404(FeedbackService, **kwargs)
        output = ''
        error_msg = ''
        if request.method == 'POST':
            try:
                num_deactivated = service.call()
                output = '%d device%s deactivated.\n' % (num_deactivated, ' was' if num_deactivated == 1 else 's were')
            except InvalidPassPhrase:
                error_msg = "Invalid Passphrase!"

        return TemplateResponse(request, 'admin/ios_notifications/feedbackservice/feedback_service.html',
                                {'service': service, 'output': output, 'error_msg': error_msg},
                                current_app='ios_notifications')


admin.site.register(Device, DeviceAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(APNService, APNServiceAdmin)
admin.site.register(FeedbackService, FeedbackServiceAdmin)

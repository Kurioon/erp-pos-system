from django.conf import settings
from django.db import models
from django.utils import timezone


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=128)
    object_id = models.CharField(max_length=128)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity log'
        verbose_name_plural = 'Activity logs'

    def __str__(self):
        return f'{self.timestamp.isoformat()} | {self.model_name} {self.action} | {self.object_repr}'

    @classmethod
    def log(cls, user, action, instance, changes=None):
        if getattr(user, 'is_authenticated', False) is False:
            user = None
        return cls.objects.create(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,
            object_id=str(getattr(instance, 'pk', '')),
            object_repr=str(instance),
            changes=changes or {},
        )

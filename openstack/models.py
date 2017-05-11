from __future__ import unicode_literals

from django.db import models

# Create your models here.
class Log(models.Model):
    holder = models.CharField(max_length=200)
    log_type = models.CharField(max_length=200)
    time = models.DateTimeField('date of log')
    log_info = models.CharField(max_length=2000)
    def __unicode__(self):
        return self.holder +"_"+self.log_type+"_log"
from django.db import models
from datetime import datetime
from uuidfield import UUIDField

class Search(models.Model):
    
    uuid = UUIDField(auto=True, primary_key=True)
    
    user = models.ForeignKey('auth.User')
    pattern = models.CharField(max_length=1024)
    
    last_view = models.DateTimeField(default=datetime.now)
    
    def ping(self):
        self.last_view = datetime.now()
        self.save()
    
    @models.permalink
    def get_absolute_url(self):
        return ('czagenda_event_ical', (), {'format' : 'ics', 'pk': self.pk})
    
    def __unicode__(self):
        return self.pattern

    class Meta:
        verbose_name = u'Search'
        verbose_name_plural = u'Searches'
        
        
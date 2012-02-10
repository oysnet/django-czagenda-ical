from django.db import models

class Search(models.Model):
    
    user = models.ForeignKey('auth.User')
        
    pattern = models.CharField(max_length=1024)
    
    def __unicode__(self):
        return self.pattern

    class Meta:
        verbose_name = u'Search'
        verbose_name_plural = u'Searches'
        
        unique_together = (('user', 'pattern'),)
from django.views.generic.base import View
from django.http import HttpResponse
from czagenda_ical.helper import CzAgendaHelper
from django.views.generic.detail import SingleObjectMixin
from czagenda_ical.models import Search

class IcalView(SingleObjectMixin, View):
    
    model = Search
    
    def get(self, request, *args, **kwargs):
        
        search = self.get_object()
        search.ping()
        
        profile = search.user.get_profile()
        
        helper = CzAgendaHelper(profile.get_token(), profile.get_secret())
        
        search_result = helper.search_event(search.pattern)
        
        ext = self.kwargs.get('format')
        
        if ext == 'txt':
            return HttpResponse(search_result.to_ical(), content_type="text/plain; charset=utf-8")
        else:
            return HttpResponse(search_result.to_ical(), content_type="text/calendar; charset=utf-8")
        
       
        
        
    
    
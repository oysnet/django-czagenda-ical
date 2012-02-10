from django.core.management.base import BaseCommand
import urllib2
from icalendar import Calendar, Event
from datetime import datetime
import oauth2 as oauth
from django.conf import settings
from django.utils import simplejson
import urllib
from httplib2 import Http
from time import time
import re, os


OAUTH_TOKEN_KEY = os.environ.get('CZAGENDA_OAUTH_TOKEN_KEY', '') 
OAUTH_TOKEN_SECRET = os.environ.get('CZAGENDA_OAUTH_TOKEN_SECRET', '')

OAUTH_CONSUMER_KEY = getattr(settings, 'CZAGENDA_OAUTH_CONSUMER_KEY')
OAUTH_CONSUMER_SECRET = getattr(settings, 'CZAGENDA_CONSUMER_SECRET')

API_HOST = getattr(settings, 'CZAGENDA_API_HOST')
API_PORT = getattr(settings, 'CZAGENDA_API_PORT')
 

 
ICS_DIR = '/Users/me/Desktop/ics/'
 

 
class Command(BaseCommand):
    
    CATEGORIES = {}
    EVENT_COUNT = 0
    
    """
    
        f = open('/Users/hugo/Dropbox/oxys/czagenda/list_ical.txt', 'r')
        
        for line in f.readlines():
            try:
                id, cat, url = line.split(";")
                
                content = urllib2.urlopen("http://%s" % url).read()
                
                ics = open('ics/%s-%s.ics' % (cat, id), 'w')
                ics.write(content)
                ics.close()
                
                print id, cat, url
            except Exception,e:
                print e
                pass
    """
    
    def handle(self, *args, **options):
        
        self._http_client = self.get_http_client()
        self._load_categories()
        
        go = False
        
        for ics in os.listdir(ICS_DIR):
            
            if not go and ics == 'academic-3436.ics':
                go = True  
            
            if not go: continue
            
            self._import_ical(ics)
        
        self._delete()
        
        
        
    def _delete(self):
        
        search = "q=author:/user/oxys%20agenda:/agenda/astronomy&size=500"
        
        resp, content = self._http_client.request("http://%s:%s/api/event/_search?%s" % (API_HOST, API_PORT, search), headers={}, method="GET")

        for event in simplejson.loads(content)['rows']:
            
            self._http_client.request("http://%s:%s/api%s" % (API_HOST, API_PORT, event['id']), headers={}, method="DELETE")
            
            print event['id']
        
    def _import_ical(self, ics_file_path):
        
        print ics_file_path
        
        ical_string = open("%s%s" % (ICS_DIR,ics_file_path), "r").read()
        
        try:
            cal = Calendar.from_ical(ical_string)
        except Exception, e:
            return
        
        try:
            agenda_id = self.get_or_create_agenda(cal.get('X-WR-CALNAME', 'Default'), cal.get('X-WR-CALDESC', None))
            
            category_id = self.get_or_create_category(ics_file_path.split('-')[0])
        except Exception,e:
            print e
            return
        
        for ical_event in cal.walk('VEVENT'):
            
            try:
                event = {
                         'category' : category_id,
                         "links": [{"rel": "describedby","href": "/schema/event"}]
                }
                
                event['title'] = ical_event['summary'].encode('utf-8')
                
                try:
                    event['content'] = ical_event['description'].encode('utf-8')
                except KeyError:
                    continue
                
                event['when'] = [{'startTime' : self._format_date_or_datetime(ical_event['dtstart'].dt)}]
                
                try:
                    event['when'][0]['endTime'] = self._format_date_or_datetime(ical_event['dtend'].dt)
                except KeyError:
                    pass
                
                try:
                    if ical_event['url'][:7] == 'http://' or ical_event['url'][:8] == 'https://':
                        event['website'] = ical_event['url']
                    
                except KeyError:
                    pass
                
                try:
                    event['where'] = [{'valueString' : ical_event['location'].encode('utf-8')}]
                    try:
                        
                        p = urllib.urlencode({'address':event['where'][0]['valueString'].encode('utf-8'),'sensor':"false"})
                        
                        h = Http()   
                        headers, geoloc = h.request("https://maps.googleapis.com/maps/api/geocode/json?%s" % p, "GET")
                        geoloc=simplejson.loads(geoloc)
                        
                        
                        if geoloc['status']=='OK':
                            event['where'][0]['geoPt'] = {}
                            event['where'][0]['geoPt']['lon'] = geoloc['results'][0]['geometry']['location']['lng']
                            event['where'][0]['geoPt']['lat'] = geoloc['results'][0]['geometry']['location']['lat']
                            
                            street_number = None
                            street = None
                            
                            for ac in geoloc['results'][0]['address_components']:
                                
                                if 'street_number' in ac['types']:
                                    street_number=ac['short_name']
                                
                                if 'route' in ac['types']:
                                    street=ac['long_name']
                                
                                if 'country' in ac['types']:
                                    event['where'][0]['country']=ac['short_name']
                                    
                                
                                if 'postal_code' in ac['types']:
                                    event['where'][0]['zipCode']=ac['short_name']
                                
                                if 'locality' in ac['types']:
                                    event['where'][0]['city']=ac['long_name']
                
                                if 'administrative_area_level_1' in ac['types']:
                                    event['where'][0]['adminLevel1']=ac['long_name']
                
                                if 'administrative_area_level_2' in ac['types']:
                                    event['where'][0]['adminLevel2']=ac['long_name']
                            
                            
                            _street = []
                            if street_number is not None:
                                _street.append(street_number)
                            
                            if street is not None:
                                _street.append(street)
                            
                            if len(_street) > 0:
                                event['where'][0]['street']= ' '.join(_street)
                            
                    except ValueError:
                        pass
                    
                except KeyError:
                    pass
                
                try:
                    event['eventStatus'] = str(ical_event['status']).lower()
                except KeyError:
                    event['eventStatus'] ='tentative'
                    
                event = {'event' : event, 'agenda' : agenda_id}
                
                Command.EVENT_COUNT += 1
                print Command.EVENT_COUNT
                
                self.create_event(event)
                
            except Exception, e:
                print e
           
            
    def get_http_client(self):
        consumer = oauth.Consumer(key=OAUTH_CONSUMER_KEY, secret=OAUTH_CONSUMER_SECRET)
        token = oauth.Token(key=OAUTH_TOKEN_KEY, secret=OAUTH_TOKEN_SECRET)
        http_client = oauth.Client(consumer, token)
        return http_client
       
    def _load_categories(self):
        
        resp, content = self._http_client.request("http://%s:%s/api/category" % (API_HOST, API_PORT), headers={}, method="GET")

        for category in simplejson.loads(content)['rows']:
            self.CATEGORIES[category['title']] = category['id']
       
    def get_or_create_category(self, title):
        
        if len(title) < 5:
            title = "category %s" % title
        
        try:
            return self.CATEGORIES[title]
        except KeyError:
            pass
        
        headers = {'Content-Type' : 'application/json' }
        data = simplejson.dumps({'title' : title})
        resp, content = self._http_client.request("http://%s:%s/api/category" % (API_HOST, API_PORT), headers=headers, method='POST', body=data)
        
        content = simplejson.loads(content)
        self.CATEGORIES[title] = content['id']
            
        return content['id']
       
    def create_event(self, event):
        headers = {'Content-Type' : 'application/json' }
        data = simplejson.dumps(event)
        
        start = time()
        resp, content = self._http_client.request("http://%s:%s/api/event" % (API_HOST, API_PORT), headers=headers, method='POST', body=data)
        
        if int(resp['status']) == 201:
            print "create event in agenda %s (%s)" % (event['agenda'], time()-start)
        elif int(resp['status']) == 409:
            print "event already exit in agenda %s" % event['agenda']
            return
            resp, content = self._http_client.request('http://%s:%s/api/event/_search?%s' % (API_HOST, API_PORT,urllib.urlencode({'q' : 'event.title:"%s"' % event['event']['title'].encode('utf-8')})), headers={}, method='GET')
            if int(resp['status']) == 200:
                content = simplejson.loads(content)
                
                print event['event']['title']
                
                if len(content['rows']) == 1:
                    event_id = content['rows'][0]['id']
                    resp, content = self._http_client.request("http://%s:%s/api%s" % (API_HOST, API_PORT, event_id), headers=headers, method='PUT', body=data)
                    
                    if int(resp['status']) == 200:
                        print "update event %s" % event_id
                        return
            

            print "event already exit in agenda %s" % event['agenda']
            
        else:
            print resp, content
            print event
            raise Exception('create_event failed')
    def get_or_create_agenda(self, title, description):
        headers = {'Content-Type' : 'application/json' }
        
        if len(title) < 5:
            title = "agenda %s" % title
            
        title = title.encode('utf-8')
            
        agenda = {'title' : title}
        
        if description is not None:
            agenda['description'] =  description.encode('utf-8')
        
        agenda = simplejson.dumps(agenda)
        resp, content = self._http_client.request("http://%s:%s/api/agenda" % (API_HOST, API_PORT), headers=headers, method='POST', body=agenda)
        
        if int(resp['status']) == 201:
            return simplejson.loads(content)['id']
        else:
            search = urllib.urlencode({'q' : u'title:"%s"' % title})
            
            resp, content = self._http_client.request('http://%s:%s/api/agenda/_search?%s' % (API_HOST, API_PORT, search), headers={}, method='GET')
            
            if int(resp['status']) == 200:
                return simplejson.loads(content)['rows'][0]['id']
            
    def _format_date_or_datetime(self, dt):
        
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            return dt.strftime('%Y-%m-%d')
            
                
                

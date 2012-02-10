import re, iso8601,  oauth2 as oauth

from django.conf import settings
from django.utils import simplejson

from icalendar import Calendar, Event
from datetime import datetime

OAUTH_CONSUMER_KEY = getattr(settings, 'CZAGENDA_OAUTH_CONSUMER_KEY')
OAUTH_CONSUMER_SECRET = getattr(settings, 'CZAGENDA_CONSUMER_SECRET')

API_HOST = getattr(settings, 'CZAGENDA_API_HOST')
API_PORT = getattr(settings, 'CZAGENDA_API_PORT')

RE_ISO8601 = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}Z?')

class EventSearchResult(object):
    
    def __init__(self, results, http_client):
        self.results = results
        self._http_client = http_client
    
    def to_json(self):
        return simplejson.dumps(self.results)
        
    def to_ical(self):
        
        self._load_categories()
        
        ical = Calendar()

        ical.add('prodid', '-//Czagenda//czagenda.org//')
        ical.add('version', '2.0')
        ical.add('method', 'PUBLISH')
        
        for row in self.results['rows']:
            
            event = row['event']
        
            ical_event = Event()
            
            ical_event.set('uid', '%s@czagenda.org' % row['id'])
            ical_event.set('status', event['eventStatus'].upper())
            
            ical_event.add('dtstamp', iso8601.parse_date(row['createDate']))
            ical_event.add('CREATED', iso8601.parse_date(row['createDate']))
            ical_event.add('LAST-MODIFIED', iso8601.parse_date(row['updateDate']))
            
            ical_event.set('summary', event['title'])
            
            description = []
            if len(event.get('subtitle', '')) > 0:
                description.append(event['subtitle'])
            if len(event.get('shortDescription', '')) > 0:
                description.append(event['shortDescription'])
            if len(event.get('content', '')) > 0:
                description.append(event['content'])
            
            
            if event.has_key('contacts'):
                
                text_contacts = ['Contacts:']
                
                for contact in event['contacts']:
                    text_contact = [contact['rel']]
                    if contact.has_key('email'):
                        text_contact.append("email: %s" % contact['email'])
                    if contact.has_key('phone'):
                        text_contact.append("phone: %s" % contact['phone'])
                    if contact.has_key('fax'):
                        text_contact.append("fax: %s" % contact['fax'])
                    if contact.has_key('link'):
                        text_contact.append("website: %s" % contact['link'])
                    if contact.has_key('additionalInformations'):
                        text_contact.append(contact['additionalInformations'])
                    
                    text_contacts.append(u'/'.join(text_contact))
                    
                description.append('\n'.join(text_contacts))
                    
            
            if len(description)>0:
                ical_event.set('description', u'\n\n'.join(description))
            
            if event.has_key('website'):
                ical_event.set('url', event['website'])
            
            if RE_ISO8601.match(event['when'][0]['startTime']):
                ical_event.set('dtstart', iso8601.parse_date(event['when'][0]['startTime']))
                
                if event['when'][0].has_key('endTime'):
                    ical_event.add('dtend', iso8601.parse_date(event['when'][0]['endTime']))
                
            else:
                ical_event.set('dtstart', datetime.strptime(event['when'][0]['startTime'], '%Y-%m-%d'))
                
                if event['when'][0].has_key('endTime'):
                    ical_event.add('dtend', datetime.strptime(event['when'][0]['endTime'], '%Y-%m-%d'))
            
            
            location = []
            
            if event.has_key('place'):
                location.append(event['place']['name'])
            
            if event.has_key('where') and len(event['where']) > 0:
                
                try:
                    location.append(event['where'][0]['street'])
                except KeyError:
                    pass
                
                try:
                    location.append(event['where'][0]['city'])
                except KeyError:
                    pass   
                
                try:
                    location.append(event['where'][0]['zipCode'])
                except KeyError:
                    pass  
                
                try:
                    location.append(event['where'][0]['country'])
                except KeyError:
                    pass                
                
                if event['where'][0].has_key('geoPt'):
                    ical_event.add('geo', (event['where'][0]['geoPt']['lat'], event['where'][0]['geoPt']['lon'] ))
                
            if len(location) > 0:
                ical_event.add('location', u', '.join(location))
                    
            try:
                categories = [CzAgendaHelper.CATEGORIES[event['category']]]
            except KeyError:
                self._load_categories(force_reload=True)
                categories = [CzAgendaHelper.CATEGORIES[event['category']]]
            
            if event.has_key('tags'):
                for tag in event['tags']:
                    categories.append(tag)
            
            ical_event.set('categories', u', '.join(categories))
            ical_event.set('class', self._get_event_class(row))
            
            ical.add_component(ical_event)
            
        return ical.to_ical()
    
    def _load_categories(self, force_reload=False):
        if len(CzAgendaHelper.CATEGORIES) > 0 and not force_reload:
            return
        
        resp, content = self._http_client.request("http://%s:%s/api/category/_count" % (API_HOST, API_PORT), headers={}, method="GET")
        
        resp, content = self._http_client.request("http://%s:%s/api/category/?size=%s" % (API_HOST, API_PORT, simplejson.loads(content)['count']), headers={}, method="GET")

        for category in simplejson.loads(content)['rows']:
            CzAgendaHelper.CATEGORIES[category['id']] = category['title']
            
    def _get_event_class(self, event):
        resp, content = self._http_client.request("http://%s:%s/api%s" % (API_HOST, API_PORT, event['readGroups']), headers={}, method="GET")
        
        for perm in simplejson.loads(content)['rows']:
            if perm['grantTo'] == '/group/all':
                return 'PUBLIC'
       
        resp, content = self._http_client.request("http://%s:%s/api%s" % (API_HOST, API_PORT, event['readUsers']), headers={}, method="GET")
        for perm in simplejson.loads(content)['rows']:
            if perm['grantTo'] == '/user/all':
                return  'PUBLIC'
            
        return 'PRIVATE'
    
class CzAgendaHelper(object):
    
    CATEGORIES = {}
    
    def __init__(self, token, secret):
        
        self._token = token
        self._secret = secret
        
    def set_wilcards(self, pattern):
        
        re_complex_search = re.compile(r'(\*|\(|or\s+|and\s+)', re.IGNORECASE)
        re_split_search = re.compile(r'[0-9a-z\.]+:' , re.IGNORECASE)
        
        if re_complex_search.search(pattern) is None:
            
            split_pattern = re_split_search.split(pattern)
            if len(split_pattern) > 0 and pattern[0:len(split_pattern[0])] == split_pattern[0]:
                
                _tmp = []
                
                for ft in re.split(r'\s+',split_pattern[0].strip()):
                    if ft.lower() not in [')', '(', 'or', 'and']:
                        _tmp.append("*%s*" % ft)
                        _tmp.append("%s*" % ft)
                    else:
                        _tmp.append(ft)
                        
                pattern = pattern.replace(split_pattern[0].strip(), u' '.join(_tmp))
        
        return pattern
                
            
        
    def search_event(self, pattern=None, start=None, limit=None, sort=None):
        http_client = self.get_http_client()
            
        
        if pattern is not None:
            querystring = 'q=' + pattern
        else:
            querystring = ''
            
        headers = {}
        resp, content = http_client.request("http://%s:%s/api/event/_count?%s" % (API_HOST, API_PORT, querystring), headers=headers, method="GET")
        
        count = simplejson.loads(content)['count']
        if int(count) > 1000:
            count = 1000
        
        resp, content = http_client.request("http://%s:%s/api/event/_search?%s&size=%s" % (API_HOST, API_PORT, querystring, count), headers=headers, method="GET")
        
        return EventSearchResult(simplejson.loads(content), http_client)
   
        
        
    def get_http_client(self):
        consumer = oauth.Consumer(key=OAUTH_CONSUMER_KEY, secret=OAUTH_CONSUMER_SECRET)
        token = oauth.Token(key=self._token, secret=self._secret)
        http_client = oauth.Client(consumer, token)
        return http_client
    
    
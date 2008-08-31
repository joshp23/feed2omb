import feedparser
import urllib2
from urllib import urlencode
from configobj import ConfigObj

config = ConfigObj('feed2omb.config')

print 'Reading feed...'
feed=feedparser.parse(config['feedurl'])

for entry in reversed(feed.entries):
  if not "'"+entry.link+"'" in config['sentlinks']:
    bitly = urllib2.urlopen('http://bit.ly/api?url='+entry.link)
    shorturl = bitly.read()
    maxlen=140-len(shorturl)-4
    text=entry.title
    if len(text)>maxlen:
      text=text[:maxlen]+'... '
    else:
      text+=' - '
    text+=shorturl

    print 'Sending new message:'
    print '  '+text

    password_mgr=urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None,config['apibaseurl'],config['user'],config['password'])
    handler=urllib2.HTTPBasicAuthHandler(password_mgr)
    opener=urllib2.build_opener(handler)
    data={'status':text}
    resp=opener.open(config['apibaseurl']+'/statuses/update.xml',urlencode(data))
    resp.close()

    config['sentlinks']["'"+entry.link+"'"]='sent'

config.write()
print 'Finished'


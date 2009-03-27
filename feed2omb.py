#
# feed2omb - a tool for publishing atom/rss feeds to microblogging services
# Copyright (C) 2008-2009, Ciaran Gultnieks
#
# Version 0.74
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import feedparser
import urllib2
import sys
import re
from datetime import datetime
import time
from urllib import urlencode
from configobj import ConfigObj
from optparse import OptionParser


#Get the author name for a particular entry
def getauthor(entry):
  if 'source' in entry and 'author_detail' in entry.source and 'name' in entry.source.author_detail:
    return entry.source.author_detail.name
  if 'author_detail' in entry and 'name' in entry.author_detail:
    return entry.author_detail.name
  else:
    return ""

#URL shorteners - each of these takes a URL and returns the
#shortened version, along with the 'length' of the shortened
#version. The length is quoted, and returned, because where
#we allow the target OMB site to shorten for us, we don't
#return the actual length here, but an assumed one.
#The second parameter is the host to use for shortening, which
#is relevant only for shortening types that require it.
def shorten_bitly(url,host):
  try:
    biturl='http://bit.ly/api?url='+url
    print 'Requesting short URL from "'+biturl+'"'
    bitly = urllib2.urlopen(biturl)
    shorturl = bitly.read()
  except:
    #Sometimes, bit.ly seems to refuse to give a result for
    #a seemlingly innocuous URL - this is a fallback for that
    #scenario...
    print 'Failed to get short URL'
    shorturl='<no link>'
  return (shorturl,len(shorturl))

def shorten_laconica(url,host):
  return (url,22)

def shorten_lilurl(url,host):
  try:
    if host==None:
      print "Configuration error - lilurl shortener requires a host"
      sys.exit(1)
    params={'longurl' : url}
    data=urlencode(params)
    req=urllib2.Request(host,data)
    response=urllib2.urlopen(req)
    result=response.read()
    #It's a hack, but I don't want to get involved in "which parser,
    #which dom, make sure you have these dependencies installed" just
    #to pull a tiny bit of text out of a bigger bit of text, so...
    index_start=result.find('href="')
    index_end=result.find('"',index_start+6)
    if index_start==-1 or index_end==-1:
      raise Exception("Link not found")
    shorturl=result[index_start+6:index_end]
    return (shorturl,len(shorturl))
  except:
    print 'Failed to get short URL'
    shorturl='<no link>'
  return (shorturl,len(shorturl))

def shorten_none(url,host):
  return (url,len(url))



print "feed2omb version 0.74\nCopyright 2008-9 Ciaran Gultnieks\n"

#Deal with the command line...
parser=OptionParser()
parser.add_option("-v","--version",dest="version",action="store_true",default=False,
                  help="Display version and exit")
parser.add_option("-u","--update",dest="update",action="store_true",default=False,
                  help="Update the feeds using the config files specified")
parser.add_option("-e","--eat",dest="eat",action="store_true",default=False,
                  help="Eat items found - i.e. mark as sent, but do not send")
parser.add_option("-t","--test",dest="test",action="store_true",default=False,
                  help="Test only - display local output but do not post to omb or mark as sent")
parser.add_option("-m","--max",type="int",dest="max",default=0,
                  help="Specify maximum number of items to process for each feed")
(options, args) = parser.parse_args()

if options.version:
  sys.exit(0)

if not (options.update or options.eat):
  print "Specify either --update or --eat to process feeds"
  sys.exit(1)
if options.update and options.eat:
  print "You can't specify both --update and --eat"
  sys.exit(1)

if len(args)==0:
  print "No config files specified - specify one or more config files to process"
  sys.exit(1)

for thisconfig in args:

  print "Reading config: "+thisconfig
  config = ConfigObj(thisconfig,file_error=True)

  print 'Reading feed...'
  feed=feedparser.parse(config['feedurl'])

  done=0

  #Determine message mode...
  if 'msgmode' in config:
    msgmode=config['msgmode']
  else:
    msgmode='title'

  #Determine if we are including links with the message...
  if 'includelinks' in config and config['includelinks']=='no':
    includelinks=False
  else:
    includelinks=True

  #Determine sent mode... (i.e. how we decide if we've already sent an entry)
  if 'sentmode' in config:
    sentmode=config['sentmode']
  else:
    sentmode='sentlinks'
  if sentmode=='timestamp':
    if 'lastsent' in config:
      lastsent=datetime(*time.strptime(config['lastsent'],"%Y-%m-%d %H:%M:%S")[0:6])
    else:
      lastsent=datetime.min

  #Determine url shortening mode...
  if 'urlshortener' in config:
    urlshortener=config['urlshortener']
    if 'urlshortenhost' in config:
      urlshortenhost=config['urlshortenhost']
    else:
      urlshortenhost=None
  else:
    urlshortener='bit.ly'
    urlshortenhost=None

  #Determine hashtag mode...
  if 'hashtags' in config:
    hashtags=config['hashtags']
  else:
    hashtags='none'

  if 'messageregex' in config and 'messagereplace' in config:
    msgregex=re.compile(config['messageregex'])
  else:
    msgregex=None

  for entry in reversed(feed.entries):

    #Decide if this is a new entry or one we've already sent...
    isnew=False
    if sentmode=='timestamp':
      (t_year,t_month,t_day,t_hour,t_minute,t_second,t_x,t_x1,t_x2)=entry.updated_parsed
      thissent=datetime(t_year,t_month,t_day,t_hour,t_minute,t_second)
      if lastsent<thissent:
        isnew=True
    else:
      if not "'"+entry.link+"'" in config['sentlinks']:
        isnew=True

    if isnew:
      print 'Found new entry: '+entry.link

      #Shorten the URL...
      if includelinks:
        longurl=entry.link
        (shorturl,urllen) = {'bit.ly': shorten_bitly,
                             'lilurl': shorten_lilurl,
                             'laconica': shorten_laconica,
                             'none': shorten_none}[urlshortener](longurl,urlshortenhost)
      else:
        urllen=0

      #See how much space we have left once the URL is there:
      maxlen=140-urllen-4

      if msgmode=='authtitle':
        text=getauthor(entry)+' - '+entry.title
      elif msgmode=='summary':
        if 'summary' in entry:
          text=entry.summary
        else:
          text=entry.title
      else:
        text=entry.title

      #Apply regular expression search/replace to the message body if
      #requested...
      if msgregex:
        text=msgregex.sub(config['messagereplace'],text)

      if len(text)>maxlen:
        text=text[:maxlen]+'... '
      elif includelinks:
        text+=' - '

      #Append the url. Don't bother using the shortened one if the full
      #one fits...
      if includelinks:
        if len(text+longurl)<140:
          text+=longurl
        else:
          text+=shorturl

      #Add hashtags from categories if that mode is enabled...
      if hashtags=='category':
        if 'categories' in entry:
          cats=entry.categories
          for cat in cats:
            (dontcare,cattxt)=cat
            cattxt=' #'+cattxt
            if len(text+cattxt)<140:
              text+=cattxt

      if options.test:
        if options.eat:
          print 'Eaten message would be:'
        else:
          print 'Sent message would be:'
      else:
        if options.eat:
          print 'Eating new message:'
        else:
          print 'Sending new message:'
      if sys.stdout.encoding!=None:
        print '  '+text.encode(sys.stdout.encoding,'replace')
      else:
        print '  <message hidden - output encoding cannot be determined>' 

      if not options.test:
        if options.update:
          password_mgr=urllib2.HTTPPasswordMgrWithDefaultRealm()
          password_mgr.add_password(None,config['apibaseurl'],config['user'],config['password'])
          handler=urllib2.HTTPBasicAuthHandler(password_mgr)
          opener=urllib2.build_opener(handler)
          data={'status':text.encode('utf-8')}
          resp=opener.open(config['apibaseurl']+'/statuses/update.xml',urlencode(data))
          resp.close()

      #Record that we have sent this entry...
      if sentmode=='timestamp':
        lastsent=thissent
        config['lastsent']=lastsent.strftime("%Y-%m-%d %H:%M:%S")
      else:
        config['sentlinks']["'"+entry.link+"'"]='sent'

      #Rewrite the config after each link to avoid double-posting if something goes wrong
      if not options.test:
        config.write()

      done+=1
      if options.max >0 and done>=options.max:
        print "Reached requested limit"
        break

print 'Finished'

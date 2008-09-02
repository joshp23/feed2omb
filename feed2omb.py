#
# feed2omb - a tool for publishing atom/rss feeds to microblogging services
# Copyright (C) 2008, Ciaran Gultnieks
#
# Version 0.4
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
from urllib import urlencode
from configobj import ConfigObj
from optparse import OptionParser

print "feed2omb version 0.4\nCopyright 2008 Ciaran Gultnieks\n"

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
parser.add_option("-m","--max",type="int",dest="max",default="0",
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
  config = ConfigObj(thisconfig)

  print 'Reading feed...'
  feed=feedparser.parse(config['feedurl'])

  done=0

  for entry in reversed(feed.entries):
    if not "'"+entry.link+"'" in config['sentlinks']:
      print 'Found new entry: '+entry.link
      bitly = urllib2.urlopen('http://bit.ly/api?url='+entry.link)
      shorturl = bitly.read()
      maxlen=140-len(shorturl)-4
      text=entry.title
      if len(text)>maxlen:
        text=text[:maxlen]+'... '
      else:
        text+=' - '
      text+=shorturl

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
      print '  '+text.encode(sys.stdout.encoding,'replace')

      if not options.test:
        if options.update:
          password_mgr=urllib2.HTTPPasswordMgrWithDefaultRealm()
          password_mgr.add_password(None,config['apibaseurl'],config['user'],config['password'])
          handler=urllib2.HTTPBasicAuthHandler(password_mgr)
          opener=urllib2.build_opener(handler)
          data={'status':text.encode('utf-8')}
          resp=opener.open(config['apibaseurl']+'/statuses/update.xml',urlencode(data))
          resp.close()

        config['sentlinks']["'"+entry.link+"'"]='sent'

        #Rewrite the config after each link to avoid double-posting if something goes wrong
        config.write()
        
      done+=1
      if done>=options.max:
        print "Reached requested limit"
        break

print 'Finished'

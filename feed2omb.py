#
# feed2omb - a tool for publishing atom/rss feeds to microblogging services
# Copyright (C) 2008, Ciaran Gultnieks
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

print "feed2omb version 0.2\nCopyright 2008 Ciaran Gultnieks\n"

#Deal with the command line...
parser=OptionParser()
parser.add_option("-v","--version",dest="version",action="store_true",default=False,
						help="Display version and exit")
parser.add_option("-u","--update",dest="update",action="store_true",default=False,
						help="Update the feeds using the config files specified")
parser.add_option("-t","--test",dest="test",action="store_true",default=False,
						help="Test only - display new items but do not post to omb")
(options, args) = parser.parse_args()

if options.version:
  sys.exit(0)

if not options.update or len(args)==0:
  print "Specify the --update option and one or more config files to update"
  sys.exit(1)

for thisconfig in args:

  print "Reading config: "+thisconfig
  config = ConfigObj(thisconfig)

  print 'Reading feed...'
  feed=feedparser.parse(config['feedurl'])

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

      if not options.test:
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

        #Rewrite the config after each link to avoid double-posting if something goes wrong
        config.write()

print 'Finished'

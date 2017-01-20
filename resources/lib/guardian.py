import urllib2
import urlparse
from xml.dom import minidom
import time
import datetime
import re
import json
from email.utils import parsedate_tz
from email.utils import mktime_tz
from BeautifulSoup import BeautifulSoup

class GuardianTV:
    __USERAGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:50.0) Gecko/20100101 Firefox/50.0"
    
    def __init__(self):
        opener = urllib2.build_opener()
        # Use Firefox User-Agent
        opener.addheaders = [('User-Agent', self.__USERAGENT)]
        urllib2.install_opener(opener)

    def getChannels(self):
        pageUrl = "http://www.theguardian.com/video"
        data = urllib2.urlopen(pageUrl).read()
        tree = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        
        links = tree.findAll("section")
        channels = []
        for link in links:
            if link.has_key("data-id"):
                channel = {}
                channel["title"] = link["data-link-name"][link["data-link-name"].find("|") + 2 : ]
                channel["url"] = "http://www.theguardian.com/collection/%s/rss" % link["data-id"]
                channels.append(channel)
        
        return channels
        
    def getVideoByChannel(self, url):
        # RSS 2.0 only
        xmldata = urllib2.urlopen(url).read()
        dom = minidom.parseString(xmldata)

        videos = []
        for videoNode in dom.getElementsByTagName('item'):
            video = {}
            
            video["title"] = videoNode.getElementsByTagName('title')[0].firstChild.data.strip()
            
            try:
                video["description"] = videoNode.getElementsByTagName('description')[0].firstChild.data
            except:
                video["description"] = ""
            
            dt = videoNode.getElementsByTagName('pubDate')[0].firstChild.data
            video["date"] = time.gmtime((mktime_tz(parsedate_tz(dt))))
            
            video["thumb"] = ""
            width = 0
            for mediaContent in videoNode.getElementsByTagName('media:content'):
                try:
                    mimeType = mediaContent.attributes["type"].value
                except KeyError:
                    mimeType = ""
                
                imageUrl = mediaContent.attributes["url"].value
                scheme, netloc, path, params, query, fragment = urlparse.urlparse(imageUrl)
                imageExt = path[path.rfind(".")+1:]
                imageWidth = mediaContent.attributes["width"].value
                
                if (mimeType == "image/jpeg" or mimeType == "image/png" or imageExt == "jpg" or imageExt == "jpeg" or imageExt == "png" ) and imageWidth > width:
                    video["thumb"] = imageUrl
                    width = imageWidth
            
            video["pageUrl"] = videoNode.getElementsByTagName('link')[0].firstChild.data.strip()
            
            videos.append(video)
            
        return videos

    def getVideoMetadata(self, pageUrl):
        # Parse the HTML page to get the Video Metadata
        data = urllib2.urlopen(pageUrl).read()
        tree = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        
        video = {}
        video["title"] = tree.find("meta", {"property": "og:title"})["content"]
        video["thumb"] = tree.find("meta", {"property": "og:image"})["content"]
        video["url"] = None
        
        videoNode = tree.find("video")
        if videoNode is not None:
            video["url"] = videoNode.find("source", {"type": "video/mp4"})["src"]
        else:
            # Docs on YouTube
            figure = tree.find("figure")
            if figure is not None:
                dataInteractiveUrl = figure["data-interactive"]
                sheetName = dataInteractiveUrl[dataInteractiveUrl.find("/docs-")+6:dataInteractiveUrl.find("/boot.js")]
                
                dataInteractive = urllib2.urlopen(dataInteractiveUrl).read()
                match = re.search(r"'sheetId': '([A-Za-z0-9]+)',", dataInteractive, re.DOTALL)
                sheetId = match.group(1)

                sheetUrl = "https://interactive.guim.co.uk/docsdata/%s.json" % sheetId
                sheets = json.load(urllib2.urlopen(sheetUrl))
                youTubeId = sheets["sheets"][sheetName][0]["youTubeId"]

                video["url"] = "plugin://plugin.video.youtube/play/?video_id=%s" % youTubeId
         
        return video
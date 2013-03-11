#!/usr/bin/env python
#encoding utf8
import urllib2 as urll


def getSeasonUrls(baseurl = "http://www.basketball-reference.com"):
    seasonlines = filter(lambda l: True if "/leagues/" in l else False, urll.urlopen(baseurl+"/leagues/").readlines()) #Gets the lines with links to the actual seasons
    seasonurls = map(lambda l: l.split('"')[3] if "light_text" not in l else l.split('"')[5], filter(lambda l: True if "-" in l else False, seasonlines)) #Removes duplicates and Cut the url of the season out of the html
    return seasonurls

def parseSeason(seasonurls):
    raise NotImplementedError

print getSeasonUrls()

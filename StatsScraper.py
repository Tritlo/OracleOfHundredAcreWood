#!/usr/bin/env python
#encoding utf8
import urllib2 as urll
from itertools import takewhile
    

def getSeasonUrls(baseurl = "http://www.basketball-reference.com"):
    seasonlines = filter(lambda l: True if "/leagues/" in l else False, urll.urlopen(baseurl+"/leagues/").readlines()) #Gets the lines with links to the actual seasons
    seasonurls = map(lambda l: l.split('"')[3] if "light_text" not in l else l.split('"')[5], filter(lambda l: True if "-" in l else False, seasonlines)) #Removes duplicates and Cut the url of the season out of the html
    return map(lambda u: baseurl+u.split('.')[0] + "_games.html", seasonurls)[1:] #Do not parse 2013

def parseSeasons(seasonurls):
    tableStartDef = lambda line: True if '<table class=' in line else False
    tableEndDef = lambda line: True if "</table>" in line else False
    rowstart = lambda row: True if row.startswith('<tr ') else False
    rowend = lambda row: True if row.startswith("</tr>") else False
    rowsoftable = lambda table: map(lambda k: list(takewhile(lambda x: not rowend(x),table[k:])),filter(lambda i: rowstart(table[i]),range(len(table)))) #A list of the rows of the table table.
    tables = lambda lines: map(lambda i: [lines[i]] + list(takewhile(lambda x: not tableEndDef(x),lines[i+1:])),filter(lambda i: tableStartDef(lines[i]),range(len(lines)))) #The tables in the file which lines are lines
    teamsandscores = lambda lines: map(lambda table: map(lambda row: map(lambda l: l.split(">")[2].split("<")[0] if "teams" in l else l.split(">")[1].split("<")[0],row[3:7]),table[1:]),map(rowsoftable,tables(lines))) #Teams and score of the file which lines are lines
    seasonDict = lambda lines: dict(zip(["regular season","playoffs"],teamsandscores(lines))) #The seasons of the file which lines are lines
    #return map(lambda url: seasonDict(urll.urlopen(url).readlines),seasonurls)
    for season in seasonurls:
        lines = urll.urlopen(season).readlines()
        print seasonDict(lines)["regular season"][0:3]
        break

print parseSeasons(getSeasonUrls())

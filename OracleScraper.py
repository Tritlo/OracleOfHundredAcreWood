#!/usr/bin/env python
# coding: utf-8
#Copyright (C) 2013 Matthías Páll Gissurarson & Sólrún Halla Einarsdóttir. See LICENSE for details.
import urllib2 as urll
from itertools import takewhile
import sqlite3 as sql
import time, datetime


class OracleScraper:
    
    dbConn = None #Connection to the database
    databaseName = None #The name of the database were using
    tableName = None #The name of the table we keep the current view of the table in.
    dbTableName = None# Name of the table we keep all data in
    calcedDbTableName = None# Name of the table we keep all data in and we have computed data for last games
    calced = False

    def __init__(self,tableName = "data", dbTableName = "databaseTable", calcedDbTableName= "calcedDBTable", databaseName = "StatsDatabase.db",scheduleName = "Schedule", fr = 1977, to = 2012, fetchData = True, calcFrom = 2000, calcTo = 2012, calc = True, fetchSchedule = True):
        self.dbConn =  sql.connect(databaseName,detect_types=sql.PARSE_DECLTYPES)
        self.databaseName = databaseName
        self.tableName = tableName
        self.dbTableName = dbTableName
        self.calcedDbTableName = calcedDbTableName
        self.calced = calc
        tableExists = lambda tableName: False if len(list(self.dbConn.execute("select name from sqlite_master where type='table' and name = '%s'" % tableName))) < 1 else True #Checks whether the table exists.
        if fetchData:
            if not tableExists(dbTableName): 
                self.seasonsToSql( seasons=self.parseSeasons(self.getSeasonUrls(fr=fr,to=to)), fr = fr, to = to)

            if not tableExists("teamNames"):
                self.teamNamesToSql(self.getTeams())

            if not tableExists("teams"):
                self.teamsToSql()

            if not tableExists("teamStats"):
                self.teamStatsToSql(self.parseTeamStats(self.getTeamUrls()))

            if calc:
                self.calcLastGamesForDatabase(calcFrom,calcTo,calcedDbTableName)

            self.changeData(fr,to)
        
        if fetchSchedule:
            today = datetime.datetime.date(datetime.datetime.now())
            if tableExists(scheduleName):
                if len(list(self.dbConn.execute("select date from %s where date < ?" %(scheduleName),(today,)))) > 0:
                    self.dbConn.execute("DROP TABLE %s" % (scheduleName))
                    self.scheduleToSql( self.parseSeasons(self.getSeasonUrls(fr=2013,to=2013)),scheduleName=scheduleName)
            else:
                self.scheduleToSql( self.parseSeasons(self.getSeasonUrls(fr=2013,to=2013)),scheduleName=scheduleName)

    def getSeasonUrls(self,baseurl = "http://www.basketball-reference.com", fr = 1977, to= 2012):
        """
        #Use: l = getSeasonUrls(url,fr,to)
        #Pre: url is a valid url, fr - to is a valid period where games were played
        #Post: a list of the urls on the webpage that point to a season on the basketball-ref page
        """
        #print "Getting season urls from %d to %d" % (fr, to)
        seasonlines = filter(lambda l: True if "/leagues/" in l else False, urll.urlopen(baseurl+"/leagues/").readlines()) #Gets the lines with links to the actual seasons
        toIn = lambda s: True if str(to)+".html" in s else False
        fromIn = lambda s: True if str(fr)+".html" in s else False
        toIn = lambda s: True if str(to)+".html" in s else False
        assert(to>=1977)
        assert(fr<=2013)
        seasonlines.reverse()
        indexOfFrom = seasonlines.index(filter(fromIn,seasonlines)[0])
        indexOfTo = seasonlines.index(filter(toIn,seasonlines)[0])
        seasonlines = seasonlines[indexOfFrom:indexOfTo+2]
        seasonurls = map(lambda l: l.split('"')[3] if "light_text" not in l else l.split('"')[5], filter(lambda l: True if "-" in l else False, seasonlines)) #Removes duplicates and Cut the url of the season out of the html
        return map(lambda u: baseurl+u.split('.')[0] + "_games.html", seasonurls) #Do not parse 2013

    
    
    def parseSeasons(self,seasonUrls):
        """
        #Use: d = parseSeasons(SeasonUrls)
        #Pre: SeasonUrls is a list of urls to pages which contain information about games in tabular format
        #Post: d is a dictionary of dictionary's which keys are (League, Season), and the dictionaries each contain two entries, regular season and playoffs, which each contain a list of the games played in the regular season and playofss in the League in the Season respectively
        """
        #print "Parsing seasons"
        teamsandscores = lambda lines: map(lambda table: map(lambda row: map(lambda l: l.split(">")[2].split("<")[0] if ("teams" in l or "year"  in l) else l.split(">")[1].split("<")[0],row[1:2]+row[3:7]),table[1:]),self.parseTables(lines)) #Games of the file which lines are lines on the format [Date, Team 1, Score of Team 1, Team 2, Score of Team 2]
        seasonDict = lambda lines: dict(zip(["regular season","playoffs"],teamsandscores(lines))) #The seasons of the file which lines are lines
        triListToTuple = lambda lis: (lis[0],lis[1])
        return dict(zip(map(lambda season: triListToTuple(season.split('/')[-1:][0].split(".")[0].split("_")),seasonUrls), map(lambda season: seasonDict(urll.urlopen(season).readlines()),seasonUrls)))

    def parseTeamStats(self,teamUrls):
        teamStats = {}
        for url in teamUrls:
            lines = urll.urlopen(url).readlines()
            table = self.parseTables(lines)[0][1:] #Only one table per page, first column only states what is what
            splitTwoBraketFromLeft = lambda r: r.split("<")[2].split(">")[1]
            splitOneBraketFromLeft = lambda r: r.split("<")[1].split(">")[1]
            s1 = lambda r: splitOneBraketFromLeft(r)
            s2 = lambda r: splitTwoBraketFromLeft(r)
            season = lambda s: int(s.split(".html")[0].split("/")[-1:][0])
            table = map(lambda row: [season(row[1])] + map(lambda i:s2(row[i]),range(2,4)) + map(lambda i: s1(row[i]),range(4,11)),table)
            newerThan1977 = lambda s: True if s[0] >= 1977 else False
            table = filter(newerThan1977,table)
            table = map(lambda row: row[:3] + map(lambda s: int(s),row[3:5]) + map(lambda s: float(s),row[5:]),table)
            teamStats[table[0][2]] = table
        return teamStats

    def teamStatsToSql(self,teamStats):
        self.dbConn.execute("CREATE TABLE teamStats (season, league, team, win, lose, win_lose_ratio, finish, srs, offrtg,defrtg)")
        for team in teamStats:
            stats = map(lambda row: row[:2] + row[3:],teamStats[team])
            self.dbConn.executemany("Insert into teamStats values (?,?,'%s',?,?,?,?,?,?,?) " % (team), stats)
        self.dbConn.commit()
            
            

    def getTeamUrls(self):
        lines = urll.urlopen("http://www.basketball-reference.com/teams/").readlines()
        tables = self.parseTables(lines)
        for table in tables:
            teamUrlInSecond = lambda i: True if "/teams/" in i else False
            secondrows = map(lambda row: row[1],table)
            withUrls = filter(teamUrlInSecond,secondrows)
            urlStrings = map(lambda s: s.split(">")[1].split('"')[1], withUrls)
            return map(lambda s: "http://www.basketball-reference.com"+s,urlStrings)
            
        
    def getTeams(self):
        #returns a list of team names that correspond to the same team.
        lines = urll.urlopen("http://www.basketball-reference.com/teams/").readlines()
        tables = self.parseTables(lines)
        teamNames = []
        for table in tables:
            teamUrlInSecond = lambda i: True if "/teams/" in secondrows[i] else False
            teamUrlNotInSecond = lambda i: True if "/teams/" not in secondrows[i] else False
            teamNameWithUrl = lambda r: r.split("<")[2].split(">")[1]
            teamNameWithoutUrl = lambda r: r.split("<")[1].split(">")[1]
            secondrows = map(lambda row: row[1],table)
            #print secondrows
            withUrls = filter(teamUrlInSecond,range(len(secondrows)))
            withoutUrls = filter(teamUrlNotInSecond,range(len(secondrows)))[1:] #We don't want to include franchise
            allTeamNames = map(lambda i: teamNameWithUrl(secondrows[i]) if i in withUrls else teamNameWithoutUrl(secondrows[i]),range(len(secondrows)))
            namesOfTeams = []
            for j in withUrls: 
                namesOfTeam = [j]
                for i in range(j+1,len(allTeamNames)):
                    if i in withUrls:
                        break
                    namesOfTeam = namesOfTeam + [i] 
                namesOfTeams = namesOfTeams + [namesOfTeam]
            isToNames = lambda l : map(lambda i: allTeamNames[i],l)
            teamNames = teamNames + map(isToNames,namesOfTeams)
            break #Only do for non defunct teams
        return teamNames

    def teamNamesToSql(self, teamNames):
        #a table containing team names to real team name (latest team name and number
        self.dbConn.execute('CREATE TABLE teamNames (name, number,realname)')
        for (ind,name) in enumerate(teamNames):
            realname = name[0]
            for n in name:
                self.dbConn.execute("INSERT INTO teamNames VALUES ('%s', %d, '%s')" % (n,ind, realname))
        self.dbConn.commit()

    def teamsToSql(self):
        lines = urll.urlopen("http://www.basketball-reference.com/teams/").readlines()
        tables = self.parseTables(lines)
        self.dbConn.execute("CREATE TABLE teams (number,name,league,active_from,active_to,years,games,wins,losses,win_lose_ratio,playoffs,div,conf,champ)")
        numbernames = lambda x: list(self.dbConn.execute("select number from teamNames where realname='%s'"% (x)))[0][0]
        for table in tables:
            teamUrlInSecond = lambda row: True if "/teams/" in row[1] else False
            splitTwoBraketFromLeft = lambda r: r.split("<")[2].split(">")[1]
            splitOneBraketFromLeft = lambda r: r.split("<")[1].split(">")[1]
            s1 = lambda r: splitOneBraketFromLeft(r)
            s2 = lambda r: splitTwoBraketFromLeft(r)
            informativeRows = filter(teamUrlInSecond,table)
            informativeRows = map(lambda row: [numbernames(s2(row[1])), s2(row[1]), s1(row[2])] + map(lambda i: int(s1(row[i])),range(3,9)) + [float(s1(row[9]))] + map(lambda i: int(s1(row[i])),range(10,14)),informativeRows)
            self.dbConn.executemany("INSERT INTO teams values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", informativeRows)
            break #Only do for non defunct teams.
        self.dbConn.commit()
            
            
        

    def parseTables(self,lines):
        """
        #Use: l = Oc.parseTables(lines)
        #Pre: lines is a list of lines of a html file
        #Post: l is a list of lists, where each list it a table and the items in the list are the rows of that table
        """
        tableStartDef = lambda line: True if '<table class=' in line else False
        tableEndDef = lambda line: True if "</table>" in line else False
        rowstart = lambda row: True if row.startswith('<tr ') else False
        rowend = lambda row: True if row.startswith("</tr>") else False
        rowsoftable = lambda table: map(lambda k: list(takewhile(lambda x: not rowend(x),table[k:])),filter(lambda i: rowstart(table[i]),range(len(table)))) #A list of the rows of the table table.
        tables = lambda lines: map(lambda i: [lines[i]] + list(takewhile(lambda x: not tableEndDef(x),lines[i+1:])),filter(lambda i: tableStartDef(lines[i]),range(len(lines)))) #The tables in the file which lines are lines
        return map(rowsoftable,tables(lines))


    def changeData(self, fr,to, tableName = None): 
        """
        #Use: Oc.changeData(ifr,ito,tn)
        #Pre: ifr,ito is a year, ifr <= ito and are in range 1977 to 2013, tn is a tablename
        #Post: The data in the table tn now represents data from ifr to ito, the table Oc.tableName if tn is none.
        """
        tableExists = lambda tableName: False if len(list(self.dbConn.execute("select name from sqlite_master where type='table' and name = '%s'" % tableName))) < 1 else True #Checks whether the table exists.
        if tableName is None:
            tableName = self.tableName
        #Use views instead of tables, so we don't have to fetch the data all the time.
        self.dbConn.execute("DROP VIEW %s" % tableName)
        if self.calced:
            databaseTable = self.calcedDbTableName
        else:
            databaseTable = self.dbTableName
        self.dbConn.execute("CREATE VIEW %s as select * from %s where season >= %d and season <= %d order by date desc" % (tableName, databaseTable, fr,to))
        self.dbConn.commit()
        
        

    def getData(self, what,fr,to, condition = None):
       #data = list(self.dbConn.execute("select %s from %s where season >= %d and season <= %d" % (what,self.tableName,fr,to)))
       if condition is None:
           condition = "date >= '%s'" % fr
       dateToSeason = lambda date: int(date.split("-")[0]) + 1 if int(date.split("-")[1]) <= 9  else int(date.split("-")[0])
       if len(str(fr)) > 4 or len(str(to)) > 4:
           self.changeData(dateToSeason(fr),dateToSeason(to))
       else:
           self.changeData(fr,to)
       data = list(self.dbConn.execute("select %s from %s where date >= '%s' and date <= '%s' and %s" % (what,self.tableName,fr,to, condition)))
       return map(lambda x: list(x),data)

    
    def seasonsToSql(self, seasons, tableName = None, dbTableName = None, fr = 1977, to = 2012):
        """
        #Use: Sc.SeasonsToSql(seasons,name, tn, dbtn, fr,to)
        #Pre: name is a valid name for a database, seasons is a dictionary of dicitonaries with keys (League,Year), and values which are dictionaries, which contain lists of lists of five items, tn and dbtn are names of tables is sqllite3, fr to are years
        #Post: The dictionary seasons has been added to the database that dbConn is connected to, and the data put in dbtn and a view into it created as ttn.
        """
        #print "Inserting seasons into database"
        strToDate = lambda x: datetime.date.fromtimestamp(time.mktime(time.strptime(x,"%a, %b %d, %Y"))) #Turns the date format used on the site to a python date object
        c = self.dbConn.cursor()
        if dbTableName is None:
            dbTableName = self.dbTableName
        if tableName is None:
            tableName = self.tableName
        c.execute('CREATE TABLE %s (date, visitor_team,visitor_points,home_team,home_points,league, season, season_type)' % (dbTableName))
        try:
            for (seasonKey,season) in seasons.items():
                league,seasonYear = seasonKey
                for (seasonType,seasonGames) in season.items():
                    c.executemany("INSERT INTO %s VALUES (?,?,?,?,?,?,?,?)" % (dbTableName),map(lambda x: [strToDate(x[0]),x[1],int(x[2]),x[3],int(x[4]),league,int(seasonYear),seasonType],seasonGames))
            self.dbConn.execute("CREATE VIEW %s as select * from %s where season >= %d and season <= %d" % (tableName, dbTableName, fr,to))
            self.dbConn.commit()
        except OverflowError:
                print "Overflow error when converting time. Either a date is invalid, or interpeter can't handle the date. Please test on 64-bit system"
            
    def writeToFile(self,filename="seasons.txt"):
        fileToWriteTo = open("seasons.txt","w")
        fileToWriteTo.write(str(self.parseSeasons(self.getSeasonUrls())))
        fileToWriteTo.close()
    
    def calcLastGamesForDatabase(self, periodFrom = 2000, periodTo= 2012, tableName = "calcedDBTable"):
        tableExists = lambda tableName: False if len(list(self.dbConn.execute("select name from sqlite_master where type='table' and name = '%s'" % tableName))) < 1 else True #Checks whether the table exists.
        outcome = lambda li: (li[2]-li[4]) if li[1] == str(home) else (li[4]-li[2])

        if not tableExists(tableName):
            self.dbConn.execute("CREATE TABLE %s (date, visitor_team, visitor_points, home_team, home_points, league, season, season_type, last, last2, last3, last4, last5, last6,last7,last8,last9,last10)" % (tableName))
            games = self.dbConn.execute("select * from databaseTable where season >= ? and season <= ? order by date desc",(periodFrom,periodTo))
        else:
            date = list(list(self.dbConn.execute("select date from %s order by date asc limit 1" % (tableName)))[0])[0]
            games = self.dbConn.execute("select * from databaseTable where season >= ? and season <= ? and date < '%s' order by date desc" % (date) ,(periodFrom,periodTo))

        for game in games:
            hhvvdn = map(lambda i: (game[1],game[1],game[3],game[3],game[0],i),range(1,11))
            outcome = lambda li: (li[2]-li[4]) if li[1] == str(game[1]) else (li[4]-li[2])
            lasts = map(lambda h: sum([0]+map(outcome,list(self.dbConn.execute('select * from databaseTable where (home_team = ? or visitor_team = ?) and (home_team = ? or visitor_team = ?) and date < ? order by date desc limit ? ' , h)))), hhvvdn)        
            k = tuple(list(game)+lasts)
            print k
            self.dbConn.execute("INSERT INTO %s VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)" %(tableName), tuple(list(game)+lasts))
            self.dbConn.commit()
        self.dbConn.commit()


    def scheduleToSql(self, seasons, scheduleName = "Schedule"):
            strToDate = lambda x: datetime.date.fromtimestamp(time.mktime(bbRefToISO(x)))
            bbRefToISO = lambda x: time.strptime(x,"%a, %b %d, %Y") #Turns the date format used on the site to a python date object
            today = datetime.datetime.date(datetime.datetime.now())
            c = self.dbConn.cursor()

            c.execute('CREATE TABLE %s (date, visitor_team,home_team,league, season, season_type)' % (scheduleName))
            try:
                for (seasonKey,season) in seasons.items():
                    league,seasonYear = seasonKey
                    for (seasonType,seasonGames) in season.items():
                        seasonGames = filter(lambda x: True if strToDate(x[0]) >= today  else False, seasonGames) #Only fetch unplayed games
                        c.executemany("INSERT INTO %s VALUES (?,?,?,?,?,?)" % (scheduleName),map(lambda x: [strToDate(x[0]),x[1],x[3],league,int(seasonYear),seasonType],seasonGames))
                self.dbConn.commit()
            except OverflowError:
                    print "Overflow error when converting time. Either a date is invalid, or interpeter can't handle the date. Please test on 64-bit system"


if __name__== '__main__':
    Sc = OracleScraper(databaseName = "ScheduleTest.db", fetchData = False, calc = False)
    #Sc.teamStatsToSql(Sc.parseTeamStats(Sc.getTeamUrls()))
    # Sc.writeToFile()

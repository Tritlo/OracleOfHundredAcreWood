#!/usr/bin/env python
#encoding utf8
#Copyright (C) 2013 Matthías Páll Gissurarson & Sólrún Halla Einarsdóttir. See LICENSE for details.
from OracleScraper import OracleScraper
from Oracle import Oracle
import unittest
from datetime import date
import time
from optparse import OptionParser
import warnings

parser = OptionParser()
parser.add_option("-f",action="store_true",dest="fast", default = False)
(options,args) = parser.parse_args()

#Use -f to skip long test that are already cleared. Be sure to run them sometimes though!

class testOracle(unittest.TestCase):
    def setUp(self):
        self.Oc = Oracle(databaseName =":memory:",fr = 2009, to = 2012, calcFrom = 2009, calcTo=2012,calc=False)

    @unittest.skipIf(options.fast,"skipping for fast testing")
    def test_predict(self):
        self.Oc.train()
        pr = self.Oc.predict("Los Angeles Lakers","Boston Celtics",2012,"2012-02-03")
        self.assertIn(pr,["Los Angeles Lakers", "Boston Celtics"])

    @unittest.skipIf(options.fast,"skipping for fast testing")
    def test_train(self):
        self.Oc.train()
        pr = self.Oc.predict("Los Angeles Lakers","Boston Celtics",2012,"2012-02-03")
        self.assertIn(pr,["Los Angeles Lakers", "Boston Celtics"])

    @unittest.skipIf(options.fast,"skipping for fast testing")
    def test_evaluate(self):
        for model in self.Oc.models:
                self.Oc.switchModel(model)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    ev = self.Oc.evaluate()
                    self.assertLessEqual(ev,1)
                    self.assertGreaterEqual(ev,0)
        
class testOracleScraper(unittest.TestCase):

    def setUp(self):
        self.St = OracleScraper(databaseName = ":memory:", fetchData = False,fr = 2009, to = 2012,calc = False)

    def test_getSeasonUrls(self):
        urls = self.St.getSeasonUrls(fr=1969,to=2012)
        self.assertIn("http://www.basketball-reference.com/leagues/NBA_1969_games.html",urls)
        self.assertNotIn("http://www.basketball-reference.com/leagues/NBA_984_games.html",urls)

    def test_parseSeasons(self): 
        urls = ["http://www.basketball-reference.com/leagues/NBA_1969_games.html"]
        results = self.St.parseSeasons(urls)
        results = results[("NBA","1969")]
        results = results["playoffs"]
        self.assertIn(["Tue, Apr 29, 1969", "Los Angeles Lakers", "88", "Boston Celtics","89"],results)
        self.assertNotIn(["Tue, Apr 29, 1969", "Los Angeles Lakers", "88", "Boston Celtics","87"],results)
        self.assertIn(["Fri, Apr 18, 1969", "New York Knicks", "105", "Boston Celtics","106"],results)
            
    def test_seasonsToSql(self):
        urls = ["http://www.basketball-reference.com/leagues/NBA_1969_games.html"]
        results = self.St.parseSeasons(urls)
        self.St.seasonsToSql(seasons = results, dbTableName = "testdata")
        res = list(self.St.dbConn.execute("select date,visitor_team,visitor_points from testdata where home_team='Boston Celtics'"))
        self.assertIn((str(date(1969,4,29)),'Los Angeles Lakers',88),res)
        self.assertNotIn((str(date(1969,4,15)),'Boston Celtics',87),res)
        self.assertIn((str(date(1969,4,18)),'New York Knicks',105),res)

    def test_getTeams(self):
        lis = self.St.getTeams()
        self.assertIn(["Atlanta Hawks","Atlanta Hawks", "St. Louis Hawks", "Milwaukee Hawks", "Tri-Cities Blackhawks"],lis)
        self.assertIn(["Boston Celtics"],lis)
        self.assertNotIn(["Reykjavik Penguins"],lis)

    def test_getTeamUrls(self):
        urls = self.St.getTeamUrls()
        self.assertIn("http://www.basketball-reference.com/teams/ATL/",urls)
        self.assertNotIn("http://www.basketball-reference.com/leagues/RPG/",urls)
    
    def test_teamNamesToSql(self):
        self.St.teamNamesToSql(self.St.getTeams())
        results = map(lambda x: list(x)[0],list(self.St.dbConn.execute("select name from teamNames")))
        self.assertIn("Boston Celtics",results)
        self.assertIn("Chicago Bulls",results)
        self.assertNotIn("Reykjavik Penguins",results)

    def test_teamsToSql(self):
        self.St.teamNamesToSql(self.St.getTeams())
        self.St.teamsToSql()
        results = map(lambda x: list(x), list(self.St.dbConn.execute("select * from teams")))
        self.assertTrue(len(results[0]) == 14)
        self.assertIn("Atlanta Hawks", results[0])
        self.assertNotIn("Reykjavik Polar", results[0])
        
    def test_parseTeamStats(self):
        results = self.St.parseTeamStats(["http://www.basketball-reference.com/teams/ATL/"])
        self.assertIn("Atlanta Hawks", results)
        self.assertTrue(len(results["Atlanta Hawks"][0]) == 10)
        self.assertNotIn("Reykjavik Polar", results)
        
    def test_teamStatsToSql(self):
        self.St.teamStatsToSql(self.St.parseTeamStats(["http://www.basketball-reference.com/teams/DEN/"]))
        results = map(lambda x: list(x), list(self.St.dbConn.execute("select * from teamStats")))
        self.assertTrue(len(results[0]) == 10)
        self.assertIn([1990,'NBA', 'Denver Nuggets', 43, 39,0.524,4.0,1.56,108.0,106.7], results)
    
if __name__== '__main__':
    global fast
    fast = options.fast
    unittest.main(verbosity=2, exit=False)

#!/usr/bin/env python
#encoding utf8
#Copyright (C) 2013 Matthías Páll Gissurarson & Sólrún Halla Einarsdóttir. See LICENSE for details.
import unittest
import urllib2 as urll
from OracleServer import *
import urllib
from cookielib import CookieJar


class testOracleServer(unittest.TestCase):
    
    def setUp(self):
        self.location = 'http://localhost:8080/'
        cj = CookieJar()
        self.site = urll.build_opener(urll.HTTPCookieProcessor(cj))
        headers = {'User-Agent': ' Mozilla/5.0 (Windows NT 5.1; rv:10.0.1) Gecko/20100101 Firefox/10.0.1', 'Cookie': 'user=tester'}
        self.site.addheaders = headers.items()
        
        self.site.open(self.location + 'doRegister?user=tester&pass=tester') #Skraum okkur a siduna
        self.site.open(self.location + 'loginCheck?user=tester&pass=tester')
  
    def test_register(self):
        regsite = self.site.open(self.location + '/register').read()
        self.assertTrue('Register' in regsite)
        self.assertTrue('Login' in regsite)
        #Tester is already registered, not allowed
        regsite = self.site.open(self.location + 'doRegister?user=tester&pass=tester').read()
        self.assertTrue('incorrect' in regsite)
        self.site.open(self.location + 'dropUsers')
        regsite = self.site.open(self.location + 'doRegister?user=othertester&pass=tester').read() 
        self.assertFalse('User alread exists' in regsite)
        #Cleanup
        self.site.open(self.location + 'doRegister?user=tester&pass=tester') #Skraum okkur a siduna
        self.site.open(self.location + 'loginCheck?user=tester&pass=tester')

    def test_loginSite(self):
        #test whether the login lets unlogged users in
        loginsite = self.site.open(self.location + 'loginpage').read() 
        self.assertTrue('Login' in loginsite)
        loginsite = self.site.open(self.location + 'loginCheck?user=tester&pass=tester').read() 
        self.assertTrue('incorrect' not in loginsite)
        loginsite = self.site.open(self.location + 'loginCheck?user=tester&pass=nottester').read()
        self.assertTrue('incorrect' in loginsite)
        loginsite = self.site.open(self.location + 'loginCheck?user=nottester&pass=nottester').read() 
        self.assertTrue('incorrect' in loginsite)

    def test_login(self): 
        predictsite = self.site.open(self.location + 'spadispilin').read()
        self.assertTrue('Predict' in predictsite) #Should let us in, as we've registered tester already.
    def test_prediction(self):
        predictsite = self.site.open(self.location + 'spadispilin?home=Chicago+Bulls&visitor=Oklahoma+City+Thunder').read()
        self.assertTrue('The predicted winner, using' in predictsite and ( 'Oklahoma City Thunder' in predictsite or 'Chicago Bulls'  in predictsite))
            
    def testCredits(self):
         predictsite = self.site.open(self.location + 'spadispilin&morecredits').read()
         self.assertTrue('Insufficient' not in predictsite)
         for i in range(20):
             predictsite = self.site.open(self.location + 'spadispilin?home=Chicago+Bulls&visitor=Oklahoma+City+Thunder').read()

         self.assertTrue('Insufficient' in predictsite)
         #Have credits for other tests
         self.site.open(self.location + 'spadispilin&morecredits').read()
         self.site.open(self.location + 'spadispilin&morecredits').read()
        
    def test_schedule(self):
         schedulesite = self.site.open(self.location + 'schedule')
         self.assertTrue('The upcoming games in the NBA are:' in schedulesite.read())
        
    def test_settings(self):
         schedulesite = self.site.open(self.location + 'settings').read()
         self.assertTrue('Model:' in schedulesite)
         settingsset = self.site.open(self.location + 'setSettings?model=always_home&nlg=3&trainfrom=2009&trainto=2012&rfEst=100&kNK=38&mStats=win_lose_ratio&mStats=finish&mStats=srs&mStats=offrtg&mStats=defrtg')
         predictsite = self.site.open(self.location + 'spadispilin?home=Chicago+Bulls&visitor=Oklahoma+City+Thunder').read()
         self.assertTrue('always_home' in predictsite)
         settingsset = self.site.open(self.location + 'setSettings?model=randomForest&nlg=3&trainfrom=2006&trainto=2012&rfEst=5&kNK=38&mStats=win_lose_ratio&mStats=finish&mStats=srs&mStats=offrtg&mStats=defrtg')
         predictsite = self.site.open(self.location + 'spadispilin?home=Chicago+Bulls&visitor=Oklahoma+City+Thunder').read()
         self.assertTrue('randomForest' in predictsite)
         settingsset = self.site.open(self.location + 'setSettings?model=random&nlg=3&trainfrom=2006&trainto=2012&rfEst=5&kNK=38&mStats=win_lose_ratio&mStats=finish&mStats=srs&mStats=offrtg&mStats=defrtg')
         hey = settingsset.read()
         
    def test_argumentsToDict(self):
        BullsLakers=argumentsToDict('spadispilin?home=Chicago+Bulls&visitor=Los+Angeles+Lakers')
        self.assertEqual(BullsLakers["home"],'Chicago Bulls')
        self.assertEqual(BullsLakers["visitor"],'Los Angeles Lakers')

if __name__== '__main__':
    unittest.main(verbosity=2, exit=False)
    print "Note that the server must be running on port 8080 for this to work"

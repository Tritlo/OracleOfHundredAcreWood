#!/usr/bin/env python
# coding: utf-8
#Copyright (C) 2013 Matthías Páll Gissurarson & Sólrún Halla Einarsdóttir. See LICENSE for details.
import sqlite3 as sql
import itertools
from OracleScraper import OracleScraper
import random as rnd
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import confusion_matrix


class Oracle:

    Odb = None #Connection to the statsdatabase, initialized on init.
    model = "random" #The Current model
    estimator = None
    models = ["random","always_home","always_visitor","randomForest","kNeighbors","gradientBoosting"]
    modelStats = "win_lose_ratio, finish, srs, offrtg, defrtg"
    modelStatsAvailable = ["win_lose_ratio", "finish", "srs", "offrtg", "defrtg","win","lose"]
    dateToInt = lambda s, d: int(d.split("-")[0])*10000 + int(d.split("-")[1])*100 + int(d.split("-")[2])
    randomForestEstimators = 100
    kNearestK = 38
    numberOfLastGames = 3
    trained = False
    trainedFrom = 2009
    trainedTo = 2012

    
    def __init__(self, databaseName="StatsDatabase.db", model = "random", fr = 1977, to = 2012,calcFrom = 2000, calcTo=2012, calc = True): #Data is from 1969, but there were defunct teams all to 1976
        """
        #Use: Oc = Oracle(db,model,fr,to)
        #Pre: db is a name of a file containing an sql database or an empty file, model is a string that is the model to be used, fr and to is a valid season year.
        #Post Oc is a new Oracle object connected to the database db and with the model model.
        """
        assert(fr >= 1977)
        assert(to <= 2012)
        assert(fr <= to)
        assert(calcTo <= to)
        assert(calcFrom >=fr)
        self.Odb = OracleScraper(databaseName=databaseName, fr = fr, to = to,calcFrom = calcFrom, calcTo = calcTo,calc = calc)
        self.model = model

    def numbernames(self,name):
        return list(self.Odb.dbConn.execute("select number from teamNames where name='%s'"% (name)))[0][0]

    def evaluations(self, number,evalFrom = "2011-01-01", evalTo = "2013-12-31", trainFrom = "2008-01-01", trainTo = "2010-12-31"):
        evals = []
        for i in range(n):
                e =  self.evaluate(evalFrom,evalTo,trainFrom,trainTo)
                print e
                evals = evals + [e]
        return [min(evals), sum(evals)/n, max(evals)]

        
    def evaluate(self,evalFrom = "2011-01-01", evalTo = "2013-12-31", trainFrom = "2008-01-01", trainTo = "2010-12-31"):
        """
        #Use: p = oc.evaluate(ef,et,tf,tt)
        #Pre: ef,et,tf and tt are valid dates
        #Post:p is the percentage of the time the current model was correct trained with data from tf to tt and evaluated from ef to et. 
        """
        winner = lambda l: l[0] if l[1] > l[3] else "" if l[1] == l[3] else l[2]
        data = self.Odb.getData("home_team,home_points, visitor_team, visitor_points, season, date",evalFrom,evalTo)
        assert(len(data) != 0) 
        self.train(dataFrom = trainFrom, dataTo = trainTo) 
        pre = lambda l: self.predict(l[0],l[2],l[4],l[5])
        predictions = map(pre,data)
        winners = map(winner,data)
        correctPoints = lambda (x,y): 1 if x==y else 0
        return sum(map(correctPoints,zip(predictions,winners)))/float(len(data))


    def train(self, data = None, dataFrom = trainedFrom, dataTo = trainedTo):
        """
        #Use: oc.train(d,df,dt)
        #Pre: df and dt are valid dates, data is either none or data to use to train.
        #Post: The current model has been trained with the data in data.
        """
        self.trainedFrom = dataFrom
        self.trainedTo = dataTo
        doesNotUseData = ["random","always_home","always_visitor"]
        trainingDict = {\
                "random": (lambda x,y: None),\
                "always_home":(lambda x,y: None),\
                "always_visitor": (lambda x,y: None),\
                "randomForest": self.train_estimator,\
                "kNeighbors": self.train_estimator,\
                "gradientBoosting": self.train_estimator
                }
        #if data is None and self.model not in doesNotUseData:
        #    data = self.Odb.getData("home_team, home_points, visitor_team, visitor_point", dataFrom,dataTo)
        trainingDict[self.model](dataFrom,dataTo)


    
    def predict(self, home_team, visitor_team, season = None ,date = None):
        """
        #Use: p = oc.predict(ht,vt)
        #Pre: ht and vt are valid teams
        #Post: p is the predicted winner of the game between ht and vt.<
        """
        if date is None and season is None:
            l = list(self.Odb.dbConn.execute("select season,date from calcedDbTable where (home_team = '%s' or visitor_team = '%s') and (home_team = '%s' or visitor_team = '%s') order by date asc limit 1" % (home_team, home_team, visitor_team, visitor_team)))
            if len(l) > 0:
                season,date = l[0]
            else:
                return home_team

        predictDict = {\
                "random": (lambda a, b,s,d: a if rnd.random() < 0.5 else b),\
                "always_home": (lambda a,b,s,d: a),\
                "always_visitor": (lambda a,b,s,d: b),\
                "randomForest": self.predict_estimator,\
                "kNeighbors": self.predict_estimator,\
                "gradientBoosting": self.predict_estimator
                }
        return predictDict[self.model](home_team,visitor_team, season,date)

   
    def switchModel(self, model, modelStats = modelStats, kNearestK = kNearestK, randomForestEstimators = randomForestEstimators, numberOfLastGames = numberOfLastGames):
        """
        #Use: oc.switchModel(m)
        #Pre: m is a valid model
        #Post: The current model has been set to m.
        """
        self.estimator = None
        self.trained = False 
        if model == "randomForest":
            self.estimator = RandomForestClassifier(n_estimators=self.randomForestEstimators)
        elif model == "kNeighbors" :
            self.estimator = KNeighborsClassifier(self.kNearestK)
        elif model == "gradientBoosting" :
            self.estimator = GradientBoostingClassifier()
        else:
            self.estimator = None
            self.trained = True
        self.model = model
        self.modelStats = modelStats
        self.kNearestK = kNearestK
        self.numberOfLastGames = numberOfLastGames
        self.randomForestEstimators = randomForestEstimators

    def train_estimator(self,dataFrom,dataTo):
        data = self.Odb.getData("home_team,home_points, visitor_team, visitor_points, season, date",dataFrom,dataTo)
        outcome = lambda l: 0 if l[1] > l[3] else 1
        target = map(outcome,data)
        train = map(lambda x: self.estimatorInformationExtractor(x),data)
        self.estimator.fit(train,target)

    def getProbHome(self, home_team, visitor_team, season = None ,date = None):
        if date is None and season is None:
            l = list(self.Odb.dbConn.execute("select season,date from calcedDbTable where (home_team = '%s' or visitor_team = '%s') and (home_team = '%s' or visitor_team = '%s') order by date asc limit 1" % (home_team, home_team, visitor_team, visitor_team)))
            if len(l) > 0:
                season,date = l[0]
            else:
                return 0.6

        probDict = {\
                "random": (lambda a, b,s,d: float(0.5)),\
                "always_home": (lambda a,b,s,d: float(0.6)),\
                "always_visitor": (lambda a,b,s,d: float(0.6)),\
                "randomForest": self.predict_proba_estimator,\
                "kNeighbors": self.predict_proba_estimator,\
                "gradientBoosting": self.predict_proba_estimator
                }
        
        return probDict[self.model](home_team,visitor_team, season,date)
        
    def predict_estimator(self,home_team,visitor_team,season,date):
        test = self.predict_list(home_team,visitor_team,season,date)
        pred=self.estimator.predict(test)
        return home_team if pred[0] == 0 else visitor_team

    def predict_proba_estimator(self,home_team,visitor_team,season,date):
        test = self.predict_list(home_team,visitor_team,season,date)
        pred=self.estimator.predict_proba(test)
        return pred[0][0]
    
    def  informationExtractor(self, game):
        htName = list(list(self.Odb.dbConn.execute('select realname from teamNames where name = "%s"' % (game[0])))[0])[0]
        vtName = list(list(self.Odb.dbConn.execute('select realname from teamNames where name = "%s"' % (game[2])))[0])[0]
        ht = list(list(self.Odb.dbConn.execute("select %s from teamStats where team = '%s' and season = %d" % (self.modelStats,str(htName),game[4]-1)))[0]) #must have it be last season, or else we'd be cheating.
        vt = list(list(self.Odb.dbConn.execute("select %s from teamStats where team = '%s' and season = %d" % (self.modelStats,str(vtName),game[4]-1)))[0])
        return (htName,vtName,ht,vt,self.lastNres(game[0],game[2],game[5]))


    def lastNres(self,home,vis,date,n = numberOfLastGames):
        #last = self.Odb.dbConn.execute('select home_team, home_points, visitor_team, visitor_points from data where (home_team = "%s" or visitor_team = "%s") and (home_team = "%s" or visitor_team = "%s") and date < "%s" order by date desc limit %d' % (home,home,vis,vis,date,n))
        if not self.Odb.calced:
            return [0]
        st = "last%d" % (n) if n != 1 else "last"
        last = list(self.Odb.dbConn.execute('select %s from data where home_team = ? and visitor_team = ? and date == ? limit ? '% (st),(home,vis,date,n)))
        return [last[0][0]]  if len(last) > 0 else [0]

    def estimatorInformationExtractor(self,game):
        htName,vtName,ht,vt,last5results = self.informationExtractor(game)
        return [self.numbernames(game[0]),self.numbernames(game[2]),game[4]]+ht+vt+last5results
      
    def predict_list(self,home_team,visitor_team,season,date):
        game = [home_team,0,visitor_team,0,season,date]
        htName,vtName,ht,vt,lstN = self.informationExtractor(game)
        test = [[self.numbernames(home_team),self.numbernames(visitor_team),season]+ht+vt+lstN]
        return test

    def get_confusion_matrix(self,evalFrom = "2011-01-01", evalTo = "2013-12-31", trainFrom = "2008-01-01", trainTo = "2010-12-31"):
        winner = lambda l: l[0] if l[1] > l[3] else "" if l[1] == l[3] else l[2]
        data = self.Odb.getData("home_team,home_points, visitor_team, visitor_points, season, date",evalFrom,evalTo)
        assert(len(data) != 0) 
        self.train(dataFrom = trainFrom, dataTo = trainTo) 
        pre = lambda l: self.predict(l[0],l[2],l[4],l[5])
        home = lambda l: l[0]
        homes = map(home,data)
        predictions = map(pre,data)
        winners = map(winner,data)
        listToHomes = lambda li: map(lambda i: 1 if homes[i] == li[i] else 0, range(len(li)))
        predHomes = listToHomes(predictions)
        winnerHomes = listToHomes(winners)
        return confusion_matrix(winnerHomes,predHomes)




if __name__== '__main__':
    Or = Oracle()
    n = 3
    Or.switchModel('gradientBoosting')
    print Or.get_confusion_matrix() 
    print Or.evaluations(n)
    for model in Or.models:
         print "evaluating %s" % (model)
         Or.switchModel(model)
         ev = Or.evaluations(n)
         print "%s using %s from previous season predicts correctly with a min probability of %3f, average probability of %3f, and max probabilty of %3f over %d tries" % (Or.model, Or.modelStats,ev[0],ev[1],ev[2],n)
         print "Confusion matrix for %s" % (model)
         print Or.get_confusion_matrix() 
    # for model in Or.models:
    #     print "evaluating %s" % (model)
    #     Or.switchModel(model)
    #     print "%s using %s from previous season predicts correctly with a min probability of %3f, average probability of %3f, and max probabilty of %3f over %d tries" % (Or.model, Or.modelStats,ev[0],ev[1],ev[2],n)

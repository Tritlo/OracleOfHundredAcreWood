#!/usr/bin/env python
# coding: utf-8
#Copyright (C) 2013 Matthías Páll Gissurarson & Sólrún Halla Einarsdóttir. See LICENSE for details.
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import sqlite3 as sql
import itertools
from hashlib import sha256
from OracleScraper import OracleScraper
from optparse import OptionParser
from Oracle import Oracle
import logging


def argumentsToDict(path):
    argdict = {}
    if '?' in path:
        args = path.split('?')[1].split('&')
        for arg in args:
            sp = arg.split("=")
            if sp[0] not in argdict:
                argdict[sp[0]] = " ".join(sp[1].split("+"))
            else:
                argdict[sp[0]] = argdict[sp[0]] + ", "+ " ".join(sp[1].split("+"))
    return argdict

def printHeader(self, user = None , cookies = True):
    self.send_response(200)
    self.send_header('Content-type','text/html')
    if cookies:
        if user is not None:
            self.send_header('Set-Cookie','user=%s'% (user))
        else:
            self.send_header('Set-Cookie','user=none; expires=Thu, 01 Jan 1970 00:00:00 GMT')
    self.end_headers()
    self.wfile.write('<html>')
    cssFile= open("Oracle.css","r")
    css = cssFile.read()
    cssFile.close()
    self.wfile.write("<head> <title>Oracle of Hundred Acre Wood</title>" +css+ "</head>")
    self.wfile.write('<p><img src="http://notendur.hi.is/mpg3/bb.png"></p><body>')


def printMenu(self,user):
    if user is not None:
        credits = list(UserDatabase.execute('select credits from Users where user = ?', (user,)))[0][0]
        credits =  '<th>Credits: %d</th>' % (credits)
    else:
        credits = ""
    menuString = """
    <table class="menu">
    <tr>
    <th class="link"><a href="/logout">Logout</a></th>
    <th class="link"><a href="/spadispilin&morecredits">Get more credits!</a></th>
    <th class="link"><a href="/settings">Settings</a></th>
    <th class="link"><a href="/schedule">Schedule</a></th>
    """
    self.wfile.write( menuString + credits + '<tr> </table>')
    
def printSettings(self,user):
    printHeader(self,user)
    self.wfile.write('<h3 >Select the Settings you would like the Oracle to use:')
    self.wfile.write('<form name = "input",  method="get", action="/setSettings" >')
    self.wfile.write('Model: <select name= "model"> ')
    for model in Or.models:
        if model == Or.model:
            self.wfile.write('<option selected="selected" value =  "%s"> %s </option>' % (model,model))
        else:
            self.wfile.write('<option value =  "%s"> %s </option>' % (model,model))
    self.wfile.write("</select><br>")

    self.wfile.write('Number of last games: <select name= "nlg"> ')
    for i in range(1,11):
        if i == Or.numberOfLastGames:
            self.wfile.write('<option selected="selected" value =  "%d"> %d </option>' % (i,i))
        else:
            self.wfile.write('<option value =  "%d"> %d </option>' % (i,i))
    
    self.wfile.write("</select><br>")
    
    min, max = 2006,2013 
    self.wfile.write('Season to train model from: <select name= "trainfrom"> ')
    for i in range(min,max):
        if i == Or.trainedFrom:
            self.wfile.write('<option selected="selected" value =  "%d"> %d </option>' % (i,i))
        else:
            self.wfile.write('<option value =  "%d"> %d </option>' % (i,i))
    self.wfile.write("</select><br>")
    self.wfile.write('Season to train model to: <select name= "trainto"> ')
    for i in range(min,max):
        if i == Or.trainedTo:
            self.wfile.write('<option selected="selected" value =  "%d"> %d </option>' % (i,i))
        else:
            self.wfile.write('<option value =  "%d"> %d </option>' % (i,i))
    self.wfile.write("</select><br>")
    
    self.wfile.write('Number of randomForesEstimators: <select name= "rfEst"> ')
    for i in range(1,201):
        if i == Or.randomForestEstimators:
            self.wfile.write('<option selected="selected" value =  "%d"> %d </option>' % (i,i))
        else:
            self.wfile.write('<option value =  "%d"> %d </option>' % (i,i))
    
    self.wfile.write("</select><br>")

    self.wfile.write('KNearestNeighbors K: <select name= "kNK"> ')
    for i in range(2,101):
        if i == Or.kNearestK:
            self.wfile.write('<option selected="selected" value =  "%d"> %d </option>' % (i,i))
        else:
            self.wfile.write('<option value =  "%d"> %d </option>' % (i,i))

    self.wfile.write("</select><br>")
    
    self.wfile.write("Stats from last season used in model:<br>")
    mStats = Or.modelStats.split(', ') 
    for (i,stat) in enumerate(Or.modelStatsAvailable):
        if i == 4:
            self.wfile.write("<br>")
        if stat in mStats:
            self.wfile.write('<input type="checkbox" name="mStats" value="%s" checked> %s ' % (stat,stat))
        else:
            self.wfile.write('<input type="checkbox" name="mStats" value="%s"> %s ' % (stat,stat))

    self.wfile.write('<br><input type="submit"  value="Switch model and train"></form>')  
    self.wfile.write('<a href="/spadispilin"> Go back </a>')      
    self.wfile.write('</body></html>')


def setSettings(self,argdict):
    if 'model' in argdict:
        model = argdict["model"]
    else:
        model = Or.model()
    if 'rfEst' in argdict:
        rfEst = int(argdict["rfEst"])
    else:
        rfEst = Or.randomForestEstimators
    
    if 'numLastGames' in argdict:
        nlg = int(argdict["numLastGames"])
    else:
        nlg = Or.numberOfLastGames

    if 'kNK' in argdict:
        kNK = int(argdict["kNK"])
    else:
        kNK = Or.kNearestK
    
    if 'trainto' in argdict and 'trainfrom' in argdict:
        tto = int(argdict["trainto"])
        tfr = int(argdict["trainfrom"])
        if tto > tfr:
            tt = tto
            tf = tfr
        else:
            tt = Or.trainedTo
            tf = Or.trainedFrom
    else:
        tt = Or.trainedTo
        tf = Or.trainedFrom
        
    if 'mStats' in argdict:
        mStats = argdict["mStats"]
    else:
        mStats = Or.modelStats

    
    Or.switchModel(model,randomForestEstimators = rfEst, kNearestK = kNK, numberOfLastGames = nlg, modelStats = mStats)
    print "Training model..."
    Or.train(dataFrom=tf,dataTo=tt)
    print "Training model... Done"
    self.path = "/spadispilin"

def printSelection(self,argdict, item,default):
    self.wfile.write('<th> %s team: <select name= "%s"> ' % (item.title(),item))
    for name in teamNames:
        if item in argdict:
            if name == argdict[item]:
               self.wfile.write('<option selected = "selected" value =  "%s">' % (name))
            else:
               self.wfile.write('<option  value =  "%s">' % (name))
        elif name == default:
            self.wfile.write('<option selected = "selected" value =  "%s">' % (name))
        else:
            self.wfile.write('<option  value =  "%s">' % (name))
                
        self.wfile.write(name)
        self.wfile.write('</option>')
    self.wfile.write('</select></th>')

def printPredictInterface(self,argdict, user = None):
    printHeader(self,user)
    printMenu(self,user)
    self.wfile.write('<h3>Select the teams you would like an Oracle prediction for, %s: </h3>' % (user.title()))
    self.wfile.write('<form name = "input",  method="get", action="spadispilin" >')
    self.wfile.write('<table class="center">')
    self.wfile.write('<tr>')
    printSelection(self,argdict,"home","Chicago Bulls")
    self.wfile.write(' <th> vs. </th> ')
    printSelection(self,argdict,"visitor","Oklahoma City Thunder")
    self.wfile.write('</tr>')
    self.wfile.write("</table>")
    self.wfile.write('<p ><input type="submit"  value="Predict!"></p></form>')  


def printSchedule(self,user):
    printHeader(self,user)
    schedule=list(Or.Odb.dbConn.execute("select date, home_team, visitor_team, season_type from Schedule order by date asc limit 10"))
    self.wfile.write('<h3 >The upcoming games in the NBA are: </h3>')
    self.wfile.write('<p>(Click on a game to make prediction for that game or <a href="/spadispilin"> here to go back</a>) </p>')
    self.wfile.write('<table class="schedule">')
    self.wfile.write('<tr><th class="schedule">Date</th><th class="schedule">Game</th><th class="schedule">Regular or Playoffs</th></tr>')      
    for (i,game) in enumerate(schedule):
        (date,home,visitor,styp) = game
        if not i == len(schedule)-1:
            self.wfile.write('<tr><th class="schedule">%s</th><th class="schedule link"><a href="/spadispilin?home=%s&visitor=%s">%s vs %s</a> </th><th class="schedule"> %s </a></th></tr>' % (date,'+'.join(home.split()),'+'.join(visitor.split()),home,visitor,styp))
        else:
            self.wfile.write('<tr><th>%s</th><th class="link"><a href="/spadispilin?home=%s&visitor=%s">%s vs %s</a> </th><th> %s </a></th></tr>' % (date,'+'.join(home.split()),'+'.join(visitor.split()),home,visitor,styp))
    
    self.wfile.write('</table>')
    self.wfile.write('<p ><a href="/spadispilin"> Go back </a></p>')      

def printEnd(self):
    self.wfile.write('</body></html>')

def decreaseCredits(self,argdict,user):
    if 'home' not in argdict or 'visitor' not in argdict:
        return
    credits = list(UserDatabase.execute('select credits from Users where user = ?', (user,)))[0][0]
    if credits > 0:
        UserDatabase.execute('update Users set credits = credits - 1 where user = ?', (user,))
        
def printPrediction(self,argdict,user):
    if 'home' not in argdict or 'visitor' not in argdict:
        return
    credits = list(UserDatabase.execute('select credits from Users where user = ?', (user,)))[0][0]
    if credits > 0:
        if argdict["home"] == argdict["visitor"]:
            self.wfile.write('<p > Teams can\'t play themselves! Try again</p>' )
        else: 
            try:
                prediction = Or.predict(argdict["home"],argdict["visitor"])
                prob = Or.getProbHome(argdict["home"],argdict["visitor"])
            except IndexError: #Ef e-d bilar, t.d. ef lidin hafa ekki spilad nogu marga leiki, tha getum vid bara giskad a heima lidid, thad besta sem vid getum gert.
                prediction = HomeGuesser.predict(argdict["home"],argdict["visitor"])
                prob = HomeGuesser.getProbHome(argdict["home"],argdict["visitor"])
            prob = 1 - prob if prediction == argdict['visitor'] else prob
            self.wfile.write("<p>The predicted winner, using %s, with a confidence of %.2f%% is:</p><h3><b> %s </b></h3>" % (Or.model,prob*100,prediction,))
                
    else:
        self.wfile.write("<p > Insufficient credits! </p>")


def getMoreCredits(self,user):
    UserDatabase.execute('update Users set credits = credits + 5 where user = ?', (user,))

def printLoginInterface(self, argdict, incorrect = False):
    UserDatabase.execute('update Users set loggedin=0')
    printHeader(self)
    self.wfile.write('<h3 >Login to the Oracle of Hundred Acre Wood</h3>')
    self.wfile.write('<p ><form name = "input",  method="get", action="loginCheck"></p>')
    self.wfile.write('<p > Username: <input type="text" name="user">  Password: <input type="password" name="pass"> </p>')
    self.wfile.write('<p > <input type="submit"  value="Login"></form></p>')       
    self.wfile.write('<p > <a href="/register"> Register </a></p>')       
    if 'incorrect' in argdict:
        self.wfile.write('<p ><br>Incorrect user or pass, try again </p>')
    self.wfile.write('</body></html>')


def printRegisterInterface(self, argdict, incorrect = False):
    UserDatabase.execute('update Users set loggedin=0')
    printHeader(self)
    self.wfile.write('<form name = "input",  method="get", action="doRegister">')
    self.wfile.write('<h3>Register to use the Oracle of Hunred Acre Wood</h3>')
    self.wfile.write('<p>Username: <input type="text" name="user"> Password: <input type="password" name="pass"></p>')
    self.wfile.write('<p><input type="submit"  value="Register"></form> </p>')       
    self.wfile.write('<p><a href="/loginpage"> Login  </a></p>')       
    if 'incorrect' in argdict:
        self.wfile.write('<p><br>User already exists, try again</p>')
    self.wfile.write('</body></html>')

def printDoRegister(self,argdict):
    users = list(UserDatabase.execute('select id from Users where user= ?',(argdict['user'],)))
    if len(users) > 0:
        printRedirect(self,"/register?incorrect=1")
    else:
        s = sha256(argdict['pass']).hexdigest()
        users = list(UserDatabase.execute('select * from Users'))
        UserDatabase.execute('INSERT INTO Users (user,pass) values (?,?)', (argdict['user'],s,))
        UserDatabase.commit()
        UserDatabase.execute('update Users set loggedin=1 where user = ?', (argdict['user'],))
        printRedirect(self, user = argdict['user'])
    
def printLoginCheck(self,argdict):
    s = sha256(argdict['pass']).hexdigest()
    passw = list(UserDatabase.execute('select pass from Users where user= ?',(argdict['user'],)))
    if len(passw) > 0 and (passw[0][0] == s):
        UserDatabase.execute('update Users set loggedin=1 where user = ?', (argdict['user'],))
        printRedirect(self, user = argdict['user'])
    else:
        printRedirect(self,"/loginpage?incorrect=1")


def getCookies(self):
    cookie = self.headers.get('Cookie')
    cookie = cookie.split('; ')
    return dict(zip(map(lambda x: x.split('=')[0],cookie),map(lambda x: x.split('=')[1],cookie)))

def getUser(self):
    cookies = getCookies(self)
    user = cookies['user'] if 'user' in cookies else None
    return user
     

def printRedirect(self, redirectTo = '/spadispilin', user=None):
    printHeader(self,user)
    self.wfile.write('<html>')
    self.wfile.write('<meta http-equiv="refresh" content="0;url=%s">' % (redirectTo))       
    self.wfile.write('</html>')

def refreshUsers(self):
    tableExists = lambda tableName,database: False if len(list(database.execute("select name from sqlite_master where type='table' and name = '%s'" % tableName))) < 1 else True #Checks whether the table exists.
    if tableExists('Users',UserDatabase):
        UserDatabase.execute('Drop table Users')
    UserDatabase.execute("CREATE TABLE Users (id INTEGER PRIMARY KEY AUTOINCREMENT , user varchar(255), pass varchar(255),loggedin boolean default false, credits int default 10)")

if __name__ == '__main__':
    # Point your browser to http://localhost:8080/
    parser = OptionParser()
    parser.add_option("-f",action="store_true",dest="fast", default = False)
    (options,args) = parser.parse_args()
    PORT_NAME = 'localhost'
    PORT_NUMBER = 8080
    user = ""
    UserDatabase = sql.connect('OracleUsers.db',detect_types=sql.PARSE_DECLTYPES)
    logging.basicConfig(filename='oracleserver.log',level=logging.DEBUG)
    tableExists = lambda tableName,database: False if len(list(database.execute("select name from sqlite_master where type='table' and name = '%s'" % tableName))) < 1 else True #Checks whether the table exists.
    if not tableExists('Users',UserDatabase):
        UserDatabase.execute("CREATE TABLE Users (id INTEGER PRIMARY KEY AUTOINCREMENT , user varchar(255), pass varchar(255),loggedin boolean default false, credits int default 10)")
    
    print "Starting Oracle and Fetching Schedule..."
    Or=Oracle()
    HomeGuesser = Oracle()

    print "Starting Oracle and Fetching Schedule... Done"
    HomeGuesser.switchModel("always_home")
    if not options.fast:
        Or.switchModel('randomForest', randomForestEstimators = 100, numberOfLastGames = 3)
    print "Training model..."
    Or.train()
    print "Training model... Done"
    teamNames=list(str(name[0]) for name in list(Or.Odb.dbConn.execute("select distinct realname from teamNames")))
    class myHandler(BaseHTTPRequestHandler):
    #This class handles incoming requests from the browser 
        def do_GET(self):
        # Handler for the GET requests
            logging.debug("<request>: %s" %(self.path))
            if self.path is "/":
                self.path = "loginpage"

            argdict = argumentsToDict(self.path)

            if 'register' in self.path:
                printRegisterInterface(self,argdict)
                return
            
            if 'logout' in self.path:
                printRedirect(self,"/")
                return
                
            if 'doRegister' in self.path:
                printDoRegister(self,argdict)
                return
                
            if 'loginpage' in self.path:
                printLoginInterface(self,argdict)
                return

            if 'loginCheck' in self.path:
                printLoginCheck(self,argdict)
                return

            if 'dropUsers' in self.path:
                user = getUser(self)
                if user and list(UserDatabase.execute('select loggedin from Users where user = ?', (user,)))[0][0] == 1:
                    refreshUsers(self)
                    printRedirect(self,"/")
                else:
                    printRedirect(self,"/")
                return
            
            if 'schedule' in self.path:
                user = getUser(self)
                if user and list(UserDatabase.execute('select loggedin from Users where user = ?', (user,)))[0][0] == 1:
                    printSchedule(self,user)
                else:
                    printRedirect(self,"/")
                return

            if 'settings' in self.path:
                user = getUser(self)
                if user and list(UserDatabase.execute('select loggedin from Users where user = ?', (user,)))[0][0] == 1:
                    printSettings(self,user)
                else:
                    printRedirect(self,"/")

                return

            if 'setSettings' in self.path:
                user = getUser(self)
                if user:
                    setSettings(self,argdict)
                    printRedirect(self,"/spadispilin",user=user)
                else:
                    printRedirect(self,"/")

            if 'home' and 'visitor' and 'spadispilin' in self.path:
                user = getUser(self)
                if user and list(UserDatabase.execute('select loggedin from Users where user = ?', (user,)))[0][0] == 1:
                    decreaseCredits(self,argdict,user)
                else:
                    printRedirect(self,"/")

            if 'spadispilin' in self.path:
                user = getUser(self)
                if user and list(UserDatabase.execute('select loggedin from Users where user = ?', (user,)))[0][0] == 1:
                    if 'morecredits' in self.path:
                        getMoreCredits(self,user)
                    printPredictInterface(self,argdict,user)
                else:
                    printRedirect(self,"/")
           
            if 'home' and 'visitor' and 'spadispilin' in self.path:
                user = getUser(self)
                if user and list(UserDatabase.execute('select loggedin from Users where user = ?', (user,)))[0][0] == 1:
                    printPrediction(self,argdict, user)
                else:
                    printRedirect(self,"/")
            
            if 'spadispilin' in self.path:
                printEnd(self)

                    
    try:
        # Create a web server and define the handler to manage incoming requests
        server = HTTPServer((PORT_NAME, PORT_NUMBER), myHandler)
        print "Starting server..."
        logging.debug('Started httpserver on port %s ' % (PORT_NUMBER))
        print "Starting server... Done"
        print "Server running on %s" % (PORT_NUMBER)
        # Wait forever for incoming http requests
        server.serve_forever()
    except KeyboardInterrupt:
        UserDatabase.execute('update Users set loggedin=0')
        UserDatabase.commit()
        server.socket.close()

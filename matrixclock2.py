#!/usr/bin/python

import time, datetime, serial, os, sys
import sqlite3
import json
from datetime import date, datetime
from collections import deque

d = deque(['1234567890123456','|--------------|'])

pid = os.getpid()

with open('/home/pi/.matrixclock.pid','w') as p:
    p.write(str(pid))

ser = serial.Serial('/dev/ttyACM0', 19200, timeout=1)

today  = date.today()

def getwug():
    # get conditions last reported (cron job updates this) and return formatted list
    while True:

        try:
            data_file = open('/home/pi/x10/wug.txt')
            data = json.load(data_file)
            data_file.close()
            break

        except ValueError:
            pass

        time.sleep(2)

    return data

def formatwug():

    data = getwug()
    returnlist = []

    if len(data["alerts"])>0:
        alertslist = []
        for alert in data["alerts"]:
            if "TOR" in alert["type"]:
                returnlist.append('TORNADO WARNING')
                alertslist.append('RED')
            elif "WRN" in alert["type"]:
                returnlist.append('*TSTORM WARNING*')
                alertslist.append('RED')
            elif "TOW" in alert["type"]:
                returnlist.append('*TORNADO WATCH*')
                alertslist.append('YELLOW')
            elif "SEW" in alert["type"]:
                returnlist.append('*TSTORM WATCH*')
                alertslist.append('YELLOW')
        if 'RED' in alertslist:
            matrixwritecommand([0xd0,255,0,0])
        elif 'YELLOW' in alertslist:
            matrixwritecommand([0xd0,255,128,0])
    else:
        matrixwritecommand([0xd0,255,255,255])

    returnlist.append(' ' + str(data["current_observation"]["temp_f"]) + 'F  (' + str(data["current_observation"]["feelslike_f"]) + 'F)')

    returnlist.append(data["current_observation"]["weather"])

    returnlist.append(' hi/lo   ' +  data["forecast"]["simpleforecast"]["forecastday"][0]["high"]["fahrenheit"] +'/' + data["forecast"]["simpleforecast"]["forecastday"][0]["low"]["fahrenheit"] + 'F')

    returnlist.append(' tmrw    ' +  data["forecast"]["simpleforecast"]["forecastday"][1]["high"]["fahrenheit"] +'/' + data["forecast"]["simpleforecast"]["forecastday"][1]["low"]["fahrenheit"] + 'F')

    with open('/home/pi/x10/current.txt','w') as f:
    	f.write(data["current_observation"]["weather"])

    # data["current_observation"]["temp_f"]
    # data["current_observation"]["feelslike_f"]
    # data["current_observation"]["weather"] = for printing desc
    # data["current_observation"]["icon"] - for determining lights
    # data["alerts"][#]["type"] = TOR/TOW/WRN/SEW
    # data["forecast"]["simpleforecast"]["forecastday"][0]["high"]["fahrenheit"] (today = 0, tomorrow = 1)
    # data["forecast"]["simpleforecast"]["forecastday"][0]["low"]["fahrenheit"]
    # matrixwritecommand([0xd0,255,255,0]) - yellow
    # matrixwritecommand([0xd0,255,0,0]) - red

    return returnlist

def getsundata(currdate):
    # retrieve sun data from database - only needs to happen once a day
    # should also be called on startup of script

    db = sqlite3.connect('/home/pi/database.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    with db:
        c = db.cursor()
        c.execute('select sunup,sunup3,sunup6,sunset,sunset3,sunset6 from suntimes where date = ?',(currdate,))
        sundata = c.fetchone()
    return sundata

def formatsundata(sundata,now):
    # format the sunrise/set data and return list
    if sundata[0].date <> now.date():
        sundata = getsundata(now.date())

    returnlist = []

    returnlist.append(str(sundata[0].hour) + ":%(mup)02d <---> " %{"mup":sundata[0].minute} + str(sundata[3].hour) + ":%(mdn)02d" %{"mdn":sundata[3].minute})

    if now < sundata[0]: # before sunup
        totsec = (sundata[0] - now).seconds
        hourstosunup = totsec / 3600
        minstosunup = totsec % 3600 / 60
        secstosunup = totsec % 3600 % 60
        timetosunup = "%(h)01d" %{"h":hourstosunup} + ":%(m)02d" %{"m":minstosunup} + ":%(s)02d" %{"s":secstosunup}
        returnlist.append("sunup in " + timetosunup)
    elif now < sundata[3]: # before sunset
        totsec = (sundata[3] - now).seconds
        hourstosundn = totsec / 3600
        minstosundn = totsec % 3600 / 60
        secstosundn = totsec % 3600 % 60
        timetosundn = "%(h)01d" %{"h":hourstosundn} + ":%(m)02d" %{"m":minstosundn} + ":%(s)02d" %{"s":secstosundn}
        returnlist.append("sundn in " + timetosundn)

    return returnlist

def x10control():
    pass
    #print data["current_observation"]["observation_time"]

def matrixwritecommand(commandlist):
    commandlist.insert(0, 0xFE)
    for i in range(0, len(commandlist)):
         ser.write(chr(commandlist[i]))

def buildlist(d):
    # put together the list of strings that the loop loops through
    d.append("      " + str(now.hour) + ":%(m)02d" %{"m":now.minute})
    d.extend(formatwug())
    d.extend(formatsundata(sundata,datetime.today()))

sundata = getsundata(today)
data = getwug()

#clear
matrixwritecommand([0x58])
# turn on display
matrixwritecommand([0x42, 0])
# setup contrast, brightness, color
matrixwritecommand([0x91,220]) # contrast 220 seems best
time.sleep(0.1)
matrixwritecommand([0x99,128]) #brightness 256 is full
time.sleep(0.1)
matrixwritecommand([0x4b])
time.sleep(0.1)
matrixwritecommand([0x54])
time.sleep(0.1)
matrixwritecommand([0xd0,255,255,255]) #color RGB
#go home
matrixwritecommand([0x48])

# Continually update the time on a 4 char, 7-segment display
while(True):
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    #second = now.second
    x10control()

    if len(d) <= 1:
        buildlist(d)

    lineone = d.popleft()
    linetwo = d[0]

    #print lineone
    #clear
    matrixwritecommand([0x58])
    #go home
    matrixwritecommand([0x48])
    ser.write(lineone)
    # move to line 2
    matrixwritecommand([0x47, 1, 2])
    ser.write(linetwo)
    # Wait five seconds
    time.sleep(5)

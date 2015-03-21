#!/usr/bin/python

import time, datetime, serial, os, sys


pid = os.getpid()
with open('/home/pi/.matrixclock.pid','w') as p:
    p.write(str(pid))


ser = serial.Serial('/dev/ttyACM0', 19200, timeout=1)


def matrixwritecommand(commandlist):
    commandlist.insert(0, 0xFE)
    for i in range(0, len(commandlist)):
         ser.write(chr(commandlist[i]))

def getweather(dtnow=datetime.datetime.now()):
    # get conditions last reported (cron job updates this)
    returnlist = []
    with open('/home/pi/x10/current.txt') as f:
        for line in f:
            if 'Temperature:' in line:
                sa = line.split()
                returnlist.append("Out Temp = " + sa[1] + sa[2])
            elif 'Windchill:' in line:
                sb = line.split()
                returnlist.append("Windchill = " + sb[1] + sb[2])

    with open('/home/pi/x10/suninfo.txt') as s:
        for line in s:
            if 'Sun rises' in line:
                sc = line.split()
                sunrisestr = sc[2]
                sunsetstr = sc[5]
                break

    sunrisetime = dtnow.replace(hour=int(sunrisestr[:2]), minute=int(sunrisestr[2:]))
    sunsettime = dtnow.replace(hour=int(sunsetstr[:2]), minute=int(sunsetstr[2:]))
    if dtnow < sunrisetime:
        returnlist.append("Sunrise @ " + str(sunrisetime.hour) + ":" + sunrisestr[2:])
    elif dtnow < sunsettime:
        returnlist.append("Sunset @ " + str(int(sunsettime.hour)%12) + ":" + sunsetstr[2:])

    return returnlist

#clear
matrixwritecommand([0x58])
# turn on display
matrixwritecommand([0x42, 0])
# setup contrast, brightness, color
matrixwritecommand([0x91,220])
time.sleep(0.1)
matrixwritecommand([0x99,128])
time.sleep(0.1)
matrixwritecommand([0x4b])
time.sleep(0.1)
matrixwritecommand([0x54])
time.sleep(0.1)
matrixwritecommand([0xd0,255,255,255])
#go home
matrixwritecommand([0x48])


weatherlist = getweather()
currentweatheritem = 0

# Continually update the time on a 4 char, 7-segment display
while(True):
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second

    # try to update weather a few times (cron updates at 10 past)
    if (minute == (11 or 41)) and (second == (15 or 46)):
        weatherlist = getweather(now)

    # get dimmer at night, brighter during day
    #if hour > 22:
    #    ledbp.setBrightness(2)
    #elif hour > 21:
    #    ledbp.setBrightness(8)
    #elif hour > 7:
    #    ledbp.setBrightness(16)
    #else:
    #    ledbp.setBrightness(2)

    # set left top dot to indicate pm and undo 24-hr time
    # colon is 2 and dot is 4
    if hour > 12:
        hour = hour - 12

    #every 10 sec, show some weather
    if not second % 10:
        # determine how big weatherlist is and iterate through them
        if currentweatheritem < len(weatherlist):
            #put cursor on line 2
            matrixwritecommand([0x47, 1, 2])
            ser.write(weatherlist[currentweatheritem] + chr(0x0d))
            currentweatheritem += 1
        else:
            #print 'exceeded top, reset to 0.  item contains:',weatherlist[0]
            matrixwritecommand([0x47, 1, 2])
            ser.write(weatherlist[0]+chr(0x0d))
            currentweatheritem = 1

    # Set hours
    strhours = str(hour)

    # Set minutes
    strmins = str(int(minute / 10)) +  str(minute % 10)

    #blink colon every sec
    if (second % 2):
        colon = ":"
    else:
        colon = " "

    #go home
    matrixwritecommand([0x48])
    ser.write("      " + strhours + colon + strmins + chr(0x0d))

    # Wait one second
    time.sleep(1)

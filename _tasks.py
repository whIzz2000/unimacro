__version__ = "$Rev: 535 $ on $Date: 2014-01-27 13:37:09 +0100 (ma, 27 jan 2014) $ by $Author: quintijn $"
# This file is part of a SourceForge project called "unimacro" see
# http://unimacro.SourceForge.net and http://qh.antenna.nl/unimacro
# (c) copyright 2003 see http://qh.antenna.nl/unimacro/aboutunimacro.html
#    or the file COPYRIGHT.txt in the natlink\natlink directory 
#
#  _tasks.py
#
#
# written by Quintijn Hoogenboom (QH softwaretraining & advies),
# july 2006
#
#

#
"""Do task switching (taskbar), switch to icons in the system tray,

And switch to Windows inside an application.

(Previous some of these commands were in grammar _general)

Move tasks to other display other to a corner of the current monitor

"""
#
#

import natlink, nsformat #

import time, os, os.path, win32gui, monitorfunctions, sys

natut = __import__('natlinkutils')
natqh = __import__('natlinkutilsqh')
natbj = __import__('natlinkutilsbj')
from actions import doAction as action
from actions import doKeystroke as keystroke
from actions import setPosition
from actions import getPosition
import actions
import win32con, win32api
language = natqh.getLanguage()        
ICAlphabet = natbj.getICAlphabet(language=language)

# center mouse after taskswitch (not good with XP and choice boxes in taskbar)

ancestor=natbj.DocstringGrammar
class ThisGrammar(ancestor):
    iniIgnoreGrammarLists = ['iconcount', 'taskcount',
                             #'switchapp', 'degrees', 'pixelcount',
                             'switchapp',
                             #'sizecount','percentcount', 'directionplus', 'direction',
                             'directionplus', 'direction',
                             'namedtask']
    language = natqh.getLanguage()        
    name = "tasks"
    # task commands in docstring form in the rule functions below
    gramSpec = ["""

# here are the older commands:
# icon (system tray) commands:
<iconswitch> exported = (icon) ({iconcount}|(<direction> [{iconcount}])) [{iconaction}];
<thisicon> exported = (icon) {iconaction};
<direction> = {direction};

# miscelaneous:
<fileswitch> exported  = ("switch file to") {switchapp};
    """]
    
    # include only if searchinothertask is True (via .ini file) (enable search commands = T)
    searchRule = "<searchinothertask> exported = search ({taskcount}|{application}) | <before> search ({taskcount}|{application});"

    def __init__(self):
        """start the inifile and add to grammar if needed the searchRule
        """
        self.startInifile()
        #print 'enableSearchCommands: %s'% self.enableSearchCommands
        if self.enableSearchCommands:
            self.gramSpec.append(self.searchRule)
        ancestor.__init__(self)                


    def initialize(self):
        self.load(self.gramSpec)
        self.switchOnOrOff() # initialises lists from inifile, and switches on
                         # if all goes well (and variable onOrOff == 1)
        self.taskCounts = range(1, self.maxTaskNumber+1)
        # call for extra spoken form with difficult numbers
        # needs self.stripSpokenForm in gotResults... function!!!
        #self.addSpokenFormNumbers(self.taskCounts)
        self.iconCounts = range(1, self.maxIconNumber+1)  # int or str both work
        self.setNumbersList('taskcount', self.taskCounts)
        self.setNumbersList('iconcount', self.iconCounts)
        self.setList('switchapp', self.switchApps)
        self.emptyList('namedtask')  # to be filled with task name command
        #for moving the window:schakel in taken
        #self.pixelCounts = range(1, 21) + range(20, 201, 10)
        #self.setNumbersList('pixelcount', self.pixelCounts)
        #self.degreeCounts = range(0, 361,10)
        #self.setNumbersList('degrees', self.degreeCounts)
        #self.sizeCounts = range(1,21)
        #self.setNumbersList('sizecount', self.sizeCounts)
        #self.percentCounts = range(10,101,10)
        #self.setNumbersList('percentcount', self.percentCounts)
        self.namedtaskDict = {} # name -> hndle dict
        # the spoken forms are the values of the inifile
        # the keys of the inifile (fixed) are the resulting directions to be
        # worked with
        # for the task position etc commands:
        self.directionsplus = self.iniGetInvertedDict('directionplusreverse')
        self.setList('directionplus', self.directionsplus.keys())
        # for the icon direction commands:
        self.directions = self.iniGetInvertedDict('directionreverse')
        self.setList('direction', self.directions.keys())
        self.activateAll()
        self.winkeyDown = 0  # for keeping down in stacked taskbar itemsals je zo graag
#left|up|right|down|lefttop|righttop|rightbottom|leftbottom;

    def iniGetInvertedDict(self, section):
        """get all the values as keys, and the keys as values
            values are separated by ; to are read in as a list
        """
        D = {}
        keys = self.ini.get(section)
        if not keys:
            raise ValueError('Grammar %s: no keys in inifile section [%s] (inifile: %s)'%
                             (self.name, section, self.ini._name))
        for k in keys:
            values = self.ini.getList(section, k)
            if values:
                for v in values:
                    if v:
                        D[v] = k
            else:
                D[k] = k
        return D

    def gotBegin(self,moduleInfo):
        if self.checkForChanges:
            self.checkInifile() # refills grammar lists and instance variables
        if self.winkeyDown:
            className = natqh.getClassName()
            if className != 'TaskListThumbnailWnd':
                print 'tasks, call cancelmode from gotBegin'
                self.cancelMode()


    def gotResultsInit(self, words, fullResults):
        self.fullResults = fullResults 
        # for the move commands:
        self.directionicon = None
        self.directionplus = None # for position, stretch, shrink
        self.units = None
        self.amount = None
        self.taskmoveresize = None  # also "position" (see gotResults)
        self.hadStartMenu = 0
        self.letters = None
        self.app = None
        self.namedictated = ""  # for naming a window
        self.giveName = None # for the hndle when naming a window
    ### here come the docstring like rules:
    ###

    def rule_startmenu(self, words):
        """start menu [{startmenucommands}]
        """
        print 'got start menu'
        if self.hasCommon(words[0], 'start'):
            self.hadStartMenu = 1
        Act = self.getFromInifile(words[-1], 'startmenucommands')
        if Act:
            self.hadStartMenu = 0 # no action in gotResults, doing it here
            self.doStartMenu()
            action(Act)
    
    def doStartMenu(self):
        """give the start menu
        """
        action("SSK {ctrl+esc}")
        
    def rule_taskswitch(self, words):
        """#commands for switching tasks:    
        task ({taskcount}|{taskcount}<subtask>|{application}|{application}<subtask>|back|{namedtask})
        """
        #print 'got taskswitch: %s'% words
        #switch to a task by number, application or Back
        #leave the mouse at 0.3 0.3 relative to the top
        countOrApp = words[1]
        #print 'goto task, countOrApp: %s'% countOrApp
        result = self.gotoTask(countOrApp)
        
        if result:
            prog, title, topchild, windowHandle = natqh.getProgInfo()
            if prog == 'explorer' and not title:
                return # no centermouse!
            if self.centerMouse and not self.nextRule:
                natqh.Wait()
                natqh.doMouse(1, 5, 0.3, 0.3, 0, 0)  # relative in client area, no clicking           
        else:
            print '_tasks, could not switch to task: %s'% countOrApp


    def rule_subtask(self, words):
        """# commands for going to a subtask in a stacked taskbar
        window {n1-10} | {firstlast} window
        """
        className = natqh.getClassName()
        wNumList = self.getNumbersFromSpoken(words) # returns a string or None
        if wNumList:
            wNum = wNumList[0]
        else:
            wNum = self.getFromInifile(words, 'firstlast')
        if not wNum:
            print 'tasks, rule subtaks, no window number found'
            return
        
        #print 'tasks, subtask: %s'% wNum
        if className == "TaskListThumbnailWnd":
            #print 'got subtask, alternative window: %s'% wNum
            self.doAlternativeClick(className, wNum)

        if self.centerMouse and not self.nextRule:  # so last rule of the recognition
            natqh.doMouse(1, 5, 0.3, 0.3, 0, 0)



    def gotResults_searchinothertask(self, words, fullResults):
        ## rule for searching in another task, activated only if ...
        
        t = time.time()
        searchWord = self.getSelectedText()
        print 'searchWord from getSelectedText: %s'% searchWord
        if not searchWord:
            searchWord = action("SELECTWORD")
            if not searchWord:
                print '_tasks, searchinothertask: could not select text'
                return
        t1 = time.time() 
        print 'searchword: %s (%.2f)'% (searchWord, t1-t)
        countOrApp = words[1]
        #print 'switch to task: %s'% countOrApp
        result = self.gotoTask(countOrApp)
        if result is None:
            print '_tasks, could not switch to task: %s'% countOrApp
            return
        print 'result after taskswitch: %s'% repr(result)
        t2 = time.time() 

        prog, title, topchild, windowHandle = progInfo = result
        #print 'switched to "%s" (%.2f)'%  (prog, t2-t1)


        if prog == 'explorer' and not title:
            return # no centermouse!
        if self.centerMouse:
            natqh.Wait()
            natqh.doMouse(1, 5, 0.3, 0.3, 0, 0)  # relative in client area, no clicking           

        natqh.Wait()
        # now do the postprocessing
        print 'postprocessing for search: %s in app: %s'% (searchWord, prog)
        if prog in ['chrome', 'firefox','iexplore']:
            phrase = '"%s" site:nl'% searchWord
            keystroke("{ctrl+k}")
            keystroke(phrase + "{enter}")
        elif prog == 'dictionaryworkbench':
            # hardcoded for Arnoud
            keystroke('{ctrl+f}')
            action("SCLIP %s"% searchWord)
            keystroke('{enter}')
        else:
            #t3 = time.time()
            action("<<startsearch>>", progInfo=progInfo)
            #t4 = time.time()
            keystroke(searchWord, progInfo=progInfo)
            #t5 = time.time()
            action("<<searchgo>>", progInfo=progInfo)
            #t6 = time.time()
            #print 'after searchaction: %s (%.2f, %.2f, %.2f, %.2f)'% (searchWord, t3-t2,
            #                                                    t4-t3, t5-t4, t6-t5)
            

    def subrule_before(self, words):
        """#optional word here in front of command:
        Here
        """
        action("CLICK")
        natqh.visibleWait()
        #action("CLICKIFSTEADY")

    def importedrule_dgndictation(self, words):
        # for giving a window a name
        self.namedictated = nsformat.formatWords(words, state=-1)[0]
        

    def rule_taskaction(self, words):
        '(<taskswitch> | <subtask> | task)({taskaction}| "give name" <dgndictation>|<closemultiple>)'
        
        # do a taskaction to the current task, or one of the
        # numbered/named tasks or task back
        #print 'got taskaction: %s'% words
        actions = self.ini.get('taskaction')
        act = self.hasCommon(words, actions)
        giveName = self.hasCommon(words, "give name")
        #if self.app == "messages":
        #    print 'action for messages: %s'% act
        #    if act == 'refresh':
        #        self.doTaskAction('close')
        #        print 'new messages window'
        #        return
        if giveName:
            hndle = natlink.getCurrentModule()[2]
            self.giveName = hndle
        elif act:
            self.doTaskAction(act)
        else:
            print 'thistask in _general, no valid action', words

        prog, title, topchild, windowHandle = natqh.getProgInfo()
        if prog == 'explorer' and not title:
            return # no centermouse!
        
        if self.centerMouse:
            natqh.doMouse(1, 5, 0.3, 0.3, 0, 0)
        
    def subrule_closemultiple(self, words):
        """close (all|other) | (all|other) close
        """
        # note the grammar alternatives, eg in Dutch the translation of
        # all close (alles sluiten) is more convenient.
        if not self.lastTaskCount:
            print '_tasks, close all | close multiple only works with a numbered task'
            return
        all = self.hasCommon(words, "all")
        multiple = self.hasCommon(words, "multiple")
        if all:
            action("MP 2, 0, 0, right; VW; {up}{enter}; VW")
            self.gotoTask("back")
            
        elif multiple:
            # close as long as special stacked window is found
            mousePos = natqh.getMousePosition()
            if mousePos is None:
                raise ValueError("could not get mouse position")
            x, y = mousePos
            className = natqh.getClassName()
            wNum = -1 # last window of stacked windows...
            #print 'tasks, subtask: %s'% wNum
            while className == "TaskListThumbnailWnd":
                #print 'got subtask, alternative window: %s'% words
                self.doAlternativeClick(className, wNum)
                action("<<windowclose>>")
                action("VW; MP 0, %s, %s"% mousePos)
                className = natqh.getClassName()
            self.gotoTask(self.lastTaskCount)
        if self.centerMouse:
            natqh.doMouse(1, 5, 0.3, 0.3, 0, 0)
            
        
    def gotoTask(self, countOrApp):
        """go to the specified task, by number or application name, return proginfo, or None if task was not found
        
        """
        self.lastTaskCount = None
        if isinstance(countOrApp, basestring):
            countBack = self.getNumberFromSpoken(countOrApp, self.taskCounts) # returns a string or None
        elif isinstance(countOrApp, int):
            countBack = countOrApp
        hasMousePos = 0
        appList = self.ini.get('application')
##        print 'appList: %s'% appList
        if isinstance(countOrApp, basestring) and self.hasCommon(countOrApp, 'back'):
            action('SSK {Alt+Tab}')
            return 1
        elif countOrApp in self.namedtaskDict:
            hndle = self.namedtaskDict[countOrApp]
            result = natqh.SetForegroundWindow(hndle)
            if not result:
                print 'switch to %s failed, delete name: %s'% (hndle, countOrApp)
                del self.namedtaskDict[countOrApp]
                self.setList('namedtask', self.namedtaskDict.keys())
                return
        elif countBack:
            t = time.time()
            self.lastTaskCount = countBack
            if self.doTasksWithWindowsKey:
                self.goto_task_winkey(countBack)
            else:
                action('TASK %s'% countBack)
            result = natqh.getProgInfo()
            #print 'after action task %s, time: %.2f'% (countBack, (time.time()-t))
            return result
        elif countOrApp in appList:
            value = self.ini.getList('application', countOrApp)
            if len(value) == 1:
                app = value[0]
                self.app = app
                result = action("BRINGUP %s"% app)
                return result
##            print 'after bringup: %s'% app
            elif len(value) == 2:
                #application is known, but click by number!!
                appName = value[0]
                countBack = value[1]
                self.lastTaskCount = countBack
                if self.doTasksWithWindowsKey:
                    self.goto_task_winkey(countBack)
                else:
                    action('TASK %s'% countBack)
                for i in range(30):
                    # 40 x 0.1: 4 seconds...
                    prog, title, topchild, windowHandle = natqh.getProgInfo()
                    if prog == appName: break
                    className = natqh.getClassName()
                    if className == "TaskListThumbnailWnd": return 1  # more items already available
                    natqh.Wait()
                else:
                    print 'application not detected in foreground: %s'% appName
                    return
        else:
            print '_tasks, no valid entry for gotoTask: %s'% countOrApp
            return
        result = natqh.getProgInfo()
   

    def goto_task_winkey(self, number):
        """switch to task with number, via the windows key"""
    ##    print 'action: goto task: %s'% number
        prog, title, topchild, windowHandle = natqh.getProgInfo()
        if prog == 'explorer' and not title:
            keystroke('{esc}')
            natqh.shortWait()
        try:
            count = int(number)
        except ValueError:
            print 'goto_task_winkey, invalid number: %s'% number
            return
        if not count:
            print 'goto_task_winkey, invalid number: %s'% number
            return
        elif count == 10:
            count=0
        elif count > 10:
            print 'goto_task_winkey, pass on to "TASK %s", number > 9'% count
            return action('TASK %s'% count)
        
        self.doWinKey('b')
        actions.do_VW()
        self.doWinKey(str(number))
        print 'self.winkeyDown: %s'% self.winkeyDown
   
        
    def rule_taskposition(self, words):
        """
        #commands for positioning (moving) and resizing tasks: 
        (<taskswitch>|task) position <directionplus> 
        """
        # position task in one of the directions, width/height
        # did also optional percent with <directionplus> <percent> switched off for the moment
        # optional percentage of work area
        self.taskmoveresize = 'position'
        print '----task position'
        
    def rule_taskmove(self, words):
        """(<taskswitch> | task) move <directionplus>;
        """
        
        # removed all the angle, pixels, centimeters, inches, percent out, too complicated for daily use I think...
        # optional a specification
        self.taskmoveresize = 'move'
        print '----task move'
    
    #def rule_taskresize(self, words):
    #    """(<taskswitch> | (task)) (stretch|shrink)
    #            (<directionplus>|<angle>)
    #               [<pixels>|<centimeters>|<millimeters>|<inches>|<percent>]
    #    """
    #    # resize a task in direction or angle
    #    # with optional specification
    #    if self.hasCommon(words, 'stretch'):
    #        self.taskmoveresize = 'stretch'
    #    if self.hasCommon(words, 'shrink'):
    #        self.taskmoveresize = 'shrink'
    #    print '----task resize: %s'% self.taskmoveresize
    #    # action in gotResult
        
    def rule_taskresizeinfo(self, words):
        """give resize info
        """
        winHndle = win32gui.GetForegroundWindow()
        canBeResized = monitorfunctions.window_can_be_resized(winHndle)
        print 'resize info %s'% canBeResized
            
    
    # rules inside position, move, stretch, shrink:
    # too precise, can be switched on again later...
    #def subrule_angle(self, words):
    #    """ 
    #    #directional specifications:
    #    {degrees} degrees
    #    """
    #    #get the move or resize angle
    #    deg = self.getNumberFromSpoken(words[0])
    #    self.directionplus = deg%360
    #    print 'angle/direction: %s'% self.directionplus
        
    def subrule_directionplus(self, words):
        '{directionplus}'
        #get the direction
        direction = words[0]
        if direction in self.directionsplus:
            self.directionplus = self.directionsplus[direction]
        else:
            self.directionplus = direction
        print 'direction: (plus) %s'% self.directionplus


    #def subrule_pixels(self, words):
    #    """
    #    # size specifications:
    #    {pixelcount} | {pixelcount} pixels
    #    """
    #    #get the amount in pixels (optional word)
    #    amountList = self.getNumberFromSpoken(words)
    #    if len(amountList) == 1:
    #        self.amount = amountList[0]
    #    else:
    #        raise ValueError("task grammar, rule pixels, more amounts found: %s"% amountList)
    #    self.units = 'pixels'
    #    print 'pixels: %s'% self.amount
    #
    #def subrule_centimeters(self, words):
    #    '{sizecount} centimeters'
    #    """get the amount in centimeters"""
    #    nCm = self.getNumberFromSpoken(words[0])
    #    self.units = 'pixels'
    #    self.amount = nCm * self.dotsperinch * 1.0 / 2.54 + 0.5
    #    print 'pixels(%s cm): %s'% (nCm, self.amount)
    #
    #def subrule_millimeters(self, words):
    #    '{sizecount} millimeters'
    #    #get the amount in millimeters
    #    nMm = self.getNumberFromSpoken(words[0])
    #    self.units = 'pixels'
    #    self.amount = nMm * self.dotsperinch * 1.0 / 25.4 + 0.5
    #    print 'pixels(%s mm): %s'% (nMm, self.amount)
    #    
    #def subrule_inches(self, words):
    #    '{sizecount} inches'
    #    #get the amount in inches
    #    nInches = self.getNumberFromSpoken(words[0])
    #    self.units = 'pixels'
    #    self.amount = nInches * self.dotsperinch
    #    print 'pixels(%s mm): %s'% (nInches, self.amount)
        
    def rule_gettaskposition(self, words):
        """
        #commands for recording taskbar and clock positions:
        'get task position' ({taskcount}|clock)
        """
        # getting the task positions (use with 1 and with another number)
        # position mouse on task number or clock and speak the command
        # first time only, or after changes of taskbar position
        count = self.getNumberFromSpoken(words[-1])
        x, y = natlink.getCursorPos()
        if count in self.taskCounts:
            print 'setting task position: ', count
        else:
            count = 0
        if count == 1:
            print 'setting mouseX1: ', x
            print 'setting mouseY1: ', y
            setPosition('mousex1', x)
            setPosition('mousey1', y)
        elif count:
            mousex1 = getPosition('mousex1')
            mousey1 = getPosition('mousey1')
            
            mouseXdiff = int((x - mousex1 )/(count-1))
            mouseYdiff = int((y - mousey1 )/(count-1))
            print 'setting mouseXdiff: ', mouseXdiff
            print 'setting mouseYdiff: ', mouseYdiff
            setPosition('mousexdiff', mouseXdiff)
            setPosition('mouseydiff', mouseYdiff)
        elif self.hasCommon(words,'clock'):
            print 'clock position:', x, y
            setPosition('clockx', x)
            setPosition('clocky', y)
        else:
            print 'invalid option in gettaskposition: %s'% words
            return
        

    # this one is for the icon direction:    
    def gotResults_direction(self, words, fullResults):
        """get the direction for an icon move"""
        direction = words[0]
        if direction in self.directions:
            self.directionicon = self.directions[direction]
        else:
            self.directionicon = direction
        print 'direction icon: %s'% self.directionicon
            
        

    def gotResults_thisicon(self, words, fullResults):
        """do actions on active icon"""
        actions = self.ini.get('iconaction')
        act = self.hasCommon(words, actions)
        if act:
            self.doIconAction(act)
        else:
            print 'thisicon in _general, no valid action', words

    def gotResults_iconswitch(self, words, fullResults):
        """go to specified icon in system tray (by number, or relative number)

        followed by an iconaction, like close or shortcut menu
        """
##        print 'icon switch, words: %s'% words
        direction = self.directionicon
        character = self.hasCommon(words, ICAlphabet)
        actions = self.ini.get('iconaction')
        act = self.hasCommon(words, actions)
        counts = self.getNumbersFromSpoken(words, self.iconCounts)
        if counts:
            count = int(counts[0])
        else:
            count = 0
        hasMousePos = 0
        if direction:
            count = count or 1
            print '_general, iconswitch: relative count: %s'% count
            keystroke("{%s %s}"% (direction, count))

        else:
            if count:
                gotit = self.getIconNumber(count)
            elif character:
                print 'get icon with letter: %s'% character[0]
                gotit = self.getIconLetter(character[0])
            else:
                print '_general, iconswitch: no count or letter, should not come here'
                return
        # wait a little
        if act:
            action('W')
            self.doIconAction(act)

    #def gotResults_windowswitch(self, words, fullResults):
    #    """goto numbered window (or back) inside program"""
    #    print 'windowswitch, words: %s'% words
    #    count = words[1]
    #    if self.hasCommon(count,['back', 'previous']):
    #        action('<<windowback>>')
    #    elif self.hasCommon(count, ['next']):
    #        action('<<windownext>>')
    #    elif count in self.windowCounts:
    #        action('<<windowmenu>>')
    #        keystroke(count)
    #
    def gotResults_fileswitch(self, words, fullResults):
        """switch file to the named application

        mark cursor
        close in current app
        open in new app
        goto top
        goto cursor
        
        if filename cannot be got the process is stopped

        """
        fileName = actions.getPathOfOpenFile()
        if fileName:
            print 'fileName: %s'% fileName
        else:
            self.DisplayMessage('cannot switch, filename cannot be established')
            return
            
        while fileName.endswith("*"):
              fileName = fileName[:-1]
        actions.putCursor()
        action("<<filesave>>")
        action("W")
        print "saved, now close: %s"% fileName
        action("<<documentclose>>")
        newApp = words[-1]
        newApp = self.ini.get('application', newApp, newApp)
           
        if not action("BRINGUP %s"% newApp):
            self.DisplayMessage('cannot switch, application %s cannot be brought to front'% newApp)
            return

        # fileopen in emacs relies on maximised state of emacs, cannot be sure here:
        if newApp in ('emacs', 'voicecode'):
            action("{ctrl+x}{ctrl+f}; {shift+home}{del}")
        else:
            action("<<fileopen>>")
        action("W")
        keystroke(os.path.normpath(fileName))
        action("VW")
        keystroke("{enter}")
        action("<<topdocument>>")
        actions.findCursor()
        action("<<filesave>>")

    def gotResults_convertfile(self, words, fullResults):
        """copy file and change \n\r in \n or vice versa

        mark cursor
          cut all
          convert clipboard
        paste 
        goto home
        goto cursor

        """
        actions.putCursor()
        action("CLIPSAVE")
        action("<<selectall>><<cut>>")
        t = natlink.getClipboard()
        t = self.convertString(t, words[-1])
        natqh.setClipboard(t)
        action("<<paste>>")
        action("<<topdocument>>")
        actions.findCursor()
        action("<<filesave>>")

    def gotResults(self, words, fullResults):
        """actions for task move, resize, position done here
        
        relevant data collected in other gotResult_... functions
        
        """
        if self.giveName:
            if self.namedictated:
                self.namedtaskDict[self.namedictated] = self.giveName
                self.setList('namedtask', self.namedtaskDict.keys())
                print 'name "%s" can now be used for switching to a task'% self.namedictated
            else:
                print 'giveName, no self.namedictated given...'
                
        if self.hadStartMenu:
            self.doStartMenu()
            if self.letters:
                keystroke(self.letters)

        if self.taskmoveresize:
            print 'taskmoveresize: %s'% self.taskmoveresize
            winHndle = win32gui.GetForegroundWindow()
            #print 'amount: %s'% self.amount
            #print 'units: %s'% self.units
            if self.directionplus in self.directions:
                direction = self.directions[self.directionplus]
            else:
                direction = self.directionplus
            print 'direction spoken: %s, direction taken: %s'% (self.directionplus, direction)
            canBeResized = monitorfunctions.window_can_be_resized(winHndle)
            if self.taskmoveresize == 'position':
                self.doTaskPositionCommand(winHndle, canBeResized, direction, self.amount, self.units)
            else:
                # move, stretch or shrink:
                if self.amount:
                    amount = self.amount
                    units = self.units or 'pixels'
                elif self.taskmoveresize == 'move':
                    amount = 1
                    units = 'relative'
                elif self.taskmoveresize == 'stretch':
                    amount = 1
                    units = 'relative'
                elif self.taskmoveresize == 'shrink':
                    amount = 0.5
                    units = 'relative'
                else:
                    print '_tasks, gotResults, invalid taskmoveresize: %s'% self.taskmoveresize
                    return

                print 'amount (adjusted): %s'% amount
                print 'units: (adjusted) %s'% units
    
                try:
                    func = getattr(monitorfunctions, '%s_window'% self.taskmoveresize, None)
                    if func:
                        #print 'doing func: %s'% func
                        func(winHndle, direction=self.directionplus, amount=amount, units=units)
                    else:
                        print 'invalid value for taskmoveresize: %s (could not find function)'% self.taskmoveresize                
                except ValueError:
                    print 'error in monitorfunctions.%s_window'% self.taskmoveresize
                    print sys.exc_info()[1]
#keepinside=None, keepinsideall=1, monitor=None):

    def doWinKey(self, keys, keepdown=None):
        """do a winkey and return the window info of the resulting window
        """
        winkey = win32con.VK_LWIN         # 91
        keyup = win32con.KEYEVENTF_KEYUP  # 2
        win32api.keybd_event(winkey, 0, 0, 0)  # key down
        try:
            actions.do_SSK(keys)
            actions.do_VW()
            classInfo = natqh.getClassName()
        finally:
            if classInfo == 'TaskListThumbnailWnd':
                #print 'keep logo key down'
                self.winkeyDown = 1
            else:
                win32api.keybd_event(winkey, 0, keyup, 0)  # key up
        
        
    
    # taken from _shownumbersplus, go to a subtask in stacked taskbar
    # number from 0, (in _shownumbersplus first window is click 0)
    def doAlternativeClick(self, className, num):
        """instead of click perform another (keystrokes) action
        
        if self.doTasksWithWindowsKey, do this with repeated winkey clicks
        """
        taskNum = self.lastTaskCount
        if isinstance(num, basestring):
            num = int(num)
        if className == "TaskListThumbnailWnd":
            #print 'tasks, doAlternative click: %s'% num
            if self.doTasksWithWindowsKey:
                if not (taskNum and self.winkeyDown):
                    print 'cannot complete windows command: taskNum: %s, winkeyDown: %s'% (taskNum, self.winkeyDown)
                    self.cancelMode()
                    return
                if num > 1:
                    keystr = str(taskNum)
                    for i in range(num-1):
                        actions.do_SSK(keystr)
                elif num < 0:
                    num2 = -num
                    keystr = '{shift+%s}'% taskNum
                    for i in range(num2):
                        actions.do_SSK(keystr)
                self.cancelMode()
                return

            # mode with mouse on taskbar position:
            taskbarPosition = monitorfunctions.get_taskbar_position() # notices changes on the fly!
            # which way to scroll through a stack of taskbar buttons:
            initialKeys = dict(left='{down}', top='{right}',
                               right='{left}{down}', bottom='{right}')
            scrollKeys = dict(left='down', top='right',
                               right='down', bottom='right')
            initialKeysReverse = dict(right='{left}', bottom='{left}',
                               left='{right}', top='{left}')
            scrollKeysReverse = dict(right='up', bottom='left',
                               left='up', top='left')
            try:
                if num > 0:
                    initial = initialKeys[taskbarPosition]
                    scrollKey = scrollKeys[taskbarPosition]
                elif num < 0:
                    initial = initialKeysReverse[taskbarPosition]
                    scrollKey = scrollKeysReverse[taskbarPosition]
                    num = -num
                else:
                    raise ValueError("_tasks, doAlternativeClick, number may NOT be 0")
            except KeyError:
                print 'key not found "taskbarPosition": %s'% taskbarPosition
                return
            # go to first of popup windows (depending on taskbar location)
            #print 'taskbarPosition: %s'% taskbarPosition
            #print 'initial: %s, scroll: %s'% (initial[1:], scrollKey)
            action(initial)
            if num > 1:
                num -= 1
                action('{%s %s}'% (scrollKey, num))
            action('{enter}')
        else:
            print 'should not call doAlternativeClick for className: %s'% className


    def doTaskPositionCommand(self, winHndle, canBeResized, direction, amount, units):
        """do the task position command with enclosed parameters
        """
        if amount and units == 'percent':
            amount = amount / 100.0
        elif amount:
            print 'amount: %s'% amount
        else:
            amountx = self.splitLeftRight
            amounty = self.splitTopDown
        xwidth = ywidth = 1.0
        if canBeResized:
            print 'setting default pos to 0.0'
            xpos = ypos = 0.0
        else:
            print 'no resize, setting default pos to 0.5'
            xpos = ypos = 0.5
        if direction.find('left') >= 0:
            xpos = 'left'
            xwidth = amountx
        elif direction.find('right') >= 0:
            xpos = 'right'
            xwidth = 1.0 - amountx
        elif direction.startswith('center'):
            xpos = 'center'
            if amountx >= 0.5:
                xwidth = amountx
            else:
                xwidth = 1.0 - amountx

        if direction.find('up') >= 0:
            ypos = 'up'
            ywidth = amounty
        elif direction.find('down') >= 0:
            ypos = 'down'
            ywidth = 1.0 - amounty
        elif direction.endswith('center'):
            ypos = 'center'
            if amounty >= 0.5:
                ywidth = amounty
            else:
                ywidth = 1.0 - amounty
    
        if not canBeResized:
            xwidth = ywidth = None
        print 'restore_window:pos: %s, %s, width: %s, %s'% \
                (xpos, ypos, xwidth, ywidth)
        func = monitorfunctions.restore_window
        func(winHndle, xpos=xpos, ypos=ypos,
                xwidth=xwidth, ywidth=ywidth)
    #
    #
    #def convertString(self, t, toCode):
    #      """convert to unix style (\n) or dos/windows style \n\r sucks..."""
    #      CR = chr(10)
    #      LF = chr(13)
    #      CRLF = CR + LF
    #      CRCRLF = CR + CR + LF
    #      if toCode == 'unix':
    #          return t.replace(CRLF, LF)
    #      elif toCode in ('windows', 'dos'):
    #          t = t.replace(LF, CRLF)
    #          t = t.replace(CRCRLF, CRLF)
    #          t = t.replace(CRLF+CRLF, CRLF)
    #          return t 
        
    def gotResults_removecursor(self, words, fullResults):
        """goto marked cursor, in case is was left in file switch actions"""
        actions.findCursor()

    def getIconNumber(self, count):
        """get the icon with the specified count in focus

        """        
##        mod1 = nfile openfile openlink.getCurrentModule()
##        mod2 = mod1
##        nTry = 0
##        action('SSK {ctrl+esc}{esc}')
##        print 'mx, my:', mx, my
        action("TOCLOCK")
        action("WINKEY b")  # get focus on icon tray (Gerrit van Wijk!)
        natqh.visibleWait()
        n = count
        keystroke("{right %s}"% n)
        

    def getIconLetter(self, char):
        """get the icon with the specified count in focus

        """        
##        mod1 = natlink.getCurrentModule()
##        mod2 = mod1
##        nTry = 0
##        action('SSK {ctrl+esc}{esc}')
##        print 'mx, my:', mx, my
        action("TOCLOCK")   # get mouse there
        action("WINKEY b")  # get focus on icon tray (Gerrit van Wijk!)
        keystroke("{right}")
        keystroke(char[0])

    def doTaskAction(self, actionWord, mouseOnPosition=0):
        """do action on 

     if mouseOnPosition, instead of {alt+space} a right click is done
        """
        if actionWord:
            act = self.ini.get('taskaction', actionWord)
            if act:
                #natqh.visibleWait()
                action(act)
            else:
                print 'no action for taskaction: %s'% actionWord
        

    def doIconAction(self, actionWord, mouseOnPosition=0):
        """do action on icon

        """
        if actionWord:
            act = self.ini.get('iconaction', actionWord)
            if act:
                action(act)
            else:
                print 'no action for iconaction: %s'% actionWord
        
    def fillInstanceVariables(self):
        """fills the necessary instance variables

        positions should be in actions.ini, and can be got by the "task position" commands
        
        """
        self.maxTaskNumber = self.ini.getInt('general', 'max task number') or 20
        self.maxWindowNumber = self.ini.getInt('general', 'max window number') or 9
        self.maxIconNumber = self.ini.getInt('general', 'max icon number') or 15
        self.centerMouse = self.ini.getBool('general', 'center mouse')
        #self.dotsperinch = self.ini.getInt('general', 'screen dots per inch') or 90
        
        self.doTasksWithWindowsKey = self.ini.getBool('general', 'do taskswitch with windows key')
        if self.doTasksWithWindowsKey:
            print 'do taskswitch with windows key enabled'
        # positioning not in middle (for Arnoud):
        self.splitLeftRight = self.ini.getFloat('general', 'split left right') or 0.5
        self.splitTopDown = self.ini.getFloat('general', 'split top down') or 0.5
        
        # search commands (for Arnoud):
        self.enableSearchCommands = self.ini.getBool('general', 'enable search commands') 
        if self.enableSearchCommands:
            print '_task, enable search commands'
        
        allApps = self.ini.get('application')

        # contstruct 
        switchApps = self.ini.getList('general', 'switchapps')
        self.switchApps = []
        if switchApps:
            # construct items for switchApps list, must be either
            # the keyword or the value of one of the items of
            # allApps (the list of applications in the inifile
            
            allAppsDict = dict([(k, self.ini.get('application', k)) for k in allApps])

            for sApp in switchApps:
                if sApp in allApps:
                    self.switchApps.append(sApp)
                else:
                    foundSpoken = 0
                    for k,v in allAppsDict.items():
                        if v == sApp:
                            foundSpoken = 1
                            self.switchApps.append(k)
                    if not foundSpoken:
                        print 'application not valid for switchapps: "%s", no written or spoken form in section [applications])'% sApp

    def getSelectedText(self):
        """gets a copy of the selection, otherwise ""
        """
        natqh.saveClipboard()
        action("<<copy>>")
        natqh.Wait()
        t = natqh.getClipboard()
        natqh.restoreClipboard()
        return t.strip()

    def cancelMode(self):
        # ending exclusive mode if in it, also ending the mode it is in
        winkey = win32con.VK_LWIN         # 91
        keyup = win32con.KEYEVENTF_KEYUP  # 2
        if self.winkeyDown:
            print 'tasks, cancelMode, release WINKEY'
            win32api.keybd_event(winkey, 0, keyup, 0)  # key up
            self.winkeyDown = 0

            
# standard stuff Joel (adapted for possible empty gramSpec, QH, unimacro)
thisGrammar = ThisGrammar()
if thisGrammar.gramSpec:
    thisGrammar.initialize()
else:
    thisGrammar = None

def unload():
    global thisGrammar
    if thisGrammar: thisGrammar.unload()
    thisGrammar = None

def changeCallback(type,args):
    # not active without special version of natlinkmain:
    if ((type == 'mic') and (args=='on')):
        return   # check WAS in natlinkmain...
    if thisGrammar:
        thisGrammar.cancelMode()

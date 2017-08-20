'''
Application built from a  .kv file
==================================

This shows how to implicitly use a .kv file for your application. You
should see a full screen button labelled "Hello from test.kv".

After Kivy instantiates a subclass of App, it implicitly searches for a .kv
file. The file test.kv is selected because the name of the subclass of App is
TestApp, which implies that kivy should try to load "test.kv". That file
contains a root Widget.
'''

import kivy
kivy.require('1.0.7')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.properties import BooleanProperty
from kivy.properties import ListProperty
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window

from datetime import datetime, time, timedelta
import pigpio
import json
import io
import re
from dateutil.parser import parse as parsedate
from functools import partial
import rpi_backlight as bl


Alarms             =     []

#Set GPIO pin variables
RED_PIN         =     11
GREEN_PIN         =     17
BLUE_PIN         =     22
WHITE_PIN         =     10
GPIO_FREQ         =     100

LIGHT_SENSOR_PIN    =    19
TAP_SENSOR_PIN         =    6

#Initiate GPIO pins
pi = pigpio.pi()
pi.set_PWM_frequency(11,GPIO_FREQ)
pi.set_PWM_frequency(17,GPIO_FREQ)
pi.set_PWM_frequency(22,GPIO_FREQ)
pi.set_PWM_frequency(10,GPIO_FREQ)

pi.set_mode(LIGHT_SENSOR_PIN, pigpio.INPUT)
pi.set_mode(TAP_SENSOR_PIN, pigpio.INPUT)

pi.set_glitch_filter(LIGHT_SENSOR_PIN, 1000)

pi.set_pull_up_down(LIGHT_SENSOR_PIN, pigpio.PUD_DOWN)
pi.set_pull_up_down(TAP_SENSOR_PIN, pigpio.PUD_DOWN)

#Define alarm status
ALARM_STATUS_OFF         =    0 
ALARM_STATUS_ACTIVE        =    1
ALARM_STATUS_WAKE_UP    =    2
ALARM_STATUS_SOUNDING    =    3
ALARM_STATUS_SNOOZED    =    4
ALARM_STATUS_DISMISSED    =    5

#Define brightnesses
SCREEN_OFF = 0
SCREEN_LOW = 1
SCREEN_HIGH = 2

LOW_BRIGHTNESS = 11
HIGH_BRIGHTNESS = 50

SELECTED_COLOR = []

isoformat_regex_datetime = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{6})')
isoformat_regex_time = re.compile(r'(\d{2}):(\d{2}):(\d{2})')

    
class DateJSONEncoder(json.JSONEncoder):
    #Encode date objects to JSON
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj,Alarm):
            return obj.__dict__
        else:
            return super(DateJSONEncoder, self).default(obj)

class DateJSONDecoder(json.JSONDecoder):
    #Decode JSON date objects
    def __init__(self, **kw):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object, **kw)

    def transform_value(self, value):
        if isinstance(value, str) and isoformat_regex_datetime.match(value):
            return parsedate(value)
        elif isinstance(value, str) and isoformat_regex_time.match(value):
            return parsedate(value).time()
        return value

    def dict_to_object(self, d):
        return {
        key: self.transform_value(value)
        for (key, value) in d.items()
        }

class LEDControl():
    #Class controls the LED strip
    def __init__(self):
        self.events = []

    def set_LED(self,r,g,b,w,*args):
        print("Setting LED to:",r,g,b,w)
        pi.set_PWM_dutycycle(RED_PIN,r)
        pi.set_PWM_dutycycle(GREEN_PIN,g)
        pi.set_PWM_dutycycle(BLUE_PIN,b)
        pi.set_PWM_dutycycle(WHITE_PIN,w)
    
    def testfunction(self, a1,a2,a3,a4,*args):
        print(a1)
        print(a2)
        print(a3)
        print(a4)
        
    def set_LED_gradient(self,starttime,endtime,startcolor,endcolor):
        length = endtime-starttime
        R_start = startcolor [0]
        G_start = startcolor [1]
        B_start = startcolor [2]
        W_start = startcolor [3]
        
        dR = endcolor[0] - R_start
        dG = endcolor[1] - G_start
        dB = endcolor[2] - B_start
        dW = endcolor[3] - W_start
        
        dMax = max(dR,dG,dB,dW)
        dT = length // dMax
        print("dT:",dT)
        
        for i in range(dMax):
            eventtime = starttime + i * dT
            time_from_now = (eventtime-datetime.now())
            seconds_from_now = time_from_now.seconds + time_from_now.microseconds / 1000000
            microseconds_from_now = time_from_now.microseconds
            R = int(R_start + i * dR/dMax)
            G = int(G_start + i * dG/dMax)
            B = int(B_start + i * dB/dMax)
            W = int(W_start + i * dW/dMax)
            
            
            print("i:",i," color:",R,G,B,W)
            #print("Eventtime:", eventtime)
            #print("TimeFromNow:", time_from_now)
            #print("SecondsFromNow:", seconds_from_now)
            #print("MicroSecondsFromNow:", microseconds_from_now)
            #print("")
            
            Clock.schedule_once(partial(self.set_LED, R,G,B,W), seconds_from_now)
    
class SoundPlayer():
    #Controls the sound
    def __init__(self):
        self.soundfile = 'sound/soft-bells.mp3'
        self.sound = SoundLoader.load(self.soundfile)
        
    def play_sound(self):
        if self.sound:
            self.sound.loop = True
            self.sound.volume = 0.05
            self.sound.play()
            
            Clock.schedule_once(partial(self.increase_volume,0.1),5)
            Clock.schedule_once(partial(self.increase_volume,0.1),10)
            Clock.schedule_once(partial(self.increase_volume,0.1),15)
            Clock.schedule_once(partial(self.increase_volume,0.1),20)
            Clock.schedule_once(partial(self.increase_volume,0.1),25)
            Clock.schedule_once(partial(self.increase_volume,0.1),30)
            
    def stop_sound(self):
        if self.sound:
            self.sound.stop()
            
    def increase_volume(self,dv,*args):
        if self.sound:
            self.sound.volume = min(self.sound.volume + dv,1)
            

class Alarm():
        
    def __init__(self,AlarmTime,IsActive,SnoozeLength,WULLength,WULColor, **rest):
        self.AlarmTime = AlarmTime
        self.IsActive = IsActive
        self.SnoozeLength = SnoozeLength
        self.WULLength = WULLength
        self.WULColor = WULColor

        self.status = ALARM_STATUS_ACTIVE
        WULTime = (datetime.now().replace(hour=self.AlarmTime.hour,minute=self.AlarmTime.minute,second=self.AlarmTime.second,microsecond=0) - timedelta(minutes=self.WULLength)).time()
        
        self.SnoozeTime = None
    
    
    
    def MinutesAfterMidnight(self):
        return self.AlarmTime.hour * 60 + self.AlarmTime.minute
        
    def to_string(self):
        return(self.AlarmTime.isoformat())
    
    def get_status(self):
        return self.status
        
    def set_status(self,status):
        self.status = status
        
    def get_alarmtime(self):
        #Return datetime object when alarm should sound
        return self.AlarmTime
    
    def get_lighttime(self):
        #Return datetime object when light should turn on
        return self.get_alarmtime() - datetime.timedelta(minutes=self.WULLength)
    
    def toggle_active(self,instance,value):
        self.IsActive = value
    
    def should_sound(self):
    
        if(self.IsActive):
            #Alarm is active, check if something should happen
            
            if(self.get_status() in (ALARM_STATUS_ACTIVE,ALARM_STATUS_WAKE_UP) and self.get_alarmtime().hour == datetime.now().hour and self.get_alarmtime().minute == datetime.now().minute):
                #Alarm should go off
                self.set_status(ALARM_STATUS_SOUNDING)
                return True
                
            if(self.get_status() == ALARM_STATUS_SNOOZED):
                
                time_until_snooze = (self.SnoozeTime-datetime.now()).total_seconds()
                if (time_until_snooze < 3):
                    self.set_status(ALARM_STATUS_SOUNDING)
                    return True
    
        
    def snooze(self):
        #TODO: fix string/datetime/time issues
        self.SnoozeTime = (datetime.now() + timedelta(minutes=self.SnoozeLength))
        print(self.SnoozeTime)
        self.set_status(ALARM_STATUS_SNOOZED)
        print("Snooze")
        
    def dismiss(self):
        print("Dismiss")
        
class SoundPopup(Popup):

    def on_press_dismiss(self, *args):
        self.dismiss()
        return False
        
class ColorPopup(Popup):
    lc = LEDControl()

    def pick_color(self, r,g,b,w):
        self.set_alarm_color(r,g,b,w)
        self.dismiss()
        return False
        
    def test_color(self,state,r,g,b,w):
        if(state=='down'):
            self.lc.set_LED(r,g,b,w)
            
        if(state=='normal'):
            self.lc.set_LED(0,0,0,0)
        
class AlarmPopup(Popup):
    sp = SoundPlayer()
    alarm = None

    def snooze_alarm(self, *args):
        self.sp.stop_sound()
        self.alarm.snooze()
        self.dismiss()
        return False
        
    def dismiss_alarm(self, *args):
        self.sp.stop_sound()
        self.alarm.dismiss()
        self.dismiss()
        return False

class AlarmApp(Widget):
    clock_string = StringProperty()
    selected_color = [0,0,0,0]
    
    #Set low screen brightness as initial brightness
    screen_status = SCREEN_LOW
    bl.set_brightness(LOW_BRIGHTNESS)
    
    last_activity = datetime.now()
    
    
    def __init__(self, **kwargs):
        super(AlarmApp, self).__init__(**kwargs)
        self.clock_string = datetime.now().strftime("%H:%M")
        Clock.schedule_interval(self.update_clock, 1)
        self.JSONToAlarms()
        self.build_overview()
        self.sp = SoundPlayer()
        self.lc = LEDControl()
        
        sensor_tap_event = pi.callback(TAP_SENSOR_PIN, pigpio.EITHER_EDGE, self.sensor_tap)
        sensor_light_on_event = pi.callback(LIGHT_SENSOR_PIN, pigpio.FALLING_EDGE,self.sensor_light_on)
        sensor_light_off_event = pi.callback(LIGHT_SENSOR_PIN, pigpio.RISING_EDGE,self.sensor_light_off)
        
        self.tap_count = 0
        #self.last_tap_sensor = datetime.now()
        self.last_tap = datetime.now()
        Window.bind(on_motion=self.on_motion)
        
    def on_motion(self,*args):
        #something touched the screen
        self.last_activity = datetime.now()

    def sensor_tap(self, pin_no, state, timestamp):
        
        time_since_last_tap = (datetime.now()-self.last_tap).total_seconds()
        self.last_tap = datetime.now()
        
        if (time_since_last_tap>1):
            #This is a new tap
            self.tap_count = self.tap_count+1
            self.last_tap = datetime.now()
            self.last_activity = self.last_tap
            print(self.tap_count)
            print(time_since_last_tap)
            
            #turn up brightness if lower
            if(self.screen_status == SCREEN_OFF):
                bl.set_brightness(LOW_BRIGHTNESS)
                self.screen_status = SCREEN_LOW
            elif(self.screen_status == SCREEN_LOW):
                bl.set_brightness(HIGH_BRIGHTNESS)
                self.screen_status = SCREEN_HIGH
                
            #turn off alarm if sounding
            for alarm in Alarms:
                if(alarm.status==ALARM_STATUS_SOUNDING):
                    alarm.snooze()
                    print("Found sounding alarm")
        
    def sensor_light_on(self, pin_no, state, timestamp):
        print("Light ON")
        
    def sensor_light_off(self, pin_no, state, timestamp):
        print("Light OFF")

    def update_clock(self, dt):
        #Set clock label
        self.clock_string = datetime.now().strftime("%H:%M")
        
        #Check if there is something to do
        for alarm in Alarms:
            if(alarm.should_sound()):
                self.sound_alarm(alarm)
                
        #check how long the last activity was
        time_since_last_activity = (datetime.now() - self.last_activity).total_seconds()
        
        #Set low screen brightness
        if(time_since_last_activity > 10 and self.screen_status == SCREEN_HIGH):
            bl.set_brightness(LOW_BRIGHTNESS)
            self.screen_status = SCREEN_LOW

                
        
    def alarm_popup(self, alarm):
        p = AlarmPopup()
        p.sp = self.sp
        p.alarm = alarm
        p.open()
        
    def sound_popup(self, *args):
        p = SoundPopup()
        p.open()
        
    def color_popup(self, *args):
        p = ColorPopup()
        p.lc = self.lc
        p.set_alarm_color = self.set_selected_color
        p.open()
        
    def set_selected_color(self,r,g,b,w):
        self.selected_color = [int(r),int(g),int(b),int(w)]
    
    def set_alarm(self, *args):
        hour = args[0]
        minute = args[1]
        snoozelength = args[2]
        wullength = args[3]
        alarmtime = time(hour,minute)
        isactive = True
        Alarms.append(Alarm(alarmtime,isactive,snoozelength,wullength,self.selected_color))
        self.build_overview()
        self.AlarmsToJSON()
        
    def AlarmsToJSON(self):
        with io.open('/home/pi/alarm/Alarms.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(Alarms, cls=DateJSONEncoder, indent=4))
        print("Written to json")
        
        
    def JSONToAlarms(self):
        print("reading json")
        with open('/home/pi/alarm/Alarms.json') as f:    
            jsonalarms = json.load(f,cls=DateJSONDecoder)
        for a in jsonalarms:
            Alarms.append(Alarm(**a))

    
    def sound_alarm(self,alarm):
        self.alarm_popup(alarm)
        self.sp.play_sound()
        alarm.status = ALARM_STATUS_SOUNDING

    def testfunction(self):
        print("test")
        #self.lc.set_LED_gradient(datetime.now()+timedelta(seconds=2),datetime.now()+timedelta(seconds=12),[0,0,0,0],[0,0,0,255])
        self.sound_alarm(Alarms[0])
        
    def delete_alarm(self,alarm,button):
        Alarms.remove(alarm)
        self.build_overview()
        self.AlarmsToJSON()
        
    
    def build_overview(self):
        alarm_overview = self.ids['Alarm_Overview_Stack']
        alarm_overview.bind(minimum_height=alarm_overview.setter('height'))
        alarm_overview.clear_widgets(children=None)
        
        SortedAlarms =sorted(Alarms, key=lambda Alarm: Alarm.MinutesAfterMidnight())
        for alarm in SortedAlarms:
            
            alarm_overview.add_widget(Label(text=alarm.to_string(),font_size=25,height=80,size_hint=(0.4,None)))
            
            alarm_switch = Switch(active=alarm.IsActive,height=80,size_hint=(0.3,None))
            alarm_switch.bind(active=alarm.toggle_active)
            
            alarm_delete = Button(background_normal='images/AccordionSelected.png',height=64,size_hint=(0.2,None))
            alarm_delete.bind(on_press=partial(self.delete_alarm, alarm))
            
            alarm_overview.add_widget(alarm_switch)
            alarm_overview.add_widget(alarm_delete)
        
class AlarmGUIApp(App):
    label_size = NumericProperty(25)
    set_alarm_label_width = NumericProperty(0.45)
    set_alarm_value_width = NumericProperty(0.15)
    pick_color_label_width = NumericProperty(0.2) 
    
    def build(self):
        root = AlarmApp()
        

        return root

try:
    if __name__ == '__main__':
        AlarmGUIApp().run()
except KeyboardInterrupt:
    pi.set_PWM_dutycycle(RED_PIN,0)
    pi.set_PWM_dutycycle(GREEN_PIN,0)
    pi.set_PWM_dutycycle(BLUE_PIN,0)
    pi.set_PWM_dutycycle(WHITE_PIN,0)
    pi.stop()
    bl.set_brightness(254)
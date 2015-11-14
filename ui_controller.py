from sense_hat import SenseHat
from evdev import InputDevice, list_devices, ecodes
import time


class Controller(object):
    def __init__(self):
        self.sense = SenseHat()
        self.sense.clear()
        self.found = False
        self.dev = None
        self.running = False
        devices = [InputDevice(fn) for fn in list_devices()]
        for dev in devices:
            if dev.name == 'Raspberry Pi Sense HAT Joystick':
                self.dev = dev
                self.found = True
                self.running = True
                break

    def on_button_pressed(self, event):
       raise NotImplementedError("Please Implement Button Pressed Method")

    def on_button_released(self, event):
        raise NotImplementedError("Please implement BUtton Released Method") 

    def pre_input_event(self):
        pass

    def run(self):
        while self.running:
            self.pre_input_event()
            event = self.dev.read_one()
            if event:
                if event.value == 1:
                    self.on_button_pressed(event) 
                if event.value == 0:
                     self.on_button_released(event) 

    def reset(self):
        raise NotImplementedError("Please implement reset method") 

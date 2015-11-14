from sense_hat import SenseHat
from evdev import InputDevice, list_devices, ecodes
import sys
import time
from threading import Thread
from threading import Event
from ui_controller import Controller
from Queue import Queue
from Queue import Empty
import csv
import logging
from sklearn.ensemble import RandomForestClassifier
import os
import copy


logger = logging.getLogger("Weather Machine Logger")
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("weather.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

SUNNY = 0
CLOUDY = 1
RAIN = 2

input_queue = Queue()
predict_queue = Queue()
training_queue = Queue()
stop_event = Event()


class WeatherComputer(Thread):
    def __init__(self, input_queue, predict_queue, training_queue, data_file, stop_event):
        self.input_queue = input_queue
        self.predict_queue = predict_queue
        self.training_queue = training_queue
        self.training_data = []
        self.training_output = []
        self.data_file = data_file
        self.stop_event = stop_event
        self.training_size = 20
        self.training_done = False
        self.classifier = RandomForestClassifier(n_estimators=10)
        logger.debug("thread init")
        super(WeatherComputer, self).__init__()

    def run(self):

        self.load_data()
        if len(self.training_data) > self.training_size:
            self.classifier.fit(self.training_data, self.training_output)
            self.training_done = True
            logger.debug("Initial training complete")
        else:
            logger.debug("Not enough data for initial training, data size %s" % len(self.training_data))

        logger.debug("Thread running")
        prediction_time = time.time()
        while not self.stop_event.is_set():
            data = self.input_queue.get()
            logger.debug("Data fetched: %s" % str(data)) 
            # Predicted answer on top, then the other at the end
            if prediction_time < time.time():
                if self.training_done:
                    result = self.classifier.predict([ data ])
                    prediction = [ int(result[0]) ]
                    if not SUNNY in prediction:
                        prediction.append(SUNNY)
                    if not CLOUDY in prediction:
                        prediction.append(CLOUDY)
                    if not RAIN in prediction:
                        prediction.append(RAIN)
                    logger.debug("prediction sent:%s" % str(prediction))
                    self.predict_queue.put(prediction)
                else:
                    prediction = [ SUNNY, CLOUDY, RAIN ]
                    self.predict_queue.put(prediction)
                    logger.debug("prediction sent:%s" % str(prediction))
                prediction_time = prediction_time + 3600
                logger.debug("next prediction at %s" % prediction_time)
            # if prediction is true, add to training set anyway
            try:
                logger.debug("training started")
                training = self.training_queue.get(timeout=5)
                logger.debug("training data is %s" % training)
                self.training_data.append(data)
                self.training_output.append(training)
                if len(self.training_data) > self.training_size:
                    self.classifier.fit(self.training_data, self.training_output)
                    self.training_done = True
                    logger.debug("training complete")
                else:
                    logger.debug("Not enough data to train, data size %s" % len(self.training_data))
                self.save_data()
            except Empty:
                logger.debug("no training")
            time.sleep(0.1)

        logger.debug("quit")
        self.save_data()
        time.sleep(1)

    def load_data(self):
        if not os.path.exists(self.data_file):
            return
        with open(self.data_file, 'rb') as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                self.training_data.append(row[:-1])
                self.training_output.append(row[-1])

    def save_data(self):
        logger.debug("writing data to %s " % self.data_file)
        with open(self.data_file, 'wb') as csv_file:
            writer = csv.writer(csv_file)
            if not self.training_data:
                return
            temp = zip(self.training_data, self.training_output)
            for entry in temp:
                x, y = entry
                logger.debug("x:%s,y: %s" % (entry))
                t = copy.deepcopy(x)
                t.append(y)
                writer.writerow(t)


class WeatherGuy(object):
    def correction(self, result):
        training_queue.put(result)

    def request_prediction(self, data):
        # This will block
        logger.debug("Putting data %s" % str(data))
        input_queue.put(data)
        logger.debug("Done Putting data %s" % str(data))
        # No prediction is fine, we only give 1 prediction every hour
        try:
            logger.debug("fetching data")
            prediction = predict_queue.get(timeout=1)
            logger.debug("Done fetching data")
        except Empty:
            logger.debug("No prediction")
            prediction = []
        return prediction

    def quit(self):
        logger.debug("quitting")
        stop_event.set()


class WeatherController(Controller):
    def __init__(self):
        self.img_set = False
        self.weather_guy = WeatherGuy()
        self.result = None
        self.img = ""
        self.predictions = []
        self.pos = 0
        super(WeatherController, self).__init__()

    def pre_input_event(self):
        logger.debug("fetch data")
        data = fetch_data(self.sense)
        predictions = self.weather_guy.request_prediction(data)
        logger.debug("Predictions is: %s" % str(predictions))
        if predictions:
            self.predictions = predictions
            self.result = predictions[self.pos]
            logger.debug("Result is %s" % self.result)
        logger.debug("load image")
        self.set_current_image()
       
    def set_current_image(self):
        if self.result == SUNNY:
            self.sense.load_image("sun.png")
        elif self.result == CLOUDY:
            self.sense.load_image("cloudy.png")
        elif self.result == RAIN:
            self.sense.load_image("rain.png")
        logger.debug("image loaded")

    def on_button_pressed(self, event):
        logger.debug("button pressed")
        self.sense.clear()
        time.sleep(1)
        status, img=handle_code(event.code)
        # If we don't have preddiction don't bother training them
        if self.predictions:
            if not status:
                logger.debug("Wrong, test %s next" % self.predictions[self.pos])
                self.pos = self.pos + 1
                if self.pos > 2:
                    self.pos = 0
                self.result = self.predictions[self.pos]
            else:
                logging.debug("Correct, sending %s" % self.result)
                self.weather_guy.correction(self.result)

        if img:
            self.sense.load_image(img)
            self.img_set = True
        else:
            self.sense.clear()
            self.img_set = False

    def on_button_released(self, event):
        logger.debug("button released")
        if self.img_set:
            self.img_set = False
        self.sense.clear()
        self.set_current_image()

    def reset(self):
        self.weather_guy.quit()
        self.sense.clear()

    def run(self):
        while self.running:
            self.pre_input_event()
            event = self.dev.read_one()
            logger.debug("event is %s" % event) 

            if event:
                logging.debug("found event")
                if event.value == 1:
                    self.on_button_pressed(event) 
                if event.value == 0:
                     self.on_button_released(event) 
            time.sleep(0.1)



def handle_code(code):
    img_file = ""
    status = False
    if code == ecodes.KEY_DOWN:
        img_file = "cross.png"
        status = False
    elif code == ecodes.KEY_UP:
        img_file = "circle.png"
        status = True
    
    return status, img_file

def fetch_data(sense):
    p_temp = sense.get_temperature_from_pressure()
    h_temp = sense.get_temperature_from_humidity()
    humidity = sense.get_humidity()
    pressure = sense.get_pressure()
    return [ p_temp, h_temp, humidity, pressure ]

def main():
    logger.debug("starting up")
    thread = WeatherComputer( input_queue, predict_queue, training_queue, "data.csv", stop_event)
    thread.daemon = True
    thread.start()
    controller = WeatherController()
    if not controller.found:
        stop_event.set()
        sys.exit()
    try:
        logger.debug("run from main")
        controller.run() 
    except KeyboardInterrupt:
        logger.debug("interrupt started")
        controller.reset()
    
if __name__ == "__main__":
    main()

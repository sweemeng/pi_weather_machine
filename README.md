# pi weather machine
Toy project to use raspberry pi sense hat with a sklearn classifier to try to predict weather. Currently the flow is a bit wonky. 

## Requirement
1. the sense hat library for python. https://pythonhosted.org/sense-hat/
2. the evdev library for python. https://python-evdev.readthedocs.org/
3. Scikit Learn. FYI I use the one comes with the repo raspbian, not up to date, but it get the job done. 

## Why?
1. The sense hat have 2 temperature sensor, 1 pressure sensor, 1 humidity sensor
2. The pi runs linux, so at least some ML algorithm can work. 
3. Not all ML algoritm is computationally expensive
4. It is a linux machine, and it have python. We just offload to whatever ML service if it is not good enough
5. I am bored

## Note
1. Yeah training using push button is stupid
2. In fact, I should really try to put that water sensor I have, and plug it to the ESP8266 that have have. To automate everything. 
3. In fact the prediction sucked
4. It is fun though
5. UI Controller might be a useful framework that I should extract out
6. My ability to make a 8x8 pixel art is horrible

## Photo of it at work
![stupid pi trick](http://i.imgur.com/IazWK39.jpg)

## To run it,
```
$ sudo python weather_machine.py
```

1) Move joystick up if prediction is correct. You will see a circle
2) Down if not, you will see a cross. 
3) THen it will present the next guess, if it is right, do 1) It will submit to the predictor for training

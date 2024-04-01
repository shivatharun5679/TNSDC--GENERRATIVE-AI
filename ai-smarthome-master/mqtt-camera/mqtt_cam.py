#
# This integration is towards MQTT in Home-Assistant and can easily
# be configured to provide both images streamed unfiltered or diff-filtered.
#
# Author: Joakim Eriksson, joakim.eriksson@ri.se
#

import paho.mqtt.client as mqttClient
import threading, time, yaml
import numpy as np, sys, time
import cv2

class MQTTCamera:

    def __init__(self, mqttBroker, camera=0, topic="ha/camera/mqtt"):
        self.show = True
        self.broker = mqttBroker
        self.camera = camera
        self.topic = topic
        self.send_frames = 0
        self.cap = cv2.VideoCapture(camera)
        # First frame is average...
        ret, self.avgframe = self.cap.read()
        connect("Python-mqtt-cam")

    def connect(self, name):
        self.client = mqttClient.Client(name)
        self.client.on_connect = self.on_connect
        self.client.connect(self.broker)
        self.client.loop_start()
        
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to broker:", rc)
        else:
            print("Connection failed: ", rc)

    def diff_filter(self, frame, avgframe):
        subframe = cv2.subtract(frame, avgframe)
        grayscaled = cv2.cvtColor(subframe, cv2.COLOR_BGR2GRAY)
        retval2,th1 = cv2.threshold(grayscaled,35,255,cv2.THRESH_BINARY)
        avgframe = cv2.addWeighted(frame, 0.1, avgframe, 0.9, 0.0)

        if self.show:
            cv2.imshow('Treshold diff', th1)

        th1 = th1 / 255
        w, h = th1.shape
        sum = cv2.sumElems(th1)[0]/(w*h)
        return avgframe, sum

    def publish_image(self, frame):
        if self.client == None:
            return
        self.client.publish(self.topic, frame)

    def camera_loop(self):
        fc = 0
        while(True):
            # Capture frame-by-frame
            ret, frame = self.cap.read()

            self.avgframe, sum = self.diff_filter(frame, self.avgframe)
            if sum > 0.01:
                print("Publishing image diff:", sum)
                self.publish_image(cv2.imencode('.png', frame)[1].tostring())

            # publish each send_frames frame
            if self.send_frames > 0 and fc % self.send_frames == 0:
                print("Publish frame")
                self.publish_image(cv2.imencode('.png', frame)[1].tostring())
            # Our operations on the frame come here
            #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Display the resulting frame
            if self.show:
                fc = fc + 1

                if fc % 1 == 0:
                    cv2.imshow('frame',frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        self.cap.release()


if __name__ == '__main__':
    video = 0
    if len(sys.argv) > 1:
        video = sys.argv[1]

    mqCam = MQTTCamera("localhost", video, topic="ha/camera/mqtt")
    mqCam.show = False
    mqCam.camera_loop()

    # When everything done, release the capture
    cv2.destroyAllWindows()

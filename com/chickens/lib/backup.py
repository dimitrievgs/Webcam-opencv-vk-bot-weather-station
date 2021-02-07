import numpy as np
import cv2

import imutils
import datetime

outputFilename = 'output.avi'

FRAME_RATE = 20.0
frameSize = (640, 480)
SECONDS_TO_RUN_FOR = 10

# WARNING **: Error retrieving accessibility bus address: org.freedesktop.DBus.Error.ServiceUnknown: The name org.ally.Bus...
# https://www.raspberrypi.org/forums/viewtopic.php?t=131102


class WebCamera2(object):
    """docstring"""

    def __init__(self, _FRAME_RATE, _SECONDS_TO_RUN_FOR, _outputFilename):
        """Constructor"""
        self.outputFilename = _outputFilename

        self.FRAME_RATE = 20.0
        self.frameSize = (640, 480)
        self.SECONDS_TO_RUN_FOR = _SECONDS_TO_RUN_FOR
        self.doLive_or_VideoWrite = True

        self.cap = cv2.VideoCapture(0)

        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter(outputFilename, fourcc, FRAME_RATE, frameSize)

    def CaptureAndWrite(self):
        while (self.cap.isOpened()):
            ret, frame = self.cap.read()
            if ret == True:
                # frame = cv2.flip(frame,0)

                # write the flipped frame
                self.out.write(frame)

                cv2.imshow('frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break

    def MotionDetection(self):
        min_area = 500

        firstFrame = None
        # loop over the frames of the video
        while True:
            # grab the current frame and initialize the occupied/unoccupied
            # text
            ret, frame = self.cap.read()
            #frame = frame[1] #frame if args.get("video", None) is None else frame[1]
            text = "Unoccupied"

            # if the frame could not be grabbed, then we have reached the end
            # of the video
            if frame is None:
                break

            # resize the frame, convert it to grayscale, and blur it
            frame = imutils.resize(frame, width=500)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # if the first frame is None, initialize it
            if firstFrame is None:
                firstFrame = gray
                continue
            # compute the absolute difference between the current frame and
            # first frame
            frameDelta = cv2.absdiff(firstFrame, gray)
            thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

            # dilate the thresholded image to fill in holes, then find contours
            # on thresholded image
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if imutils.is_cv2() else cnts[1]

            # loop over the contours
            for c in cnts:
                # if the contour is too small, ignore it
                if cv2.contourArea(c) < min_area:
                    continue

                # compute the bounding box for the contour, draw it on the frame,
                # and update the text
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                text = "Occupied"

            # draw the text and timestamp on the frame
            cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(frame, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
                        (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

            # show the frame and record if the user presses a key
            cv2.imshow("Security Feed", frame)
            cv2.imshow("Thresh", thresh)
            cv2.imshow("Frame Delta", frameDelta)
            key = cv2.waitKey(1) & 0xFF

            # if the `q` key is pressed, break from the lop
            if key == ord("q"):
                break

    def Close(self):
        # Release everything if job is finished
        self.cap.release()
        self.out.release()
        cv2.destroyAllWindows()


webCamera = WebCamera(FRAME_RATE, SECONDS_TO_RUN_FOR, outputFilename)
webCamera.MotionDetection()
webCamera.Close()

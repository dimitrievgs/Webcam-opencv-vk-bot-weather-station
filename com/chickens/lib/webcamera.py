import copy
import gc
import math
import os
import psutil
import threading
from threading import Thread
from time import sleep

import numpy as np
import cv2 # opencv-python

import imutils
import datetime
import time
import pygame

import av # pip install av

from com.chickens.lib.ArduinoTalk import *
from com.chickens.lib.ParametersInfo import MemoryInfo, SensorsInfo
from com.chickens.lib.Threads import Threads
from com.chickens.lib.TimeStuff import *


# WARNING **: Error retrieving accessibility bus address: org.freedesktop.DBus.Error.ServiceUnknown: The name org.ally.Bus...
# https://www.raspberrypi.org/forums/viewtopic.php?t=131102

# Exceptions: https://pythonworld.ru/tipy-dannyx-v-python/isklyucheniya-v-python-konstrukciya-try-except-dlya-obrabotki-isklyuchenij.html


class WebCamera(object):
    """docstring"""

    def __init__(self, _FRAME_RATE, _SECONDS_TO_RUN_FOR, main_py_path, _output_Photo_Filename, _output_Video_Filename,
                 ArduinoTalker, VkTalker, _MemoryUsageInfo_RefreshTime):
        """Constructor"""
        self.output_Photo_Filename = _output_Photo_Filename
        self.output_Video_Filename = _output_Video_Filename
        self.FRAME_RATE = _FRAME_RATE
        self.SECONDS_TO_RUN_FOR = _SECONDS_TO_RUN_FOR
        self.frameSize = (640, 480)
        self.WinName = 'Webcam'

        self.ArduinoTalker = ArduinoTalker
        self.VkTalker = VkTalker

        self.show_in_window = False  # because of Pycharm bugs
        self.Monitor_Memory = True

        self.MemoryUsageInfo_RefreshTime = _MemoryUsageInfo_RefreshTime

        # Image Watermark
        self.wm_format = "%d.%m.%Y %H:%M:%S"  # "%A %d %B %Y %I:%M:%S%p"
        self.wm_X = self.frameSize[0] - 245
        self.wm_Y = 22
        self.wm_Y_shift = 22
        self.fontScale = 0.7  # fontScale = 0.35
        self.fontColor = (255, 255, 255)

        # https://pymotw.com/2/threading/
        self.MainThreads = []
        self.JobThreads = []
        self.activities = []

        self.photos_directory = main_py_path + '/' + 'photos/'
        if not os.path.exists(self.photos_directory):
            os.makedirs(self.photos_directory)
        self.Photo_FilePath = self.photos_directory + self.output_Photo_Filename

        self.videos_directory = main_py_path + '/' + 'videos/'
        if not os.path.exists(self.videos_directory):
            os.makedirs(self.videos_directory)
        self.Video_FilePath = self.videos_directory + self.output_Video_Filename

        self.reports_directory = main_py_path + '/' + 'reports/'
        if not os.path.exists(self.reports_directory):
            os.makedirs(self.reports_directory)

        self.MemoryUsage_file = self.reports_directory + 'MemoryUsage.txt'
        text_file = open(self.MemoryUsage_file, 'w')
        text_file.flush()
        text_file.close()

        self.lockGrabber = threading.Lock()

        pos_x = 0
        pos_y = 0
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (pos_x, pos_y)  # set pygame display position
        pygame.init()  # Initialize pygame

        self.PrintTooMuchFramesSec = False

        self.collect_statictics = True
        self.ArduinoData_last_Timestamp = -1

        self.ArduinoParameters_statistics = []
        self.MemoryUsage_statistics = []

        self.MemoryUsage_lastData = None # or get error if firstly ask for photo

        #self.PrepareForWork()

    ################ Preparations ################

    def PrepareForWork(self):
        self.CapturedFrame = None
        self.ProcessedFrame = None
        self.StartFrame_TimeStamp = -100
        self.LastFrame_TimeStamp = -100
        self.StopActivityRequest = False

        self.MainThreads.clear()
        self.JobThreads.clear()
        self.activities.clear()
        self.ArduinoParameters_statistics.clear()
        self.MemoryUsage_statistics.clear()
        self.MemoryUsage_lastData = None

        self.startTime = time.time()

        # https://www.pygame.org/docs/ref/display.html
        if self.show_in_window == True:
            pygame.display.init()
            self.display = pygame.display.set_mode(self.frameSize, 0)
            pygame.display.set_caption('Webcamera image')

    def CleanUpAll(self):
        self.MainThreads.clear()
        self.JobThreads.clear()
        self.activities.clear()
        self.ArduinoParameters_statistics.clear()

        if self.show_in_window == True:
            pygame.display.quit()
        gc.collect()

    ################ Init input and output ################

    def Init_Camera(self):
        self.capturer = cv2.VideoCapture()
        self.capturer.open(0)

    def Release_Camera(self):
        self.capturer.release()

    def Init_VideoFileOutput(self):
        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(
            *'XVID')  # *'XVID'->*.avi (это MPEG-4)  /   *'FLV1'->*.flv   /*'X264'   /*'mp4v'
        self.out = cv2.VideoWriter(self.Video_FilePath, fourcc, self.FRAME_RATE, self.frameSize)
        # self.FRAME_RATE here is just about setting frameRate for each new frame in output video file,
        # not about grabbing from webcamera
        self.Video_Record_StartTime = time.time()

    def Release_VideoFileInput(self):
        self.out.release()
        self.Video_Record_FinishTime = time.time()

    #def Destroy_Windows(self):
    #    cv2.destroyAllWindows()  # looks like it doesn't work with windows from other threads

    ################ Capture stuff ################

    def Capture_Job(self):
        # self.PrepareForWork()  # only after that signal others that we have started

        self.activities.append('Capture')

        try:
            self.Init_Camera()

            TargetDelayTime_d = 1.0 / self.FRAME_RATE

            frameCounter = 0.0
            # ProcessedTimes = []
            # LeftTimes = []
            startT = 0.0
            prevT = 0.0

            while (self.capturer.isOpened() and self.StopActivityRequest == False):
                ret, frame, framePr = self.GetImage_w_TimeStamp()
                # for some reason it grabs frames faster or slower, than self.FRAME_RATE
                # looks like it's okay
                if ret == True:
                    if (frameCounter == 0):  # because in the beginning it freezes for more than 1-1.5 seconds
                        startT = time.time()
                        prevT = startT
                        currentT = startT
                        self.Video_Record_StartTime = startT
                    else:
                        currentT = time.time()

                    self.Put_Frame(frame, framePr)
                    if self.show_in_window == True:
                        self.ShowImage(framePr)

                    # ProcessedTimes.append((currentT - prevT) * 1000.0)  # ms
                    TimeLeft_ms = frameCounter * TargetDelayTime_d - (
                            currentT - startT)  # may be I need to wait smth ms in the beginning?
                    prevT = currentT
                    # Left_DelayTime = math.floor(TimeLeft_ms)
                    if (TimeLeft_ms < 0):
                        TimeLeft_ms = 0
                        if (self.PrintTooMuchFramesSec == True):
                            print("Too much frames/sec, frame = " + str(frameCounter))
                    # LeftTimes.append(TimeLeft_ms * 1000.0)
                    sleep(TimeLeft_ms)

                    frameCounter += 1.0
                else:
                    # self.doLive_or_VideoWrite = False
                    break

            finishT = time.time()
            self.Video_Record_FinishTime = finishT
            real_fps = frameCounter / (finishT - startT)
            print("Frames count = " + str(frameCounter) + ", real fps = " + ('%.2f' % real_fps))
            TimeStuff.PrintElapsedTime(startT, finishT)

            # self.Release_Camera()
        finally:
            self.Release_Camera()  # ???

        self.activities.remove('Capture')

        '''thefile1 = open(self.videos_directory + 'ProcessedTimes.txt', 'w')
        for item in ProcessedTimes:
            thefile1.write("%.2f\n" % item)
        thefile2 = open(self.videos_directory + 'LeftTimes.txt', 'w')
        for item in LeftTimes:
            thefile2.write("%.2f\n" % item)'''

    def Wait_for_CapturerStart(self):
        # may be lock needed here???
        while ('Capture' not in self.activities):
            sleep(10)

    def Capture_Works(self):
        return ('Capture' in self.activities)  # check if 'Capture' thread was crashed - made in Wait_forThreads_Close

    def Any_Activity(self):
        return len(self.activities) > 0

    def Wait_for_noActivity(self):
        while (self.Any_Activity() == True):
            sleep(0.01)

    def GrabberFrames_Manipulation(self, _capturedFrame, _processedFrame, to_add):  # already check with ret that it is not None
        self.lockGrabber.acquire()
        result = None, None
        if (to_add == True):  # write frame
            if not (_capturedFrame is None):
                # if (len(_capturedFrame) > 0): # empty sequences are false
                self.CapturedFrame = _capturedFrame
                self.ProcessedFrame = _processedFrame
            # LastFrame_TimeStamp = capturedFrame.timestamp
        else:  # read frame
            if not (self.CapturedFrame is None):
                # if (len(self.CapturedFrame) > 0):
                capturedFrame = self.CapturedFrame  # .copy()  # ??? check if really works and needed (to clone)
                processedFrame = self.ProcessedFrame
                result = capturedFrame, processedFrame
        self.lockGrabber.release()
        return result

    def Get_LastFrame(self):
        return self.GrabberFrames_Manipulation(None, None, False)

    def Put_Frame(self, capturedFrame, processedFrame):
        self.GrabberFrames_Manipulation(capturedFrame, processedFrame, True)

    def Wait_ForFrame(self, thread_LastFrameTimestamp):
        while (self.LastFrame_TimeStamp <= thread_LastFrameTimestamp and self.Capture_Works()):
            sleep(0.01)
        capturedFrame, processedFrame = self.Get_LastFrame()  # lets think that we guaranteed that to this time capturedFrame != null
        return capturedFrame, processedFrame

    def GetImage_w_TimeStamp(self):
        ret, frame, framePr = self.GetImage()

        # Create timestamp for this frame
        # videoTS = 1000 * (System.currentTimeMillis() - startTime);
        curTime = time.time() * 1000000.0
        if (self.StartFrame_TimeStamp < 0):
            self.StartFrame_TimeStamp = curTime
            self.LastFrame_TimeStamp = 0
        else:
            self.LastFrame_TimeStamp = curTime - self.StartFrame_TimeStamp  # may be need to pass?.. will be better
        return ret, frame, framePr

    def GetImage(self):
        ret, frame = self.capturer.read()
        framePr = frame.copy()
        framePr = self.ApplyWatermark(framePr)  # processed

        return ret, frame, framePr

    def ApplyWatermark(self, frame):
        Arduino_parameters = self.ArduinoTalker.Get_SensorsParameters()
        SI = SensorsInfo(Arduino_parameters)

        cv2.putText(frame, datetime.datetime.now().strftime(self.wm_format),
                    (self.wm_X, self.wm_Y), cv2.FONT_HERSHEY_SIMPLEX, self.fontScale, self.fontColor, 1)

        # for degree symbol I need to use QT_Font -> arial (https://github.com/opencv/opencv/pull/3614)
        # but no idea how to make it in python and it could slow down watermark application

        s2 = ''

        if (SI.OK == True):
            if (self.collect_statictics == True and self.ArduinoData_last_Timestamp != SI.Time):
                self.ArduinoData_last_Timestamp = SI.Time
                self.ArduinoParameters_statistics.append(SI)

            s1 = ("%.1f" % SI.Wout_temperature) + ' C, ' + ("%.1f" % SI.Wout_humidity) + ' %'
            cv2.putText(frame, s1, (self.wm_X, self.wm_Y + self.wm_Y_shift), cv2.FONT_HERSHEY_SIMPLEX, self.fontScale, self.fontColor, 1)

            s2 += ("%.0f" % SI.Light) + ' lux'

        if self.Monitor_Memory == True and not self.MemoryUsage_lastData is None: # not enough statement
            if len(s2) > 0:
                s2 += ', '
            s2 += ("%.0f" % self.MemoryUsage_lastData.MemoryUsage) + ' mb'

        cv2.putText(frame, s2, (self.wm_X, self.wm_Y + 2 * self.wm_Y_shift), cv2.FONT_HERSHEY_SIMPLEX, self.fontScale, self.fontColor, 1)

        return frame

    ################ Show image ################

    def ShowImage(self, frame):
        pg_img = self.CV_To_Pygame_Image(frame)
        self.display.blit(pg_img, (0, 0))
        pygame.display.update()

        # cv2.imshow(self.WinName, frame)
        # key = cv2.waitKey(1)  # imshow will not work without this

    def CV_To_Pygame_Image(self, frame):
        frame2 = frame  # copy.deepcopy(frame)
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
        frame2 = cv2.transpose(frame2)
        pg_img = pygame.surfarray.make_surface(frame2)
        return pg_img

    ################ Other Jobs ################

    def VideoWrite_Job(self, user_id):
        self.activities.append('Video Write')
        self.Init_VideoFileOutput()

        thread_LastFrame_Timestamp = -1
        self.Wait_for_CapturerStart()

        while (self.Capture_Works()):
            capturedFrame, processedFrame = self.Wait_ForFrame(thread_LastFrame_Timestamp)
            thread_LastFrame_Timestamp = self.LastFrame_TimeStamp
            self.out.write(processedFrame)
            # print("Write cadre to video... " + ("%.2f" % thread_LastFrame_Timestamp) + " s")

        self.Release_VideoFileInput()
        self.activities.remove('Video Write')

    # https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
    def MotionDetection_Job(self, user_id):
        self.activities.append('Motion Detection')

        self.VkTalker.DeleteOldLiveVideos() # sporno!

        self.Init_VideoFileOutput()
        thread_LastFrame_Timestamp = -1

        self.Wait_for_CapturerStart()

        min_area = 500
        FrameNumber = 0
        prevGray = None
        # loop over the frames of the video
        while (self.Capture_Works()):
            # grab the current frame and initialize the occupied/unoccupied
            capturedFrame, processedFrame = self.Wait_ForFrame(thread_LastFrame_Timestamp)
            thread_LastFrame_Timestamp = self.LastFrame_TimeStamp

            # resize the frame, convert it to grayscale, and blur it
            # frame = imutils.resize(frame, width=500)
            gray = cv2.cvtColor(capturedFrame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # if the first frame is None, initialize it
            if prevGray is None:
                prevGray = gray
                continue
            # compute the absolute difference between the current frame and
            # first frame
            frameDiff = cv2.absdiff(prevGray, gray)
            thresh = cv2.threshold(frameDiff, 64, 255, cv2.THRESH_BINARY)[1]

            # dilate the thresholded image to fill in holes, then find contours
            # on thresholded image
            thresh = cv2.dilate(thresh, None, iterations=2)  # wasn't in Java project
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if imutils.is_cv2() else cnts[1]

            # ???
            if len(cnts) > 0:
                prevGray = gray
                FrameNumber += 1
                self.out.write(processedFrame)

        self.Release_VideoFileInput()

        self.motion_detection_Time = (1.0 / self.FRAME_RATE) * FrameNumber

        self.VkTalker.Send(user_id, 'Лайв-трансляция завершена, выполняю загрузку отчета на сервер')

        self.VkTalker.Send_Video_File('', self.Video_FilePath, self.Video_Record_StartTime, self.Video_Record_FinishTime,
            self.motion_detection_Time, user_id, self.photos_directory, self.startTime, self.ArduinoParameters_statistics, self.MemoryUsage_statistics)

        self.activities.remove('Motion Detection')

    def encode(self, frame):
        try:
            packet = self.video_stream.encode(frame)
        except Exception:
            return False
        if packet is not None:
            try:
                self.output.mux(packet)
                return True
                # self.output.mux(self.audio_stream.encode(None))
            except Exception as e:
                print(e)
                return False
                # print('mux failed: ' + str(packet))
        return False  # not needed?

    # https://github.com/opencv/opencv/issues/9981
    # https://ffmpeg.org/ffmpeg-protocols.html#rtmp
    # https://github.com/mikeboers/PyAV/issues/302
    # https://github.com/mikeboers/PyAV/blob/master/examples/encode_frames.py
    # https://ffmpeg.org/doxygen/trunk/libavcodec_2options__table_8h_source.html#l00036

    # recommended settings: https://vk.com/page-135678176_54378816

    def RTMP_Job(self):
        self.activities.append('RTMP')

        # device as input
        '''container = av.open('/dev/dsp', format='aac')
        audio_stream = None
        for i, stream in enumerate(container.streams):
            if stream.type == b'audio':
                audio_stream = stream
                break
        if not audio_stream:
            exit()'''

        self.GOP_LENGTH_IN_FRAMES = 1 * self.FRAME_RATE  # 2 * self.FRAME_RATE # 60

        self.url = 'rtmp://stream.vkuserlive.com:443/live?srv=620011&s=aWQ9Z3BfcVRRMVprM0Umc2lnbj1peW9xM0xVOWFSd2F2djFmSWU3cGJnPT0='
        self.key = 'gp_qTQ1Zk3E'

        url_key = self.url + '/' + self.key

        key_str = 'keyint=' + str(self.GOP_LENGTH_IN_FRAMES) + ':min-keyint=' + str(
            self.GOP_LENGTH_IN_FRAMES)  # 'keyint=60:min-keyint=60'
        gop_size_str = str(self.GOP_LENGTH_IN_FRAMES)

        opts = {
            'x264-params': key_str,  # 'keyint=60:min-keyint=60' #'keyint=60:min-keyint=60:no-scenecut',
            'tune': 'zerolatency',
            'preset': 'veryfast',  # 'fast'
            'g': gop_size_str  # '60'
            # 'crf':'28'  # Constant Rate Factor (see: https://trac.ffmpeg.org/wiki/Encode/H.264)
        }

        # использование options: https://github.com/mikeboers/PyAV/issues/312

        while (self.Capture_Works()):
            try:
                self.output = av.open(url_key, mode='w', format='flv', options={})

                self.video_stream = self.output.add_stream('libx264', self.FRAME_RATE)  # archive.add_stream('mpeg4')

                # self.video_stream.options = opts
                self.video_stream.pix_fmt = 'yuv420p'
                self.video_stream.width = self.frameSize[0]
                self.video_stream.height = self.frameSize[1]
                self.video_stream.codec_context.options = opts  # {'x264_build': '150'}
                # self.video_stream.gop_size = 60
                # self.video_stream.bit_rate = 2000000  # 2000 kb/s, reasonable "sane" area for 720

                # self.audio_stream = self.output.add_stream(codec_name='aac', rate=44100) # 1 / iastream.rate # 'aac'

                thread_LastFrame_Timestamp = -1
                self.Wait_for_CapturerStart()

                self.time_base = 1.0 / self.FRAME_RATE * 1000000.0

                while (self.Capture_Works()):
                    capturedFrame, processedFrame = self.Wait_ForFrame(thread_LastFrame_Timestamp)
                    thread_LastFrame_Timestamp = self.LastFrame_TimeStamp

                    frame = av.VideoFrame.from_ndarray(processedFrame, format='bgr24')
                    result = self.encode(frame)
                    if (result == False):
                        break  # may be not so rude?

                self.output.close() # if internet has been lost will lead to "[Errno 1] Operation not permitted: 'rtmp://stream.vkuserlive.com:443/live?srv=620011&s=aWQ9Z3BfcVRRMVprM0Umc2lnbj1peW9xM0xVOWFSd2F2djFmSWU3cGJnPT0=/gp_qTQ1Zk3E' (16: )"
            except Exception as e:
                self.output = None # may be wrong -> let's set gc on fire
                print('Try to reconnect')  # last 3 lines break through error "connection reset by peer" (looks like it can also happen when I try to broadcast from 2 computers in the same time)

        self.activities.remove('RTMP')

    def Monitor_Memory_Job(self):
        if (self.Monitor_Memory == True):
            self.activities.append('Monitor Memory')

            text_file = open(self.MemoryUsage_file, 'a')

            process = psutil.Process(os.getpid())
            colTime = 0

            self.Wait_for_CapturerStart()

            while (self.Capture_Works()):
                rss = process.memory_info().rss / 1024.0 / 1024.0
                curTime = time.time() - self.startTime
                memInfo = MemoryInfo(curTime,rss)
                self.MemoryUsage_statistics.append(memInfo)
                self.MemoryUsage_lastData = memInfo

                mes = ("%.2f" % curTime) + "\t" + ("%.2f" % rss)
                text_file.write(mes + "\n")
                # print(mes)

                if (curTime - colTime > 60):
                    colTime = curTime
                    gc.collect()
                    # print('Run collection')
                sleep(self.MemoryUsageInfo_RefreshTime)

            text_file.close()

            self.activities.remove('Monitor Memory')

    def Vk_Send_Photo(self, user_id):
        self.activities.append('Capture photo')

        try:
            self.Init_Camera()

            ret = False

            while (self.capturer.isOpened() and ret == False):
                ret, frame, framePr = self.GetImage()
                # for some reason it grabs frames faster or slower, than self.FRAME_RATE
                # looks like it's okay
                if ret == True:
                    cv2.imwrite(self.Photo_FilePath, framePr)
                    self.VkTalker.Send_Photo('', self.Photo_FilePath, user_id)
                    # save

                #else:
                #    break
        finally:
            self.Release_Camera()  # ???

        self.activities.remove('Capture photo')

    ################ Parallel Threads ################

    def Wait_for_Threads_Close(self):
        while (len(self.JobThreads) > 0):
            for thread in self.JobThreads:
                if not thread.isAlive():
                    if (
                            thread.name == 'Capture' and self.Capture_Works() == True):  # check for crash in thread 'Capture'
                        self.activities.remove('Capture')

                    self.JobThreads.remove(thread)
            sleep(0.05)
        print('Threads left: ' + str(self.JobThreads))

    def AnyActiveThread(self, threadPool):
        return (len(threadPool) > 0)

    def Run_Capture(self, user_id):
        # self.activities.append('Run_Capture')
        print("~ Motion Caption starts ~")
        self.PrepareForWork()  # only after that signal others that we have started

        Threads.New_Thread(self.Capture_Job, 'Capture', self.JobThreads)
        Threads.New_Thread(self.VideoWrite_Job, (user_id,), 'Video Write', self.JobThreads)
        Threads.New_Thread(self.Monitor_Memory_Job, 'Monitor Memory', self.JobThreads)

        self.Wait_for_Threads_Close()

        self.CleanUpAll()
        print("~ Motion Caption finished ~")
        # self.activities.remove('Run_Capture')

    def Run_MotionDetection(self, user_id):
        # self.activities.append('MotionDetection')
        print("~ Motion Detection starts ~")
        self.PrepareForWork()  # only after that signal others that we have started

        Threads.New_Thread(self.Capture_Job, 'Capture', self.JobThreads)
        Threads.New_Thread(self.MotionDetection_Job, (user_id,), 'Motion Detection', self.JobThreads)
        Threads.New_Thread(self.Monitor_Memory_Job, 'Monitor Memory', self.JobThreads)

        self.Wait_for_Threads_Close()

        self.CleanUpAll()
        print("~ Motion Detection finished ~")
        # self.activities.remove('MotionDetection')

    def Run_RTMP(self):
        # self.activities.append('Run_Capture')
        print("~ RTMP starts ~")
        self.PrepareForWork()  # only after that signal others that we have started

        Threads.New_Thread(self.Capture_Job, 'Capture', self.JobThreads)
        Threads.New_Thread(self.RTMP_Job, 'RTMP', self.JobThreads)
        Threads.New_Thread(self.Monitor_Memory_Job, 'Monitor Memory', self.JobThreads)

        self.Wait_for_Threads_Close()

        self.CleanUpAll()
        print("~ RTMP finished ~")
        # self.activities.remove('Run_Capture')

    def Run_RTMP_and_VideoWithMotion(self, user_id):
        # self.activities.append('Run_Capture')
        print("~ RTMP starts ~")
        self.PrepareForWork()  # only after that signal others that we have started

        self.VkTalker.Send(user_id, 'Начинаю лайв-трансляцию')

        Threads.New_Thread(self.Capture_Job, 'Capture', self.JobThreads)
        Threads.New_Thread_args(self.MotionDetection_Job, (user_id,), 'Motion Detection', self.JobThreads)
        Threads.New_Thread(self.RTMP_Job, 'RTMP', self.JobThreads)
        Threads.New_Thread(self.Monitor_Memory_Job, 'Monitor Memory', self.JobThreads)

        self.Wait_for_Threads_Close()

        self.CleanUpAll()
        print("~ RTMP finished ~")
        # self.activities.remove('Run_Capture')

    def StopActivity(self):
        self.StopActivityRequest = True
        # self.Wait_for_noActivity()

    ################ Top Threads ################

    def Run_Capture_Thread(self, user_id):
        if (self.Any_Activity() == False):
            Threads.New_Thread_args(self.Run_Capture, (user_id,), 'Capture Main', self.MainThreads)

    def Run_MotionDetection_Thread(self, user_id):
        if (self.Any_Activity() == False):
            Threads.New_Thread_args(self.Run_MotionDetection, (user_id,), 'Motion Detection Main', self.MainThreads)

    def Run_RTMP_Thread(self):
        if (self.Any_Activity() == False):
            Threads.New_Thread(self.Run_RTMP, 'RTMP Main', self.MainThreads)

    def Run_RTMP_and_VideoWithMotion_Thread(self, user_id):
        if (self.Any_Activity() == False):
            Threads.New_Thread_args(self.Run_RTMP_and_VideoWithMotion, (user_id,), 'RTMP and Video with Motion Main', self.MainThreads)

    def Vk_Send_Photo_Thread(self, user_id):
        if (self.Any_Activity() == False):
            Threads.New_Thread_args(self.Vk_Send_Photo, (user_id,), 'Vk Send Photo', self.MainThreads)

    #def StopActivity_Thread(self):
    #    Threads.New_Thread(self.StopActivity, 'Stop Activity', self.MainThreads)




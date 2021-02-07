import serial # pyserial

from com.chickens.lib.ArduinoTalk import ArduinoTalk
from com.chickens.lib.VkTalk import *
from com.chickens.lib.webcamera import *
from com.chickens.lib.Config import Config

class Tasker(object):

    def __init__(self, Top_Exit, main_py_path):
        FRAME_RATE = 10
        SECONDS_TO_RUN_FOR = 10
        output_Photo_Filename = 'output.jpg'  # 'output.mp4'
        output_Video_Filename = 'output.avi'  # 'output.mp4'

        self.Actions_to_Do = []
        self.ActionThreads = []

        self.ArduinoParameters_RefreshTime = 1
        self.MemoryUsageInfo_RefreshTime = 5

        self.config = Config(main_py_path)

        self.ArduinoTalker = ArduinoTalk(self.ArduinoParameters_RefreshTime)

        self.VkTalker = VkTalk(self.Add_Action)

        self.webCamera = WebCamera(FRAME_RATE, SECONDS_TO_RUN_FOR, main_py_path, output_Photo_Filename,
                              output_Video_Filename, self.ArduinoTalker, self.VkTalker, self.MemoryUsageInfo_RefreshTime)

        self.Top_Exit = Top_Exit

    def Listen_Vk_Requests(self):
        self.VkTalker.Listen_Messages_Thread()

    def Process_Actions(self):
        while (True):
            if (len(self.Actions_to_Do) > 0):
                command = self.Actions_to_Do[0]
                self.Actions_to_Do.remove(command)

                command_parts = command.split(self.VkTalker.user_id_delimeter)

                user_id = self.VkTalker.AdminID
                if len(command_parts) > 1:
                    user_id = int(float(command_parts[1]))
                command = command_parts[0]

                if command == 'вебка':
                    self.webCamera.Run_Capture_Thread(user_id)
                #elif command == 'Run RTMP':
                #    self.webCamera.Run_RTMP_Thread(user_id)
                #elif command == 'Run motion detection':
                #    self.webCamera.Run_MotionDetection_Thread(user_id)
                elif command == 'фото':
                    self.webCamera.Vk_Send_Photo_Thread(user_id)
                elif command == 'стоп лайв':
                    self.webCamera.StopActivity()
                elif command == 'стоп!':  # sudden interrupt
                    self.Top_Exit()
                elif command == 'стоп':
                    self.webCamera.StopActivity()
                    self.webCamera.Wait_for_noActivity()
                    self.Top_Exit()
                elif command == 'лайв':
                    self.webCamera.Run_RTMP_and_VideoWithMotion_Thread(user_id)
                elif 'кадры=' in command:
                    s_number = command.split('=')[1]
                    try:
                        new_fps = int(float(s_number))
                        self.webCamera.FRAME_RATE = new_fps
                        self.config.Set_fps(new_fps)
                        print('Частота кадров установлена на: ' + str(self.webCamera.FRAME_RATE))
                    except ValueError:
                        print('Значение частоты кадров не верное (должно быть 1 - 30)')
                        pass
                    finally:
                        pass
                elif 'статус' in command:
                    status = self.ArduinoTalker.Get_Status()
                    self.VkTalker.Send(user_id, status)
                else:
                    self.VkTalker.Send(user_id, 'Не понятно')
                    pass

            sleep(0.2)

    def Add_Action(self, action):
        self.Actions_to_Do.append(action)

    def Listen_Arduino(self):
        Threads.New_Thread(self.ArduinoTalker.Ask_Arduino_HowAreYou, 'Ask Arduino HowAreYou', self.ActionThreads)
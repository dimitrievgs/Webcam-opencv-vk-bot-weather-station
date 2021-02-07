import os
import platform
from time import sleep

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from com.chickens.lib.Threads import Threads
from com.chickens.lib.TimeStuff import *

import matplotlib
matplotlib.use('Agg') # you can get around this by using a backend that doesn't display to the user, e.g. 'Agg': (https://stackoverflow.com/questions/15713279/calling-pylab-savefig-without-display-in-ipython)
import matplotlib.pyplot as plt

import numpy as np


#vk_session = vk_api.VkApi('dimitriev.gs@mail.ru', 'mypassword')
#vk_session.auth()

#vk = vk_session.get_api()

#print(vk.wall.post(message='Hello world!'))

# https://vk-api.readthedocs.io/en/latest/

class VkTalk(object):

    def __init__(self, Add_Action):
        api_version = '5.74' # '5.80'

        user_token = 'cd5639c8a6296f2204a7f5ed5bbf486a33943dab936858554c52441c3965b2cd0447e48b290b844f26eb1'
        # 20990bd58647f1da41853d80eff4215fb6b9b23db6af97ccac795a3852723fb9a2f29a138360b0f58db23
        self.vk_User_session = vk_api.VkApi(token=user_token, api_version=api_version)
        self.api_User = self.vk_User_session.get_api()

        group_token = 'cdfe7b44025ae9f2eb08a3fa225e43f96deb8ef961a0b3f1177be986b12a83c3a40de161b3d169bab25a9'
        self.vk_Group_session = vk_api.VkApi(token=group_token, api_version=api_version)
        self.api_Gr = self.vk_Group_session.get_api()

        self.upload_Gr = vk_api.VkUpload(self.vk_Group_session)

        self.upload_User = vk_api.VkUpload(self.vk_User_session)

        self.AdminID = 333992

        self.GroupID = 168068964

        self.Good_Users_IDs = [333992]

        self.MainThreads = []

        self.Add_Action = Add_Action

        self.user_id_delimeter = '@@@'

        # Turn interactive plotting off (https://stackoverflow.com/questions/15713279/calling-pylab-savefig-without-display-in-ipython)
        # may be matplotlib.use('Agg') is already enough?
        plt.ioff()

        # self.Actions_to_Do = Actions_to_Do

        #    session = vk.Session(
        #    access_token='cdfe7b44025ae9f2eb08a3fa225e43f96deb8ef961a0b3f1177be986b12a83c3a40de161b3d169bab25a9')
        #api = vk.API(session)

    # удаляет все старые Live-трансляции, которые были сохранены, кроме той, которая активна
    def DeleteOldLiveVideos(self):
        try:
            response = self.api_User.video.get(owner_id=-self.GroupID, count=20)

            Videos = response['items']
            for i in range(len(Videos)):
                V = Videos[i]
                Title = V['title']
                isLive = 'live' in V
                #if (isLive == True):
                #    print('gotcha!')
                #    pass
                VideoID = V['id']
                if ('Live' in Title and isLive == False):
                    self.api_User.video.delete(owner_id=-self.GroupID, video_id = VideoID)
        except Exception as e:
            print(e)

    def Send(self, user_id, text):
        #self.api.wall.post(message="Hello, world")

        self.api_Gr.messages.send(
            user_id=user_id,
            message=text
        )

    def Send_Photo(self, text, image_path, user_id):
        attachments = []

        # photo = self.upload.photo(image_path, album_id=2, group_id=self.GroupID)
        # photo = self.upload.photo('/root/3301.jpg', album_id=200851098, group_id=74030368)

        image_paths = []
        image_paths.append(image_path)

        photo = self.upload_Gr.photo_messages(photos=image_paths)[0]

        attachments.append(
           'photo{}_{}'.format(photo['owner_id'], photo['id'])
        )

        #vk_photo_url = 'https://vk.com/photo{}_{}'.format(
        #    photo['owner_id'], photo['id']
        #)
        # doesn't work with upload_User - doesn't attach just text, reference gives 'access denied'

        self.api_Gr.messages.send(
            user_id=user_id, # self.AdminID
            attachment=','.join(attachments),
            message=text
        )

    def Send_Video_File(self, text, Video_FilePath, Video_Record_StartTime, Video_Record_FinishTime, motion_detection_Time, user_id, photos_directory, startTime,
                _ArduinoParameters_statistics, _MemoryUsage_statistics):
        result = False
        while(result == False):
            try:
                attachments = []

                # video_paths = []
                # video_paths.append(Video_FilePath)

                nameTimeFormat = '%d.%m.%Y'  # "dd.MM.yyyy"
                descTimeFormat = '%H:%M'  # "HH:mm"

                VideoName = "Отчет за " + TimeStuff.ToStr(Video_Record_StartTime, nameTimeFormat)
                VideoDescription = TimeStuff.ToStr(Video_Record_StartTime, descTimeFormat) + ' - ' + TimeStuff.ToStr(
                    Video_Record_FinishTime, descTimeFormat)

                file_Size_mb = os.path.getsize(Video_FilePath) / 1024.0 / 1024.0
                file_Ext = os.path.splitext(Video_FilePath)[1]

                start_Upload_Time_ms = time.time()
                video = self.upload_User.video(video_file=Video_FilePath, name=VideoName, description=VideoDescription, group_id=self.GroupID)
                UploadTime = (time.time() - start_Upload_Time_ms)
                print('video uploaded to vk')

                if 'error' in video:
                    s = 'Видео файл не корректен, отменяю загрузку видеоотчета'
                    self.Send(user_id, s)
                    print(s)
                    break

                videoID = video['video_id']
                attachments.append(
                   'video{}_{}'.format(video['owner_id'], video['video_id'])
                )

                vk_video_url = 'https://vk.com/video{}_{}'.format(
                    video['owner_id'], video['video_id']
                )
                # doesn't work with upload_User - doesn't attach just text, reference gives 'access denied'


                Plot_files = self.Make_Statistics_Pictures(photos_directory, startTime, _ArduinoParameters_statistics, _MemoryUsage_statistics)
                photos = self.upload_User.photo_wall(Plot_files, user_id=None, group_id=self.GroupID)
                for i in range(len(Plot_files)):
                    photo = photos[i]
                    attachments.append(
                        'photo{}_{}'.format(photo['owner_id'], photo['id'])
                    )
                print('plot files uploaded to vk')

                # Processing...
                start_Processing_Time_ms = time.time()
                ProcessingTime = 0
                isProcessing = True
                while (isProcessing == True):
                    Video_Info = self.Get_Video_Info(videoID)
                    has_Processing_key = 'processing' in Video_Info
                    isProcessing = has_Processing_key and (Video_Info['processing'] == 1)
                    # print('Processing...' + str(isProcessing))
                    if (isProcessing == False):
                        ProcessingTime = time.time() - start_Processing_Time_ms
                    else:
                       sleep(0.5) # since java - if too fast - get error

                print('video processed at vk')

                # vk.wall().post(adminActor).ownerId(-GROUP_ID).message(Wall_VideoComment).attachments(Attachments).execute();

                # make Wall post message text

                platform_info = platform.platform()
                position = platform_info.find('with') + 5
                os_name = platform_info # platform_info[(position):]

                os_arch = platform.uname().processor

                uploadSpeed = file_Size_mb * 8 / UploadTime  # mbit / s
                procTime_per_mb = ProcessingTime / file_Size_mb
                Time_withMotion_Part = motion_detection_Time / (Video_Record_FinishTime - Video_Record_StartTime) * 100.0

                s_fileSize = '%.1f' % file_Size_mb
                s_UploadTime = '%.1f' % UploadTime
                s_uploadSpeed = '%.1f' % uploadSpeed
                s_ProcTime = '%.1f' % ProcessingTime
                s_procTime_per_mb = '%.1f' % procTime_per_mb
                s_TimeWithMotion = '%.1f' % motion_detection_Time
                s_Time_withMotion_Part = '%.1f' % Time_withMotion_Part

                Wall_VideoComment = VideoName + ' (' + VideoDescription + ')' + '\n'
                Wall_VideoComment += '~~ Файл: размер = ' + s_fileSize + ' мб, расш = ' + file_Ext + ' ~~' + '\n'
                Wall_VideoComment += "~~ Загрузка: время = " + s_UploadTime + " с, скорость = " + s_uploadSpeed + " мбит/с ~~" + "\n"
                Wall_VideoComment += "~~ Обработка: время = " + s_ProcTime + " с, время/размер = " + s_procTime_per_mb + " с/мб ~~" + "\n"
                Wall_VideoComment += "~~ Эффективность: время с движением = " + s_TimeWithMotion + " с, доля = " + s_Time_withMotion_Part + " % ~~" + "\n"
                Wall_VideoComment += '~~ Система: ' + os_name + ', ' + os_arch  + " ~~"

                # post to wall
                self.api_User.wall.post(owner_id=-self.GroupID, attachments = ','.join(attachments), message=Wall_VideoComment)

                wall_response = self.api_User.wall.get(owner_id=-self.GroupID, count = 1)
                wallPostFull = wall_response['items'][0]
                RepostAttachments = 'wall' + '-' + str(self.GroupID) + '_' + str(wallPostFull['id'])

                self.api_Gr.messages.send(
                    user_id=user_id,
                    attachment=RepostAttachments,
                    message=''
                )

                result = True

            except Exception as e:
                s = 'Произошла ошибка во время загрузки видеоотчета: ' + str(e) + ', пытаюсь заново'
                self.Send(user_id, s)
                print(s)

        # will not work until processing...

    def Get_Video_Info(self, video_id):
        response = self.api_User.video.get(owner_id=-self.GroupID, videos='-' + str(self.GroupID) + '_' + str(video_id), count=1)
        return response['items'][0]

    # https://matplotlib.org/examples/pylab_examples/simple_plot.html
    def Make_Statistics_Pictures(self, photos_directory, startTime, _ArduinoParameters_statistics, _MemoryUsage_statistics):
        Plot_files = []

        PointsN = len(_ArduinoParameters_statistics)

        _time_statistics = []
        InTemperatures = []
        InHumidity = []
        OutTemperatures = []
        OutHumidity = []
        Vcc_Voltages = []
        Light_luxes = []
        DcDc_Temperatures = []

        for i in range(PointsN):
            ap = _ArduinoParameters_statistics[i]

            _time_statistics.append(ap.Time - startTime)
            InTemperatures.append(ap.Win_temperature)
            InHumidity.append(ap.Win_humidity)
            OutTemperatures.append(ap.Wout_temperature)
            OutHumidity.append(ap.Wout_humidity)
            Vcc_Voltages.append(ap.Vcc)
            Light_luxes.append(ap.Light)
            DcDc_Temperatures.append(ap.DcDc_temperature)

        time_np = np.asarray(_time_statistics)
        InTemperatures_np = np.asarray(InTemperatures)
        InHumidity_np = np.asarray(InHumidity)
        OutTemperatures_np = np.asarray(OutTemperatures)
        OutHumidity_np = np.asarray(OutHumidity)
        Vcc_Voltages_np = np.asarray(Vcc_Voltages)
        Light_luxes_np = np.asarray(Light_luxes)
        DcDc_Temperatures_np = np.asarray(DcDc_Temperatures)

        fig = plt.figure()
        plt.plot(time_np, OutTemperatures_np, 'r-')
        plt.plot(time_np, InTemperatures_np, 'b-')
        plt.xlabel('Время, с')
        plt.ylabel('Температура, \u00b0C')
        plt.legend(['Температура в курятнике', 'Температура в устройстве'])
        plt.title('Температура в курятнике и устройстве')
        temp_file = photos_directory + "temp.png"
        plt.savefig(temp_file)
        Plot_files.append(temp_file)
        plt.close(fig)

        fig = plt.figure()
        plt.plot(time_np, OutHumidity_np, 'r-')
        plt.plot(time_np, InHumidity_np, 'b-')
        plt.xlabel('Время, с')
        plt.ylabel('Влажность, %')
        plt.legend(['Влажность в курятнике', 'Влажность в устройстве'])
        plt.title('Влажность в курятнике и устройстве')
        temp_file = photos_directory + "humi.png"
        plt.savefig(temp_file)
        Plot_files.append(temp_file)
        plt.close(fig)

        fig = plt.figure()
        plt.plot(time_np, Light_luxes_np, 'g-')
        plt.xlabel('Время, с')
        plt.ylabel('Освещенность, люкс')
        plt.legend(['Освещенность'])
        plt.title('Освещенность в курятнике')
        temp_file = photos_directory + "light.png"
        plt.savefig(temp_file)
        Plot_files.append(temp_file)
        plt.close(fig)

        fig = plt.figure()
        plt.plot(time_np, Vcc_Voltages_np, 'g-')
        plt.xlabel('Время, с')
        plt.ylabel('Vcc напряжение, В')
        plt.legend(['Vcc напряжение'])
        plt.title('Vcc напряжение в устройстве')
        temp_file = photos_directory + "vcc.png"
        plt.savefig(temp_file)
        Plot_files.append(temp_file)
        plt.close(fig)

        fig = plt.figure()
        plt.plot(time_np, DcDc_Temperatures_np, 'g-')
        plt.xlabel('Время, с')
        plt.ylabel('Dc-dc температура, \u00b0C')
        plt.legend(['Dc-dc Temperature'])
        plt.title('Температура радиатора dc-dc преобразователя')
        temp_file = photos_directory + "dcdc_temp.png"
        plt.savefig(temp_file)
        Plot_files.append(temp_file)
        plt.close(fig)

        if len(_MemoryUsage_statistics) > 0:
            _mem_time_statistics = []
            _mem_usage_statistics = []
            Mem_PointsN = len(_MemoryUsage_statistics)
            for j in range(Mem_PointsN):
                mp = _MemoryUsage_statistics[j]
                _mem_time_statistics.append(mp.Time) #  - startTime  # already has done it
                _mem_usage_statistics.append(mp.MemoryUsage)
            mem_time_np = np.asarray(_mem_time_statistics)
            mem_usage_np = np.asarray(_mem_usage_statistics)

            fig = plt.figure()
            plt.plot(mem_time_np, mem_usage_np, 'g-')
            plt.xlabel('Время, с')
            plt.ylabel('Использование памяти, мб')
            plt.legend(['Использование памяти'])
            plt.title('Использование памяти процессом')
            temp_file = photos_directory + "py_memory.png"
            plt.savefig(temp_file)
            Plot_files.append(temp_file)
            plt.close(fig)

        return Plot_files

    # https://github.com/python273/vk_api/blob/master/examples/longpoll.py
    def Listen_Messages2(self):
        longpoll = VkLongPoll(self.vk_Group_session)

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                self.api_Gr.messages.markAsRead(peer_id=event.peer_id)

                print('in message : from_me ' + str(event.from_me) + ' from_user ' + str(event.from_user) + ' peer_id ' + str(event.peer_id) + ' user_id ' + str(event.user_id))

                if (event.user_id in self.Good_Users_IDs and event.from_me == False):
                    self.Add_Action(event.text + self.user_id_delimeter + str(event.user_id))

            else:
                pass

    def Listen_Messages(self):
        while(True):
            conversations = self.api_Gr.messages.getConversations(count = 30, filter = 'unread')['items']

            conv_commands = []

            for conv in conversations:
                # print(conv)
                # print()
                peer_id = conv['conversation']['peer']['id']
                mes_history = self.api_Gr.messages.getHistory(count=30, peer_id=peer_id)['items']

                # mes_history2 = self.api_Gr.messages.search(count=30, peer_id=peer_id, date = '10082018')['items']
                # print(mes_history2[0])
                # print()

                # print('messages in history:')

                for mes in mes_history:
                    # print(mes)
                    # print('')
                    read_state = mes['read_state']
                    if (int(float(read_state)) == 0):
                        from_id = mes['from_id']
                        if (from_id in self.Good_Users_IDs):
                            command = mes['body'] + self.user_id_delimeter + str(from_id)
                            conv_commands.append(command)
                            # print('vk message: ' + command)
                self.api_Gr.messages.markAsRead(peer_id=peer_id)

            for command in conv_commands:
                self.Add_Action(command)

            sleep(1) # 1 second

    def Listen_Messages_Thread(self):
        Threads.New_Thread(self.Listen_Messages, 'Listen VK Messages', self.MainThreads)
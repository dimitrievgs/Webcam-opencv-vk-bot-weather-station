import time


class TimeStuff(object):


    @staticmethod
    def ToStr(time_time, format = None):
        if (format is None):
            s = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_time))   # '%Y-%m-%d %H:%M:%S'
        else:
            s = time.strftime(format, time.localtime(time_time))
            return s

    @staticmethod
    def PrintElapsedTime(startT, finishT):
        s = time.strftime('%H:%M:%S', time.localtime(finishT - startT))
        print('Time elapsed: ' + s)
        #m, s = divmod(finishT - startT, 60)
        #h, m = divmod(m, 60)
        #time_str = "%02d:%02d:%.2f" % (h, m, s)
        #print("Time elapsed: %s" % time_str)
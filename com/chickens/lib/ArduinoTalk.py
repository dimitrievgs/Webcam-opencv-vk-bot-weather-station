import threading
import time
import serial.tools.list_ports

from pprint import pprint

from com.chickens.lib.ParametersInfo import SensorsInfo
from com.chickens.lib.Threads import Threads


class ArduinoTalk(object):
    """docstring"""

    def __init__(self, _ArduinoParameters_RefreshTime):
        """Constructor"""
        self.ArduinoParameters_RefreshTime = _ArduinoParameters_RefreshTime

        ports = list(serial.tools.list_ports.comports())

        self.Port = None
        for port in ports:
            #print(str(port))
            #pprint(port)
            #vars(port)
            #for attr in dir(port):
            #    print("port.%s = %r" % (attr, getattr(port, attr)))
            if (not port.manufacturer is None and 'Arduino' in port.manufacturer):
                self.Port = port

        if (not self.Port is None):
            self.ser = serial.Serial(self.Port.device, 9600)  # '/dev/ttyACM0', 9600
            print('Arduino port: ' + self.Port.device)
        else:
            print('No Arduino device connected')

        # sudo chmod 666 /dev/ttyACM0

        #Privileges (https://stackoverflow.com/questions/27858041/oserror-errno-13-permission-denied-dev-ttyacm0-using-pyserial-from-pyth):
        #  navigate to rules.d directory
        #cd /etc/udev/rules.d
        #create a new rule file
        #sudo touch my-newrule.rules
        # open the file
        #sudo vim my-newrule.rules
        # add the following
        #KERNEL=="ttyACM0", MODE="0666"

        # w_in:25.36 *C,998.50 hPa,40.54 %; w_in:25.08 *C,998.47 hPa,42.83 %; Vcc=4.98 V; Light: 132 lx; dc-dc temp=23.00 *C~

        # self.ParametersNumber = 5 # not very correct...
        self.sensors_parameters = []

        self.lockGrabber = threading.Lock()


    ArduinoStatus = ""

    def Ask_Arduino_HowAreYou(self):
        while (True):
            # ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
            self.ser.write(b'a')
            ard_response = self.ser.read_until(b'~').decode()
            if ('init' not in ard_response and '#' in ard_response): # it means full parameters packet from begin '#' to end '~'
                # ArduinoStatus = ard_response
                cur_time = time.time()

                sensors_status = ard_response.split('; ')
                self.sensor_Number = len(sensors_status)

                try:
                    str_sensors_parameters = []
                    for i in range(self.sensor_Number):
                        par = sensors_status[i].split('=')[1].split(',')
                        str_sensors_parameters.append(par)

                    _sensors_parameters = []
                    for i in range(self.sensor_Number):
                        str_sensor_par = str_sensors_parameters[i]
                        sensor_parameters = []
                        for j in range(len(str_sensor_par)):
                            value = float(str_sensor_par[j].split(' ')[0])
                            #print(value)
                            sensor_parameters.append(value)
                        _sensors_parameters.append(sensor_parameters)

                    _sensors_parameters.append([cur_time]) # absolute time

                    self.Write_SensorsParameters(_sensors_parameters)
                    #for i in range(self.sensor_Number):
                    #    print(sensors_parameters[i])
                except IndexError:
                    print(sensors_status)

            time.sleep(self.ArduinoParameters_RefreshTime) # refresh info every N s - faster not necessary

    def sensors_parameters_Manipulation(self, _sensors_parameters, to_add):  # already check with ret that it is not None
        self.lockGrabber.acquire()
        result = None
        if (to_add == True):  # write frame
            if not (_sensors_parameters is None):
                self.sensors_parameters = _sensors_parameters
        else:  # read frame
            if not (self.sensors_parameters is None):
                _sensors_parameters = self.sensors_parameters
                result = _sensors_parameters
        self.lockGrabber.release()
        return result

    def Write_SensorsParameters(self, _sensors_parameters):
        self.sensors_parameters_Manipulation(_sensors_parameters, True)

    def Get_SensorsParameters(self):
        return self.sensors_parameters_Manipulation(None, False)

    def Get_Status(self):
        Arduino_parameters = self.Get_SensorsParameters()

        SI = SensorsInfo(Arduino_parameters)

        if (SI.OK == True):
            status = ''

            status += 'Курятник: температура = ' + ('%.1f' % SI.Wout_temperature) + ' \u00b0C, '
            status += 'влажность = ' + ('%.1f' % SI.Wout_humidity) + ' %, '
            status += 'устройство: температура = ' + ('%.1f' % SI.Win_temperature) + ' \u00b0C, '
            status += 'влажность = ' + ('%.1f' % SI.Win_humidity) + ' %, '

            status += 'Vcc = ' + ('%.2f' % SI.Vcc) + ' В, '
            status += 'освещенность = ' + ('%.0f' % SI.Light) + ' люкс, '
            status += 'температура радиатора dc-dc преобразователя = ' + ('%.1f' % SI.DcDc_temperature) + ' \u00b0C. '

            return status
        else:
            return 'Общение с arduino ещё не инициализировано'
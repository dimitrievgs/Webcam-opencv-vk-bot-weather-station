class SensorsInfo(object):

    def __init__(self, sensors_parameters):
        self.OK = False

        if (len(sensors_parameters) > 4): # not very correct...

            self.Win_temperature = sensors_parameters[0][0]
            self.Win_pressure = sensors_parameters[0][1]
            self.Win_humidity = sensors_parameters[0][2]

            self.Wout_temperature = sensors_parameters[1][0]
            self.Wout_pressure = sensors_parameters[1][1]
            self.Wout_humidity = sensors_parameters[1][2]

            self.Vcc = sensors_parameters[2][0]

            self.Light = sensors_parameters[3][0]

            self.DcDc_temperature = sensors_parameters[4][0]

            self.Time = sensors_parameters[6][0]

            self.OK = True
        else:
            self.OK = False

class MemoryInfo(object):

    def __init__(self, _Time, _MemoryUsage):
        self.MemoryUsage = _MemoryUsage
        self.Time = _Time
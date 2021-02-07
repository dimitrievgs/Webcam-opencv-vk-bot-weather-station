import configparser
import os


class Config(object):

    def __init__(self, main_py_path):
        self.settings_path = main_py_path + '/settings/settings.ini'

        if not os.path.exists(self.settings_path):
            with open(self.settings_path, 'w'): pass

        self.settings = configparser.ConfigParser()
        # settings._interpolation = configparser.ExtendedInterpolation()
        self.settings.read('settings.ini')

        # create absent sections

        sections = self.settings.sections()
        needed_sections = ['base', 'vk', 'webcamera']
        for i in range(len(needed_sections)):
            sec = needed_sections[i]
            if (not sec in sections):
                self.settings.add_section(sec)

        self.Create_or_Read_Option('vk', 'user_token', 'cd5639c8a6296f2204a7f5ed5bbf486a33943dab936858554c52441c3965b2cd0447e48b290b844f26eb1')
        self.Create_or_Read_Option('vk', 'group_token', 'cdfe7b44025ae9f2eb08a3fa225e43f96deb8ef961a0b3f1177be986b12a83c3a40de161b3d169bab25a9')
        self.Create_or_Read_Option('vk', 'admin_id', '333992')
        self.Create_or_Read_Option('vk', 'group_id', '168068964')
        self.Create_or_Read_Option('vk', 'good_users_ids', '[333992]')

        self.Create_or_Read_Option('webcamera', 'fps', '10')

        self.Save()

    def Create_or_Read_Option(self, section, option, value = None):
        if (self.settings.has_option(section, option) == False):
            self.settings.set(section, option, value)
        else:
            self.settings.get(section, option)

    def Save(self):
        with open(self.settings_path, "w") as config:
            self.settings.write(config)

    def Set_fps(self, value):
        self.settings.set('webcamera', 'fps', str(value))
        self.Save()
import sys

from com.chickens.lib import *
from com.chickens.lib.Tasker import Tasker
from com.chickens.lib.webcamera import *
import os

# https://ru.stackoverflow.com/questions/460207/%D0%95%D1%81%D1%82%D1%8C-%D0%BB%D0%B8-%D0%B2-python-%D0%BE%D0%BF%D0%B5%D1%80%D0%B0%D1%82%D0%BE%D1%80-switch-case
# switch http://tony.su/2011/11/14/switchcase-ifelifelse/

def Top_Exit():
    sys.exit()

main_py_path = os.path.dirname(os.path.abspath(__file__))

tasker = Tasker(Top_Exit, main_py_path)

def Listen_Print():
    x = "a"
    while (x!='стоп' and x!='стоп!'):
        x = str(input('command: \n'))
        tasker.Add_Action(x)

tasker.Listen_Arduino()
tasker.Listen_Vk_Requests()
Threads.New_Thread(Listen_Print, 'Listen Print', tasker.ActionThreads)

tasker.Process_Actions()


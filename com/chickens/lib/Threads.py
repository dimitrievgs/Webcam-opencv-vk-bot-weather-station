from threading import Thread


class Threads(object):

    def __init__(self):
        pass

    def New_Thread(Job, Thread_name, threadPool):
        t1 = Thread(target=Job, args=())
        t1.name = Thread_name
        t1.daemon = True #False
        threadPool.append(t1)
        t1.start()
        return t1

    def New_Thread_args(Job, args, Thread_name, threadPool):
        t1 = Thread(target=Job, args=args)
        t1.name = Thread_name
        t1.daemon = True #False
        threadPool.append(t1)
        t1.start()
        return t1
# encoding: utf-8

import socket
import cPickle

class ERPError(Exception):

    def __init__(self, exception, traceback):
        self.exception = exception
        self.traceback = traceback.decode('utf-8').encode('ascii',
                                                          'xmlcharrefreplace')
        stringified = unicode(exception)
        if hasattr(stringified, 'split'):
            lines = stringified.split('\n')
            self.type = lines[0].split(' -- ')[0]
        else:
            self.type = 'error'

    def __str__(self):
        if self.type == 'error':
            return self.traceback
        else:
            return unicode(self.exception).encode('utf-8')


class OEConnection(socket.socket):

    def __init__(self, host, port, credentials):
        self.host = host
        self.port = port
        self.socket = None

    def send(self, message, exception=False, traceback=None):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(0.5)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(None)
        picked = cPickle.dumps([message, traceback])
        self.socket.sendall('%8d%s%s' % (len(picked),
                                         '1' if exception else '0', picked))

    def read(self, size):
        buf = ''
        while len(buf) < size:
            chunk = self.socket.recv(size - len(buf))
            if chunk == '':
                raise RuntimeError
            buf += chunk
        return buf

    def receive(self):
        size = int(self.read(8))
        exception = self.read(1) != '0'
        obj, err = cPickle.loads(self.read(size))

        if isinstance(obj, Exception):
            raise ERPError(obj, err)
        else:
            return obj

        self.socket.close()
        self.socket = None

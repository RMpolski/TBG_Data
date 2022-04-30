from qcodes import Instrument
import qcodes.utils.validators as vals
from qcodes.utils.helpers import strip_attrs
import serial


class vdpArduino(Instrument):
    """
    A van der Pauw switching box. It has 6 configurations (1 and 4 are the
    same, and 2 and 5 are the same)
        1: S1 I+  S2 I-  S3 V-  S4 V+
        2: S1 I+  S2 V+  S3 V-  S4 I-
        3: S1 I+  S2 V+  S3 I-  S4 V-
        4: S1 I+  S2 I-  S3 V-  S4 V+
        5: S1 I+  S2 V+  S3 V-  S4 I-
        6: S1 V+  S2 I+  S3 V-  S4 I-
    """
    def __init__(self, name, address, timeout=None, **kwargs):
        super().__init__(name, **kwargs)

        self.address = address
        self._open_serial_connection(timeout)

        self.add_parameter('config', set_cmd=self._bytes_write,
                           get_cmd=self._getcn,
                           vals=vals.Ints(1, 6))

        self._confign = None

    def _open_serial_connection(self, timeout=None):
        if timeout is None:
            ser = serial.Serial(self.address, 9600)
        else:
            ser = serial.Serial(self.address, 9600, timeout=timeout)
        print(ser.isOpen())
        if not (ser.isOpen()):
            ser.open()
        self._ser = ser
        print('Connected to ', self.address)
        # print(self.get_idn())  # for some reason get_idn() doesn't work as
        # the first command, but it works after using other commands.
        # It doesn't work even after waiting like 2 seconds

    def close(self):
        """Irreversibly stop this instrument and free its resources.
        Closes the serial connection too"""
        if hasattr(self, 'connection') and hasattr(self.connection, 'close'):
            self.connection.close()
        ser = self._ser
        ser.close()

        strip_attrs(self, whitelist=['name'])
        self.remove_instance(self)

    def _bytes_write(self, n):
        self._confign = n
        self._ser.write(str(n).encode('utf-8'))
        return

    def _getcn(self):
        if self._confign is None:
            print('Need to input a configuration first')
            return None
        else:
            return self._confign

"""Created Feb 7, 2018 by Robert Polski

Not useable at the moment"""

from qcodes import VisaInstrument
import qcodes.utils.validators as vals
import time


class Agilent_XGS600(VisaInstrument):
    """The Agilent XGS-600 pressure gauge driver"""
    def __init__(self, name: str, address: str, **kwargs):
        """name: internal name
           address: address of the port in VISA"""
        super().__init__(name, address, terminator='\r', **kwargs)
        s1 = ''
        self.add_parameter('pressure_units', get_cmd='#0013')
        self.add_parameter('pressure_s1', get_cmd='#0002'+s1)

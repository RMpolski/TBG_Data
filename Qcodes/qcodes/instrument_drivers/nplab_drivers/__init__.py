import sys
import subprocess

from qcodes.instrument_drivers.tektronix.Keithley_2000 import Keithley_2000
from qcodes.instrument_drivers.nplab_drivers.Keithley_6221 import Keithley_6221
from qcodes.instrument_drivers.nplab_drivers.Keithley_2182a import Keithley_2182a
from qcodes.instrument_drivers.nplab_drivers.Keithley_2200 import Keithley_2200
from qcodes.instrument_drivers.nplab_drivers.LR_700 import LR_700
from qcodes.instrument_drivers.nplab_drivers.SIM900 import SIM900
from qcodes.instrument_drivers.nplab_drivers.SIM900_stick import SIM900_stick
from qcodes.instrument_drivers.nplab_drivers.SIM900_rs232 import SIM900_rs232
from qcodes.instrument_drivers.nplab_drivers.OpenDacs_Seekat import Seekat
from qcodes.instrument_drivers.nplab_drivers.OpenDacs_DAC_ADC import DAC_ADC
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
## This SR865A is the standard one, with normal error handling
# from qcodes.instrument_drivers.stanford_research.SR865A import SR865A
## This SR865A contains error handling that allows a timeout error to occur
## and keeps measuring
from qcodes.instrument_drivers.nplab_drivers.SR865A import SR865A
from qcodes.instrument_drivers.nplab_drivers.vdpArduino import vdpArduino
from qcodes.instrument_drivers.nplab_drivers.NPTriton import Triton
from qcodes.instrument_drivers.nplab_drivers.SR560 import SR560
from qcodes.instrument_drivers.nplab_drivers.SRDC205 import SRDC205
from qcodes.instrument_drivers.nplab_drivers.Lakeshore211 import Lakeshore211
from qcodes.instrument_drivers.nplab_drivers.plot_tools import (get2d_dat,
                        dvdi2dfromiv, concat_2d,
                        val_to_index, mov_average,
                        iv_from_dvdi,
                        Rxxfromdata,
                        RapidTwoSlopeNorm,
                        DivLogNorm,
                        DivSymLogNorm,
                        graphene_mobilityFE,
                        graphene_mobilityB,
                        gr_Boltzmannfit)

from qcodes.instrument_drivers.nplab_drivers.time_params import (
        time_from_start,
        time_stamp,
        output_datetime,
        output_date_strings)

from qcodes.instrument_drivers.nplab_drivers.common_commands import (
        single_param_sweep,
        twod_param_sweep,
        data_log, breakat)


from qcodes.instrument_drivers.nplab_drivers.instrumentinitialize import (
        ppms_init,
        triton_init,
        stick_setup_init)

from .bipolarcolor import bipolar

if sys.platform == 'win32':
    from .QD import QD

reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
installed_packages = [r.decode() for r in reqs.split()]
if 'qtplot==0.2.5' in installed_packages:
    from .plot_tools import qt2dplot

# Commonly used simple loops and calculated parameter structure
# also breakif-function-generating function
import qcodes as qc
from math import ceil
import numpy as np
import time
from qcodes.instrument_drivers.nplab_drivers.time_params import time_from_start


def single_param_sweep(SetParam, SetArray, delay, *MeasParams,
                       DataName='', XParam=None, YParam=None,
                       plot_results=True, save_plots=True):
    """ Single parameter sweep, single measure (for more measurements, add
    parameters to the .each() part). Includes live plot.

    Returns: data (a qcodes DataSet object), plot

    Arguments:
    SetParam: The parameter to sweep (such as a voltage)
    SetArray: should be a list or numpy array of values you want to set
                SetParam to.
    delay: The delay time between when SetParam is set till the MeasParams
                are measured (0 by default).
    *MeasParam: The comma-separated parameters you want to measure at each
                setpoint
    Keyword Arguments:
    DataName: A name to tag the data (defaults to nothing)
    XParam: Optional, the x parameter to be used in plotting (if not used, will
                default to the set parameter for every plot). Must be either a
                list that is the same length as YParam, a single parameter, or
                None.
    YParam: Allows you to pick only a few parameters to plot out of those
                measured. (if not mentioned, will plot all *MeasParams)
    plot_results: True by default, if false, suppresses plotting
    save_plots: True by default. If false, doesn't save plots at the end of the
                sweep
    """

    loop = qc.Loop(SetParam[SetArray], delay=delay).each(*MeasParams)
    data = loop.get_data_set(name=DataName)
    plot = []

    def _plot_update():
        if type(plot) is list:
            for p in plot:
                p.update()
        else:
            plot.update()

    def _plot_save():
        if type(plot) is list:
            for i in range(len(plot)):
                fname = '{}_{}.png'.format(plot[i].get_default_title(), str(XParam[i])+'vs'+str(YParam[i]))
                plot[i].save(filename=fname)
        else:
            fname = '{}_{}.png'.format(plot.get_default_title(), str(XParam)+'vs'+str(*MeasParams))
            plot.save(filename=fname)

    if plot_results:
        if XParam is None:
            XParam = SetParam

        if len(MeasParams) == 1:
            plot = qc.QtPlot(getattr(data, str(XParam)+'_set'),
                             getattr(data, str(*MeasParams)),
                             window_title=str(XParam)+' vs. '+str(*MeasParams))
            loop.with_bg_task(plot.update)
        else:
            if YParam is None:
                YParam = MeasParams
            if type(XParam) is not list and type(XParam) is not tuple:
                if type(YParam) is not list and type(YParam) is not tuple:
                    XParam = [XParam]
                    YParam = [YParam]
                else:
                    XParam = [XParam]*len(MeasParams)
            elif len(XParam) != len(YParam):
                raise ValueError('length of XParam list must be the same as' +
                                 'length of YParam list')

            # Create a str for XParam so we can account for _set in the str
            XParamStr = []
            for i in range(len(XParam)):
                xpi = str(XParam[i])
                if xpi == str(SetParam):
                    XParamStr.append(xpi + '_set')
                else:
                    XParamStr.append(xpi)

            for i in range(len(YParam)):
                title = str(YParam[i]) + ' vs. ' + str(XParam[i])
                plot.append(qc.QtPlot(getattr(data, XParamStr[i]),
                            getattr(data, str(YParam[i])), window_title=title))

            loop.with_bg_task(_plot_update)
    try:
        loop.run()
        if save_plots and plot_results:
            _plot_save()
        return data, plot
    except KeyboardInterrupt:
        if plot_results:
            _plot_update()
            if save_plots:
                _plot_save()
        print('Keyboard Interrupt')
        return data, plot


def twod_param_sweep(SetParam1, SetArray1, SetParam2, SetArray2, *MeasParams,
                     SetDelay1=0, SetDelay2=0, Param2_SetBetween=None,
                     DataName='', ZParam=None,
                     plot_results=True, save_plots=True):
    """ Single parameter sweep, single measure (for more measurements, add
    parameters to the .each() part). Includes live plot. Note: if the SetParam1
    array is nonuniform, the y axis of the plot will be messed up. Try MatPlot
    instead of QtPlot in that situation.

    Returns: data (a qcodes DataSet object), plot

    Arguments:
    SetParam1: The outer parameter to sweep (such as a temperature)
    SetArray1: should be a list or numpy array of values you want to set
                SetParam1 to. This array will be run through once
    SetParam2: The inner parameter to sweep (such as a voltage)
    Param2_SetBetween: Sets parameter 2 to this value at the end of each
                sweep of the parameter (completion of one row) and before
                changing parameter 1.
    SetArray1: should be a list or numpy array of values you want to set
                SetParam2 to. This array will be run through for each value of
                SetArray1
    MeasParams: The parameter(s) you want to measure at each setpoint
    Keyword Arguments:
    SetDelay1: The delay time between when SetParam1 is set till the SetParam2
                is set to its first value (0 by default)
    SetDelay2: Delay time between when SetParam2 is set and the MeasParam
                is measured (0 by default)
    DataName: A name to tag the data (defaults to nothing)
    ZParam: Allows you to pick only a few parameters to plot out of those
                measured. (if not mentioned, will plot all *MeasParams)
    plot_results: True by default, if false, suppresses plotting
    save_plots: True by default. If false, doesn't save plots at the end of the
                sweep
    """

    if Param2_SetBetween is None:
        def between_func():
            pass
    else:
        def between_func():
            SetParam2(Param2_SetBetween)
            return

    innerloop = qc.Loop(SetParam2[SetArray2],
                        delay=SetDelay2).each(*MeasParams)
    twodloop = qc.Loop(SetParam1[SetArray1],
                       delay=SetDelay1).each(innerloop, qc.Task(between_func))
    data = twodloop.get_data_set(name=DataName)
    plot = []

    def _plot_update():
        if type(plot) is list:
            for p in plot:
                p.update()
        else:
            plot.update()

    def _plot_save():
        if type(plot) is list:
            for i in range(len(plot)):
                fname = '{}_{}.png'.format(plot[i].get_default_title(), str(ZParam[i]))
                plot[i].save(filename=fname)
        else:
            fname = '{}_{}.png'.format(plot.get_default_title(), str(*MeasParams))
            plot.save(filename=fname)

    if plot_results:
        if len(MeasParams) == 1:
            plot = qc.QtPlot(getattr(data, str(*MeasParams)), window_title=str(*MeasParams))
            twodloop.with_bg_task(plot.update)
        else:
            if ZParam is None:
                ZParam = MeasParams
            if type(ZParam) is not list and type(ZParam) is not tuple:
                ZParam = [ZParam]

            for zp in ZParam:
                plot.append(qc.QtPlot(getattr(data, str(zp)), window_title=str(zp)))

            twodloop.with_bg_task(_plot_update)

    try:
        twodloop.run()
        if save_plots and plot_results:
            _plot_save()
        return data, plot
    except KeyboardInterrupt:
        if plot_results:
            _plot_update()
            if save_plots:
                _plot_save()
        print('Keyboard Interrupt')
        return data, plot


def data_log(delay, *MeasParams, N=None, minutes=None, DataName='',
             XParam=None, YParam=None, breakif=None,
             plot_results=True, save_plots=True):
    """A loop that takes measurements every "delay" seconds (starts measuring
    at startup, and each delay comes after the measurement). Either choose to
    measure N times or for minutes. The arrays of the data are: count_set
    (the number of the data point), time0 (the time since the start),
    *MeasParams (comma-separated collection of parameters (instr.param)
    measured at each point)

    Note that the amount of minutes may be slightly larger than min because
    this assumes the time of measurement for the parameters is 0.

    Returns: data (a DataSet object), plot (a plot or a list of plots
    if MeasParams has more than one parameter)

    Arguments:
    delay: Seconds between each measurement
    *MeasParams: a comma-separated collection of parameters to measure
    Keyword Arguments:
    N: The number of data points to take (if left None, need to use minutes)
    minutes: The number of minutes to take data points (if left as None, need
                to use N). If minutes/delay is not an integer, rounds up
    DataName: the name to be placed on the file (defaults to '')
    XParam: an optional specification of the x-axis parameter to plot (defaults
            to time0 for all plots). If you want different x-axes for different
            plots, use a list. To include time0 in that list, use the string
            'time' or 'time0'. The list must be the same length as YParam or
            MeasParams
    YParam: optional specification of y-axis parameters to plot (if not
            specified, it will create one plot per MeasParam).
    breakif: specify a parameterless function that returns true when the break
            condition is met (example ppms temperature < 2.01)
    plot_results: if you want to do the data log without plots, set this to
            False
    save_plots: True by default. If false, doesn't save plots at the end of the
                sweep

    """
    if breakif is None:
        def breakif():
            pass

    count = qc.ManualParameter('count')
    time0 = time_from_start('time0')
    if N is None and minutes is None:
        return ValueError('Must have either N or minutes arguments')
    elif N is not None and minutes is not None:
        return ValueError('Only use N or minutes arguments')
    elif N is not None and minutes is None:
        loop = qc.Loop(count.sweep(1, int(N), step=1)).each(time0,
                                                            *MeasParams,
                                                            qc.Wait(delay),
                                                            qc.BreakIf(
                                                                breakif))
    elif minutes is not None and N is None:
        N = ceil(minutes*60/delay)
        loop = qc.Loop(count.sweep(1, int(N), step=1)).each(time0,
                                                            *MeasParams,
                                                            qc.Wait(delay),
                                                            qc.BreakIf(
                                                                breakif))
    data = loop.get_data_set(name=DataName)
    plot = []

    def _plot_update():
        if type(plot) is list:
            for p in plot:
                p.update()
        else:
            plot.update()

    def _plot_save():
        if type(plot) is list:
            for p in plot:
                p.save()
        else:
            plot.save()

    if plot_results:
        if XParam is None:
            XParam = time0

        if len(MeasParams) == 1:
            plot = qc.QtPlot(getattr(data, str(XParam)),
                             getattr(data, str(*MeasParams)),
                             window_title=str(XParam)+' vs. '+str(*MeasParams))
            loop.with_bg_task(plot.update)
        else:
            if YParam is None:
                YParam = MeasParams
            if type(XParam) is not list and type(XParam) is not tuple:
                if type(YParam) is not list and type(YParam) is not tuple:
                    XParam = [XParam]
                    YParam = [YParam]
                else:
                    XParam = [XParam]*len(MeasParams)
            elif len(XParam) != len(YParam):
                raise ValueError('length of XParam list must be the same as' +
                                 'length of YParam list')
            for i in range(len(XParam)):
                if type(XParam[i]) is str:
                    if XParam[i] == 'time' or XParam[i] == 'time0':
                        XParam[i] = time0

            # plot = []
            for i in range(len(YParam)):
                title = str(YParam[i]) + ' vs. ' + str(XParam[i])
                plot.append(qc.QtPlot(getattr(data, str(XParam[i])),
                            getattr(data, str(YParam[i])), window_title=title))

            # def _plot_update():
            #     for p in plot:
            #         p.update()
            #
            # def _plot_save():
            #     for p in plot:
            #         p.save()

            loop.with_bg_task(_plot_update)
    try:
        time0.reset()
        loop.run()
        if save_plots and plot_results:
            _plot_save()
        return data, plot
    except KeyboardInterrupt:
        if plot_results:
            _plot_update()
            if save_plots:
                _plot_save()
        print('Keyboard Interrupt')
        return data, plot


def breakat(parameter, setpoint, epsilon, waitafter=None, boolcond=None):
    """ Returns a function based on the measured parameter, a setpoint, and an
    epsilon value within which it must be. There is also an optional waitafter
    option where you can wait for a certain time after it reaches the break

    parameter: The qcodes instrument parameter to measure and compare to
        setpoint
    setpoint: the desired break point
    epsilon: An uncertainty bound about the setpoint (breaks when abs(parameter
        - setpoint) < epsilon)
    waitafter: time (s) to wait after hitting the breakpoint
    boolcond: can be None (automatic), 'lessthan', 'greaterthan' (for lessthan
        and greaterthan, the epsilon value doesn't matter, but I'm keeping that
        parameter in this function since that will usually be used). This
        specifies the boolean condition used for the break condition"""

    def breakfunc():
        if boolcond:
            if boolcond.lower() == 'lessthan':
                breakbool = parameter() < setpoint
            elif boolcond.lower() == 'greaterthan':
                breakbool = parameter() > setpoint
            else:
                return TypeError('boolcond must be None, lessthan, or' +
                                 ' greaterthan')
        else:
            breakbool = np.abs(parameter() - setpoint) < epsilon
        if breakbool or 'breakstart' in breakfunc.__dict__:
            if not waitafter:
                return True
            elif 'breakstart' not in breakfunc.__dict__:
                breakfunc.breakstart = time.time()
                return False
            elif time.time() - breakfunc.breakstart < waitafter:
                return False
            else:
                return True
        else:
            return False

    return breakfunc


# Calculated parameter outline. If the value provided by instr.param() needs
# to have an operation done to it before you want it displayed in the
# measurement, use a parameter defined this way. Define your own function that
# returns what you want, using OhmsfromI as an example.
# constV = 0.5
# def OhmsfromI():
#     return constV/instr.current()
#
#
# paramname = qc.Parameter('paramname', get_cmd=OhmsfromI, label='Resistance',
#                          unit='Ohms')

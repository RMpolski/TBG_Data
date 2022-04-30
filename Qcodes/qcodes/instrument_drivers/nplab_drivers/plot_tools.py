import qcodes as qc
import pandas as pd
import numpy as np
from scipy.integrate import cumtrapz
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import Normalize
import subprocess
import sys


def mov_average(array, window):
    """A simple moving average function with a window size. Calculates the
    average of the first number of points in the window, shifts by one point,
    calculates the average, and so on until the end of the array.

    array: the array from which to calculate the moving average
    window: (must be integer) the amount of points in each average
    """
    return np.convolve(array, np.ones((window,))/window, mode='valid')


def find_closest(value, array):
    """Find the closest value to what is in the array and return the
    index. In case of a tie, it chooses the first number"""
    closest = np.argmin(np.abs(array-value))
    return closest


def val_to_index(valuefindarray, array):
    """Searches in array for the values in valuefindarray. Returns a list of
    indices.
    If the value isn't in the array, uses the closest value"""
    indarray = list([])
    count = 0
    for i in valuefindarray:
        if np.isin(i, array):
            indarray.append(list(array).index(i))
        else:
            print('{:.2f} is not a value in the array'.format(i))
            indarray.append(find_closest(i, array))
            print('Plotted {:.2f} instead'.format(array[int(indarray[count])]))
        count += 1
    return indarray


def imshowplot(x, y, z, aspect=1, interpolation=None, cmap='viridis', norm=None):
    """
    I don't think this quite works yet.

    Makes a plot that is true to the data points. Pcolormesh naturally
    interpolates and sets the bounds of the figure to the max and min setpoint
    values, using n-1 pixels in each direction. This plots the pixels as they
    were measured.

    x, y: The setpoint values in x and y (1D arrays from left to right or
            bottom to top)
    z: The measured values in a 2D array
    aspect: If the two setpoint values are not similar in similar in magnitude,
            the plot will have an awkward aspect ratio. Change it with by
            setting aspect < 1 to stretch in the x direction and > 1 to stretch
            in the y direction.
    interpolation: Smooth the dataset by choosing the interpolation (available
            options can be found in plt.imshow)
    cmap: The colormap to use"""

    dx = x[1] - x[0]
    dy = y[1] - y[0]
    y = y[::-1]
    z = z[::-1]

    extent = [x[0]-dx/2, x[-1]+dx/2, y[-1]+dy/2, y[0]-dy/2]
    im = plt.imshow(z, extent=extent, aspect=aspect,
                    interpolation=interpolation,
                    cmap=cmap, norm=norm)
    return im


def iv_from_dvdi(dvdi, x, axis=1):
    """ Returns a cumulative integral array from a 2d array dvdi, integrating
    each row by default (choose axis=0 for integrating over columns) and
    somewhat artificially sets the 0 point of x to the 0 point of V

    Inputs:
    dvdi is either a 2d array or a 1d array of a derivative with respect to
            the next argument
    x: the x-axis argument used to integrate
    axis: only necessary for 2d arrays. Selects the direction in which to
    integrate.

    Returns: an integrated array, with the same shape as the input (either 2d
        or 1d), where the 0 point of the array x is set to 0"""

    if len(np.array(dvdi).shape) == 2:
        V = cumtrapz(dvdi, x=x, axis=axis, initial=0)
        return V - V[:, val_to_index([0], x)]
    elif len(np.array(dvdi).shape) == 1:
        V = cumtrapz(dvdi, x=x, initial=0)
        return V - V[val_to_index([0], x)]
    else:
        raise ValueError('Problem with the array shape. Accepts only 2d or' +
                         '1d arrays')


def get2d_dat(filename):
    """Gets 2D data from qcodes .dat file.
    Returns X, Y, Z where X and Y are the inner- and outer-loop set params,
    and Z is the measured array"""
    data = pd.read_csv(filename, sep='\t', header=None, comment='#',
                       skip_blank_lines=True)
    npdata = np.array(data)
    Y = np.unique(npdata[:, 0])
    X = npdata[:, 1][np.where(npdata[:, 0] == Y[0])]
    zl = []
    for yval in Y:
        zl.append(npdata[:, 2][np.where(npdata[:, 0] == yval)])
    Z = np.array(zl)
    return X, Y, Z


def dvdi2dfromiv(dset, Iparam, yparam, Vparam, diffset='dVdI'):
    """ V is for voltage, I for current, y is the other parameter (y in 2D).
    It's intended for an I sweep, V measure situation.

    Note: this is for
    calculating dV/dI or dI/dV when current is the swept parameter and voltage
    is measured.

    Iparam, yparam, Vparam are the parameters (instr.param) used in acquiring
    the datasets dset.

    Returns 3 arrays (I, Y, dVdI) or (I, Y, dIdV) that can be used to plot
    using plt.pcolormesh(I, Y, dVdI).

    You can change between dVdI and dIdV using keyword arg diffset
    'dIdV' or 'dVdI' (not case sensitive)
    """
    Ip = str(Iparam) + '_set'
    yp = str(yparam) + '_set'
    Vp = str(Vparam)

    curr = getattr(dset, Ip)[0]
    Y = getattr(dset, yp).ndarray
    dI = np.gradient(curr)
    dV = np.gradient(getattr(dset, Vp).ndarray, axis=1)

    if diffset.lower() == 'dvdi':
        dVdI = dV/dI
        return curr, Y, dVdI
    elif diffset.lower() == 'didv':
        dIdV = dI/dV
        return curr, Y, dIdV
    else:
        raise ValueError('diffset keyword arg must be either dVdI or dIdV' +
                         ' upper or lowercase')


def concat_2d(dsets, xparam, yparam, zparam):
    """Concatenates 2D datasets. When the x direction has been partially measured
    for the top y point and has been replaced by the second array, this
    function replaces the points with the second array and concatenates the two

    dsets must be a tuple, of length 2 or more, of qcodes datasets
    xparam, yparam, zparam, are the parameters (instrument.param) used in the
    measurement

    Returns X, Y, Z, numpy arrays that can be plotted with
    plt.pcolormesh(X, Y, Z)

    Note: xparam is for the inner loop sweep, and yparam the outer loop. Also,
    enter the dsets in the order that they were taken.
    Also, you may encounter problems when using plt.pcolormesh due to nan
    values. If you do, just use Z = np.nan_to_num(Z) to replace nans with 0.
    """

    xp = str(xparam) + '_set'
    yp = str(yparam) + '_set'
    zp = str(zparam)

    if len(dsets) < 2:
        raise ValueError('Need tuple of length >=2 for argument')

    # Check for same x shapes
    for a in dsets[1:len(dsets)]:
        if getattr(a, xp).shape[1] != getattr(dsets[0], xp).shape[1]:
                raise ValueError('Datasets must have same length in x')

    X = getattr(dsets[0], xp)[0]

    # initialize yfinalvals with first dset and work forward
    # also initialize z until first nan or end of first dset
    # First toss these in one by one and then sort at the end
    yfinalvals = []
    zfinalvals = []
    y0vals = getattr(dsets[0], yp).ndarray

    for yind in range(0, len(y0vals)):
        if np.isnan(y0vals[yind]):
            break
        else:
            yfinalvals.append(y0vals[yind])
            zfinalvals.append(getattr(dsets[0], zp)[yind])

    # Concatenate the y values
    for d in dsets[1:]:
        new_yvals = getattr(d, yp).ndarray
        for vind in range(0, len(new_yvals)):
            val = new_yvals[vind]
            if np.isnan(val):
                break
            elif val in yfinalvals:
                ind = yfinalvals.index(val)
                zfinalvals[ind] = getattr(d, zp)[vind]
            else:
                zfinalvals.append(getattr(d, zp)[vind])
                yfinalvals.append(val)

    indsort = np.array(yfinalvals).argsort()
    Y = np.array(yfinalvals)
    Y.sort()
    Z = np.array(zfinalvals)[indsort]

    return X, Y, Z

def Rxxfromdata(dset, current, instrument='lockin865', Rswitchohms=50000):
    """Use X for values less than 50000 ohms (or whatever the value of
    Rswitchohms you want) and R for anything larger.

    dset is the dataset from qc.load_data(), current is the constant
    current amplitude used (in A),
    and instrument can be lockin865 (default) or lockin830 if you want"""
    X = getattr(dset, str(instrument) + '_X')[:]/current
    Y = getattr(dset, str(instrument) + '_Y')[:]/current
    R = np.sqrt(X**2 + Y**2)

    if len(X.shape) == 1:
        for i, r in enumerate(R):
            if r > Rswitchohms:
                X[i] = r
    elif len(X.shape) == 2:
        for j in range(R.shape[0]):
            for i, r in enumerate(R[j, :]):
                if r > 5*10**4:
                    X[j, i] = r

    return X

class RapidTwoSlopeNorm(Normalize):
    def __init__(self, vcenter, P25=0.5, P75=0.5, vmin=None, vmax=None):
        """
        Normalize data with a set center.

        Useful when mapping data with an unequal rates of change around a
        conceptual center, e.g., data that range from -2 to 4, with 0 as
        the midpoint.

        Parameters
        ----------
        vcenter : float
            The data value that defines ``0.5`` in the normalization.
        P25 : float, optional
            See P75 below, but this one is for below the 0.5 point. These two
            parameters basically just add another two points to the
            interpolation at 0.25 and 0.75. Lower means more sqeezed near
            the vcenter point.
        P75 : float, optional
            Squeezes or expands the data near small values about the 0.5 point.
            The percent distance from between the 0.5 point and 1.0 point
            where the unmodified 0.75 point now sits. (make lower to squeeze).
            Defaults to the unmodified value of 0.5
        vmin : float, optional
            The data value that defines ``0.0`` in the normalization.
            Defaults to the min value of the dataset.
        vmax : float, optional
            The data value that defines ``1.0`` in the normalization.
            Defaults to the the max value of the dataset.

        Examples
        --------
        This maps data value -4000 to 0., 0 to 0.5, and +10000 to 1.0; data
        between is linearly interpolated::

            >>> import matplotlib.colors as mcolors
            >>> offset = mcolors.TwoSlopeNorm(vmin=-4000.,
                                              vcenter=0., vmax=10000)
            >>> data = [-4000., -2000., 0., 2500., 5000., 7500., 10000.]
            >>> offset(data)
            array([0., 0.25, 0.5, 0.625, 0.75, 0.875, 1.0])
        """

        self.vcenter = vcenter
        self.P25 = P25
        self.P75 = P75
        self.vmin = vmin
        self.vmax = vmax
        if vcenter is not None and vmax is not None and vcenter >= vmax:
            raise ValueError('vmin, vcenter, and vmax must be in '
                             'ascending order')
        if vcenter is not None and vmin is not None and vcenter <= vmin:
            raise ValueError('vmin, vcenter, and vmax must be in '
                             'ascending order')
        if P25 <= 0 or P25 >= 1:
            raise ValueError('P25 must be between 0 and 1')
        if P75 <= 0 or P75 >= 1:
            raise ValueError('P75 must be between 0 and 1')

    def autoscale_None(self, A):
        """
        Get vmin and vmax, and then clip at vcenter
        """
        super().autoscale_None(A)
        if self.vmin > self.vcenter:
            self.vmin = self.vcenter
        if self.vmax < self.vcenter:
            self.vmax = self.vcenter

    def __call__(self, value, clip=None):
        """
        Map value to the interval [0, 1]. The clip argument is unused.
        """
        result, is_scalar = self.process_value(value)
        self.autoscale_None(result)  # sets self.vmin, self.vmax if None

        if not self.vmin <= self.vcenter <= self.vmax:
            raise ValueError("vmin, vcenter, vmax must increase monotonically")
        result = np.ma.masked_array(
            np.interp(result, [self.vmin, self.vcenter - (self.vcenter - self.vmin)*self.P25, self.vcenter, self.vcenter + (self.vmax - self.vcenter)*self.P75, self.vmax],
                      [0, 0.25, 0.5, 0.75, 1.]), mask=np.ma.getmask(result))
        if is_scalar:
            result = np.atleast_1d(result)[0]
        return result
        

class DivLogNorm(Normalize):
    """Normalize a given value to the 0-1 range on a log scale. The first
    arg (centerpct) is the centerpoint of the diverging colors (between 0
    and 1)"""
    def __init__(self, centerpct, vmin=None, vmax=None, clip=False):
        super().__init__(vmin, vmax, clip)
        self.centerpct = centerpct

    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        result = np.ma.masked_less_equal(result, 0, copy=False)

        self.autoscale_None(result)
        vmin, vmax = self.vmin, self.vmax
        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin <= 0:
            raise ValueError("values must all be positive")
        elif vmin == vmax:
            result.fill(0)
        else:
            if clip:
                mask = np.ma.getmask(result)
                result = np.ma.array(np.clip(result.filled(vmax), vmin, vmax),
                                     mask=mask)
            # in-place equivalent of above can be much faster
            resdat = result.data
            mask = result.mask
            if mask is np.ma.nomask:
                mask = (resdat <= 0)
            else:
                mask |= resdat <= 0
            np.copyto(resdat, 1, where=mask)
            np.log(resdat, resdat)
            resdat -= np.log(vmin)
            resdat /= (np.log(vmax) - np.log(vmin))
            result = np.ma.array(resdat, mask=mask, copy=False)
            result = np.ma.masked_array(
                np.interp(result, [0, self.centerpct, 1],
                          [0, 0.5, 1.]), mask=np.ma.getmask(result))
        if is_scalar:
            result = result[0]
        return result

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until scaled")
        vmin, vmax = self.vmin, self.vmax

        if np.iterable(value):
            val = np.ma.asarray(value)
            return vmin * np.ma.power((vmax / vmin), val)
        else:
            return vmin * pow((vmax / vmin), value)

    def autoscale(self, A):
        # docstring inherited.
        super().autoscale(np.ma.masked_less_equal(A, 0, copy=False))

    def autoscale_None(self, A):
        # docstring inherited.
        super().autoscale_None(np.ma.masked_less_equal(A, 0, copy=False))

## Only works with older matplotlib versions
# class DivSymLogNorm(colors.SymLogNorm):
#     def __init__(self, linthresh, centerpct=0.5, linscale=1.0, vmin=None, vmax=None, clip=False):
#         super().__init__(linthresh, linscale, vmin, vmax, clip)
#         self.centerpct = centerpct
#
#     def __call__(self, value, clip=None):
#         if clip is None:
#             clip = self.clip
#
#         result, is_scalar = self.process_value(value)
#         self.autoscale_None(result)
#         vmin, vmax = self.vmin, self.vmax
#
#         if vmin > vmax:
#             raise ValueError("minvalue must be less than or equal to maxvalue")
#         elif vmin == vmax:
#             result.fill(0)
#         else:
#             if clip:
#                 mask = np.ma.getmask(result)
#                 result = np.ma.array(np.clip(result.filled(vmax), vmin, vmax),
#                                      mask=mask)
#             # in-place equivalent of above can be much faster
#             resdat = self._transform(result.data)
#             resdat -= self._lower
#             resdat /= (self._upper - self._lower)
#             result = np.ma.masked_array(
#                 np.interp(result, [0, self.centerpct, 1],
#                           [0, 0.5, 1.]), mask=np.ma.getmask(result))
#
#         if is_scalar:
#             result = result[0]
#         return result

class DivSymLogNorm(Normalize):
    """
    The symmetrical logarithmic scale is logarithmic in both the
    positive and negative directions from the origin.

    This is just edited to adjust the centerpoint with the centerpct parameter

    Since the values close to zero tend toward infinity, there is a
    need to have a range around zero that is linear.  The parameter
    *linthresh* allows the user to specify the size of this range
    (-*linthresh*, *linthresh*).
    """
    def __init__(self, linthresh, centerpct=0.5, linscale=1.0, vmin=None, vmax=None,
                 clip=False, *, base=None):
        """
        Parameters
        ----------
        linthresh : float
            The range within which the plot is linear (to avoid having the plot
            go to infinity around zero).

        linscale : float, default: 1
            This allows the linear range (-*linthresh* to *linthresh*)
            to be stretched relative to the logarithmic range. Its
            value is the number of powers of *base* to use for each
            half of the linear range.

            For example, when *linscale* == 1.0 (the default) and
            ``base=10``, then space used for the positive and negative
            halves of the linear range will be equal to a decade in
            the logarithmic.

        base : float, default: None
            If not given, defaults to ``np.e`` (consistent with prior
            behavior) and warns.

            In v3.3 the default value will change to 10 to be consistent with
            `.SymLogNorm`.

            To suppress the warning pass *base* as a keyword argument.

        """
        Normalize.__init__(self, vmin, vmax, clip)
        if base is None:
            self._base = 10  # default to base 10
        else:
            self._base = base
        self._log_base = np.log(self._base)

        self.linthresh = float(linthresh)
        self.centerpct = float(centerpct)
        self._linscale_adj = (linscale / (1.0 - self._base ** -1))
        if vmin is not None and vmax is not None:
            self._transform_vmin_vmax()

    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)
        self.autoscale_None(result)
        vmin, vmax = self.vmin, self.vmax

        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin == vmax:
            result.fill(0)
        else:
            if clip:
                mask = np.ma.getmask(result)
                result = np.ma.array(np.clip(result.filled(vmax), vmin, vmax),
                                     mask=mask)
            # in-place equivalent of above can be much faster
            resdat = self._transform(result.data)
            resdat -= self._lower
            resdat /= (self._upper - self._lower)
            result = np.ma.masked_array(
                np.interp(result, [0, self.centerpct, 1],
                          [0, 0.5, 1.]), mask=np.ma.getmask(result))

        if is_scalar:
            result = result[0]
        return result

    def _transform(self, a):
        """Inplace transformation."""
        with np.errstate(invalid="ignore"):
            masked = np.abs(a) > self.linthresh
        sign = np.sign(a[masked])
        log = (self._linscale_adj +
               np.log(np.abs(a[masked]) / self.linthresh) / self._log_base)
        log *= sign * self.linthresh
        a[masked] = log
        a[~masked] *= self._linscale_adj
        return a

    def _inv_transform(self, a):
        """Inverse inplace Transformation."""
        masked = np.abs(a) > (self.linthresh * self._linscale_adj)
        sign = np.sign(a[masked])
        exp = np.power(self._base,
                       sign * a[masked] / self.linthresh - self._linscale_adj)
        exp *= sign * self.linthresh
        a[masked] = exp
        a[~masked] /= self._linscale_adj
        return a

    def _transform_vmin_vmax(self):
        """Calculate vmin and vmax in the transformed system."""
        vmin, vmax = self.vmin, self.vmax
        arr = np.array([vmax, vmin]).astype(float)
        self._upper, self._lower = self._transform(arr)

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until scaled")
        val = np.ma.asarray(value)
        val = val * (self._upper - self._lower) + self._lower
        return self._inv_transform(val)

    def autoscale(self, A):
        # docstring inherited.
        super().autoscale(A)
        self._transform_vmin_vmax()

    def autoscale_None(self, A):
        # docstring inherited.
        super().autoscale_None(A)
        self._transform_vmin_vmax()

# # For use with nplab_qtplot_v0.2.5... Won't install if qtplot isn't installed
reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
installed_packages = [r.decode() for r in reqs.split()]
if 'qtplot==0.2.5' in installed_packages:
    import qtplot

    def qt2dplot(xdata, ydata, zdata):
        """import xdata, ydata as 1d arrays. Zdata as a 2d array
        This function plots the data in qtplot"""
        zs = zdata.shape
        xx, yy = np.mgrid[0:zs[0], 0:zs[1]]
        xd = np.tensordot(xdata, np.ones(zs[0]), axes=0).T
        yd = np.tensordot(ydata, np.ones(zs[1]), axes=0)
        boo = [xd.shape == zs, yd.shape == zs]
        if all(boo):
            plot_data = qtplot.qtplot.Data2D(xd, yd, zdata, row_numbers=xx)  # row numbers can be xx or yy?
            return qtplot.qtplot.QTPlot(plot_data)
        else:
            print('You need all of these to match. Check the dimensions of the data arrays.')
            print('xdata shape: {}'.format(xd.shape))
            print('ydata shape: {}'.format(yd.shape))
            print('zdata shape: {}'.format(zs))



# TODO: Make these functions work with datasets: below
# def concat_2d_dset(dsets, xparam, yparam, zparam):
#     """Concatenates 2D datasets. When the x direction has been partially measured
#     for the top y point and has been replaced by the second array, this
#     function replaces the points with the second array and concatenates the two
#
#     dsets must be a tuple, of length 2 or more, of qcodes datasets
#     xparam, yparam, zparam, are the parameter names (instr.param) used in the
#     measurement
#
#     Note: xparam is for the inner loop sweep, and yparam the outer loop. Also,
#     enter the dsets in the order that they were taken.
#
#     returns a combined dataset with the correct labels, names, and array_ids
#     just like the first dset
#     """
#
#     xp = str(xparam) + '_set'
#     yp = str(yparam) + '_set'
#     zp = str(zparam)
#
#     if len(dsets) < 2:
#         raise ValueError('Need tuple of length >=2 for argument')
#
#     # Check for same x shapes
#     for a in dsets[1:len(dsets)]:
#         if getattr(a, xp).shape[1] != getattr(dsets[0], xp).shape[1]:
#                 raise ValueError('Datasets must have same length in x')
#
#     cdata = qc.new_data()
#
#     # TODO: Introduce ypvals here straight from the arrays and then update them
#     # in the loop continuously
#
#     yfinalvals = []
#
#     npdsetsx = []
#     npdsetsz = []
#     for i in range(0, len(dsets)-1):
#         nextarray = False
#         for j in range(0, len(getattr(dsets[i], yp))):
#             ypval = getattr(dsets[i], yp)[j]
#             if (ypval in getattr(dsets[i+1], yp) or ypval is np.nan) and \
#                     nextarray is False:
#                     # If this point is in the next array, append the array up
#                     # to that point and append the next array
#                 yfinalvals.append(getattr(dsets[i], yp)[0:j])
#
#                 npdsetsx.append(getattr(dsets[i], xp)[0:j])
#                 npdsetsz.append(getattr(dsets[i], zp)[0:j])
#
#                 npdsetsx[i].append(*getattr(dsets[i+1], xp))
#                 npdsetsz[i].append(*getattr(dsets[i+1], zp))
#                 nextarray = True
#             elif nextarray is True and ypval is np.nan:
#                 # if nan, break. No more values to search for
#                 break
#             elif nextarray is False and j == len(getattr(dsets[i], yp))-1:
#                 # if the end of the array and no match, append the next array
#                 npdsetsx.append(getattr(dsets[i], xp))
#                 npdsetsy.append(getattr(dsets[i], yp))
#                 npdsetsz.append(getattr(dsets[i], zp))
#
#                 npdsetsx[i].append(*getattr(dsets[i+1], xp))
#                 npdsetsy[i].append(*getattr(dsets[i+1], yp))
#                 npdsetsz[i].append(*getattr(dsets[i+1], zp))
#
#             elif nextarray is True and ypval not in getattr(dsets[i+1], yp):
#                 # if the next array is already appended, and there are values
#                 # not in that array, append them
#                 npdsetsx[i].append(getattr(dsets[i], xp)[j])
#                 npdsetsy[i].append(getattr(dsets[i], yp)[j])
#                 npdsetsz[i].append(getattr(dsets[i], zp)[j])
#
#     # Assign dataset attributes to new dataset arrays
#     aidx = getattr(dsets[0], xp).array_id
#     aidy = getattr(dsets[0], yp).array_id
#     aidz = getattr(dsets[0], zp).array_id
#     anamex = getattr(dsets[0], xp).name
#     anamey = getattr(dsets[0], yp).name
#     anamez = getattr(dsets[0], zp).name
#     alabelx = getattr(dsets[0], xp).label
#     alabely = getattr(dsets[0], yp).label
#     alabelz = getattr(dsets[0], zp).label
#     aunitx = getattr(dsets[0], xp).unit
#     aunity = getattr(dsets[0], yp).unit
#     aunitz = getattr(dsets[0], zp).unit

def graphene_mobilityFE(n, sigmaxx):
    """Find the mobility of graphene using the regular low-limit field-effect
    linear fit to the slope near the CNP. Input here a small region where you
    want to apply the linear fit about the CNP.
    Use density n in cm^-2 and
    rhoxx in ohms/sq

    Returns: mobility (cm^2/(Vs))"""

    params = np.polyfit(n*1.602e-19, sigmaxx, 1)
    return params[0]


def gr_Boltzmannfit(dens, mu, rhos):
    """ dens is electron density in units of cm^-2.
    mu is in cm^2/(Vs). rhos is the base resistivity at high
    density. returns sigma_xx"""

    return ((dens*1.602e-19*mu)**-1 + rhos)**-1


def graphene_mobilityB(n, sigmaxx):
    """Find the mobility of graphene using a Boltzmann fit as used in Cory
    Dean's first hBN paper.
    Use density n in cm^-2, rhoxx in ohms/sq.

    Returns: param -- a list of parameters, first is mobility (unit cm^2/(Vs))
    and second is rho_s, which is the residual resistivity at high density"""

    if n[5] > 0:
        mu0 = 100000
    elif n[5] < 0:
        mu0 = -100000
    params, pcov = curve_fit(gr_Boltzmannfit, n, sigmaxx, p0=[mu0, 50])
    return params

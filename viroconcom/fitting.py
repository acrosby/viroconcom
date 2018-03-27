#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fit distribution to data.
"""

from multiprocessing import Pool
import numpy as np
import statsmodels.api as sm
import scipy.stats as sts
from scipy.optimize import curve_fit
from .params import ConstantParam, FunctionParam
from .distributions import (WeibullDistribution, LognormalDistribution, NormalDistribution,
                                   KernelDensityDistribution,
                                   MultivariateDistribution)
import warnings

__all__ = ["Fit"]


# ----------------------------
# Functions for fitting

# Exponential function
def _f2(x, a, b, c):
    return a + b * np.exp(c * x)

# Power function
def _f1(x, a, b, c):
    return a + b * x ** c

# Bounds for function parameters
# 0 < a < inf
# 0 < b < inf
# -inf < c < inf

_bounds = ([np.finfo(np.float64).tiny, np.finfo(np.float64).tiny, -np.inf],
          [np.inf, np.inf, np.inf])
# ----------------------------

class BasicFit():
    """
    Holds the parameters (shape, loc, scale) and also the raw data to a single fit.

    Attributes
    ----------
    shape : float,
        The shape parameter for the fit.

    loc : float,
        The location parameter for the fit.

    scale : float,
        The scale parameter for the fit.

    samples : list of float,
        The raw data that is used for this fit. For that case that there is no dependency this
        list contains the whole data of the dimension.

    """

    def __init__(self, shape, loc, scale, samples):

        # Parameters for the distribution
        self.shape = shape
        self.loc = loc
        self.scale = scale

        # Raw data
        self.samples = samples

class FitInspectionData():
    """
    This class holds information for plotting the fits of a single dimension. It is used to give
    a visual look about how good the fits in this dimension were.

    Attributes
    ----------
    used_number_of_intervals : int,
        The actually number of intervals this dimension is divided for other dependent dimensions.

    shape_at : list of float,
        This list contains the values of the divided dimension the shape parameter depends on.

    shape_value : list of float,
        The associated values of the parameter shape to the divided dimension the shape
        parameter depends on.

    loc_at : list of float,
        This list contains the values of the divided dimension the location parameter depends on.

    loc_value : list of float,
        The associated values of the parameter loc to the divided dimension the location
        parameter depends on.

    scale_at : list of float,
        This list contains the values of the divided dimension the scale parameter depends on.

    scale_value : list of float,
        The associated values of the parameter scale to the divided dimension the scale
        parameter depends on.

    shape_samples : list of list,
        This list with the length of the number of used intervals for the shape parameter
        contains lists with the used samples for the respective fit.

    loc_samples : list of list,
        This list with the length of the number of used intervals for the location parameter
        contains lists with the used samples for the respective fit.

    scale_samples : list of list,
        This list with the length of the number of used intervals for the scale parameter
        contains lists with the used samples for the respective fit.

    """

    def __init__(self):

        # Number of the intervals this dimension is divided
        self.used_number_of_intervals = None

        # Parameter values and the data they belong to
        self.shape_at = None
        self._shape_value = [None, None, None]

        self.loc_at = None
        self._loc_value = [None, None, None]

        self.scale_at = None
        self._scale_value = [None, None, None]

        # Raw data for each parameter of this dimension
        self.shape_samples = None
        self.loc_samples = None
        self.scale_samples = None

    @property
    def shape_value(self):
        """
        Takes out the list that contains the shape parameters.

        Returns
        -------
        list of float,
             The associated values of the parameter shape to the divided dimension the shape
             parameter depends on.
        Notes
        ------
        This function can be used as attribute. For example:
        >>> v_i_data_dim_0.shape_value
        """
        return self._shape_value[0]

    @property
    def loc_value(self):
        """
        Takes out the list that contains the location parameters.

        Returns
        -------
        list of float,
             The associated values of the parameter loc to the divided dimension the location
             parameter depends on.
        Notes
        ------
        This function can be used as attribute. For example:
        >>> v_i_data_dim_0.loc_value
        """
        return self._loc_value[1]

    @property
    def scale_value(self):
        """
        Takes out the list that contains the scale parameters.

        Returns
        -------
        list of float,
             The associated values of the parameter scale to the divided dimension the scale
             parameter depends on.
        Notes
        ------
        This function can be used as attribute. For example:
        >>> v_i_data_dim_0.scale_value
        """
        return self._scale_value[2]

    def append_basic_fit(self, param ,basic_fit):
        """
        This function can be used to add a single fit to the hold data.

        Parameters
        ----------
        param : str,
            The respective parameter the data should be associated.
        basic_fit : BasicFit,
            The data of the single fit hold in a BasicData object.
        Raises
        ------
        ValueError,
            If the parameter is unknown.
        """
        if param == 'shape':
            self._shape_value[0].append(basic_fit.shape)
            self._shape_value[1].append(basic_fit.loc)
            self._shape_value[2].append(basic_fit.scale)
            self.shape_samples.append(basic_fit.samples)
        elif param == 'loc':
            self._loc_value[0].append(basic_fit.shape)
            self._loc_value[1].append(basic_fit.loc)
            self._loc_value[2].append(basic_fit.scale)
            self.loc_samples.append(basic_fit.samples)
        elif param == 'scale':
            self._scale_value[0].append(basic_fit.shape)
            self._scale_value[1].append(basic_fit.loc)
            self._scale_value[2].append(basic_fit.scale)
            self.scale_samples.append(basic_fit.samples)
        else:
            err_msg = "Parameter '{}' is unknown.".format(param)
            raise ValueError(err_msg)

    def get_basic_fit(self, param, index):
        """
        This function returns the data of a single fit to a given parameter and the index of the
        interval of the divided dimension the parameter depends on.

        Parameters
        ----------
        param : str,
            The respective parameter of the data.
        index : int,
            The index of the interval.
        Returns
        -------
        BasicFit,
             The data of the single fit hold in a BasicData object.
        Raises
        ------
        ValueError,
            If the parameter is unknown.
        """
        if param == 'shape':
            return BasicFit(self._shape_value[0][index], self._shape_value[1][index],
                            self._shape_value[2][index], self.shape_samples[index])
        elif param == 'loc':
            return BasicFit(self._loc_value[0][index], self._loc_value[1][index],
                            self._loc_value[2][index], self.loc_samples[index])
        elif param == 'scale':
            return BasicFit(self._scale_value[0][index], self._scale_value[1][index],
                            self._scale_value[2][index], self.scale_samples[index])
        else:
            err_msg = "Parameter '{}' is unknown.".format(param)
            raise ValueError(err_msg)


class Fit():
    """
    Holds data and information about a fit.

    Note
    ----
    The fitted results are not checked for correctness. The created distributions may not contain useful
    parameters. Distribution parameters are being checked in the contour creation process.

    Attributes
    ----------
    mul_var_dist : MultivariateDistribution,
        Distribution that is calculated

    multiple_fit_inspection_data : list of FitInspectionData,
        Contains fit inspection data objects for each dimension.

    Examples
    --------
    Create a Fit and visualize the result in a IFORM contour:

    >>> from multiprocessing import Pool
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> import statsmodels.api as sm
    >>> import scipy.stats as sts
    >>> from scipy.optimize import curve_fit
    >>> from compute.params import ConstantParam, FunctionParam
    >>> from compute.distributions import (WeibullDistribution,\
                                           LognormalDistribution,\
                                           NormalDistribution,\
                                           KernelDensityDistribution,\
                                           MultivariateDistribution)
    >>> from compute.contours import IFormContour
    >>> prng = np.random.RandomState(42)
    >>> sample_1 = prng.normal(10, 1, 500)
    >>> sample_2 = [point + prng.uniform(-5, 5) for point in sample_1]
    >>> dist_description_1 = {'name': 'KernelDensity', 'dependency': (None, None, None)}
    >>> dist_description_2 = {'name': 'Normal', 'dependency': (None, 0, None), 'functions':(None, 'f1', None)}
    >>> my_fit = Fit((sample_1, sample_2), (dist_description_1, dist_description_2), 5)
    >>> my_contour = IFormContour(my_fit.mul_var_dist)
    >>> #example_plot = plt.scatter(my_contour.coordinates[0][0], my_contour.coordinates[0][1], label="IForm")


    Create a Fit and visualize the result in a HDC contour:

    >>> from compute.contours import HighestDensityContour
    >>> sample_1 = prng.weibull(2, 500) + 15
    >>> sample_2 = [point + prng.uniform(-1, 1) for point in sample_1]
    >>> dist_description_1 = {'name': 'Weibull', 'dependency': (None, None, None)}
    >>> dist_description_2 = {'name': 'Normal', 'dependency': (None, None, None)}
    >>> my_fit = Fit((sample_1, sample_2), (dist_description_1, dist_description_2), 5)
    >>> return_period = 50
    >>> state_duration = 3
    >>> limits = [(0, 20), (0, 20)]
    >>> deltas = [0.05, 0.05]
    >>> my_contour = HighestDensityContour(my_fit.mul_var_dist, return_period, state_duration, limits, deltas,)
    >>> #example_plot2 = plt.scatter(my_contour.coordinates[0][0], my_contour.coordinates[0][1], label="HDC")


    An Example how to use the attributes mul_param_points and mul_dist_points to visualize how good your fit is:

    >>> dist_description_0 = {'name': 'Weibull', 'dependency': (None, None, None)}
    >>> dist_description_1 = {'name': 'Lognormal_1', 'dependency': (None, None, 0), 'functions': (None, None, 'f2')}
    >>> my_fit = Fit((sample_1, sample_2), (dist_description_0, dist_description_1), 3)
    >>>
    >>> #fig = plt.figure(figsize=(10, 8))
    >>> #example_text = fig.suptitle("Dependence of 'scale'")
    >>>
    >>> #ax_1 = fig.add_subplot(221)
    >>> #title1 = ax_1.set_title("Fitted curve")
    >>> param_grid = my_fit.mul_param_points[1][2][0]
    >>> x_1 = np.linspace(5, 15, 100)
    >>> #ax1_plot = ax_1.plot(param_grid, my_fit.mul_param_points[1][2][1], 'x')
    >>> #example_plot1 = ax_1.plot(x_1, my_fit.mul_var_dist.distributions[1].scale(x_1))
    >>>
    >>> #ax_2 = fig.add_subplot(222)
    >>> #title2 = ax_2.set_title("Distribution '1'")
    >>> #ax2_hist = ax_2.hist(my_fit.mul_dist_points[1][2][0], normed=1)
    >>> shape = my_fit.mul_var_dist.distributions[1].shape(None)
    >>> scale = my_fit.mul_var_dist.distributions[1].scale(param_grid[0])
    >>> #ax2_plot = ax_2.plot(np.linspace(0, 20, 100), sts.lognorm.pdf(np.linspace(0, 20, 100), s=shape, scale=scale))
    >>>
    >>> #ax_3 = fig.add_subplot(223)
    >>> #title3 = ax_3.set_title("Distribution '2'")
    >>> #ax3_hist = ax_3.hist(my_fit.mul_dist_points[1][2][1], normed=1)
    >>> shape = my_fit.mul_var_dist.distributions[1].shape(None)
    >>> scale = my_fit.mul_var_dist.distributions[1].scale(param_grid[1])
    >>> #ax3_plot = ax_3.plot(np.linspace(0, 20, 100), sts.lognorm.pdf(np.linspace(0, 20, 100), s=shape, scale=scale))
    >>>
    >>> #ax_4 = fig.add_subplot(224)
    >>> #title4 = ax_4.set_title("Distribution '3'")
    >>> #ax4_hist = ax_4.hist(my_fit.mul_dist_points[1][2][2], normed=1)
    >>> shape = my_fit.mul_var_dist.distributions[1].shape(None)
    >>> scale = my_fit.mul_var_dist.distributions[1].scale(param_grid[2])
    >>> #ax4_plot = ax_4.plot(np.linspace(0, 20, 100), sts.lognorm.pdf(np.linspace(0, 20, 100), s=shape, scale=scale))

    """

    def __init__(self, samples, dist_descriptions):
        """
        Creates a Fit, by computing the distribution that describes the samples 'best'.

        Parameters
        ----------
        samples : list,
            List that contains data to be fitted : samples[0] -> first variable (i.e. wave height)
                                                   samples[1] -> second variable
                                                   ...
        dist_descriptions : list,
            contains dictionary for each parameter. See note for further information.

        Note
        ----
        dist_descriptions contains the following keys:

        name : str,
            name of distribution:

            - Weibull
            - Lognormal_1 (shape, scale)
            - Lognormal_2 (sigma, mu),
            - Normal
            - KernelDensity (no dependency)

        dependency : list,
            Length of 3 in the order (shape, loc, scale) contains:

            - None -> no dependency
            - int -> depends on particular dimension

        functions : list,
            Length of 3 in the order : (shape, loc, scale), usable options:

            - :f1: :math:`a + b * x^c`
            - :f2: :math:`a + b * e^{x * c}`
            - remark : in case of Lognormal_2 it is (sigma, loc=0, mu)

        and either number_of_bins or width_of_bins:

        number_of_intervals : int,
            Number of bins the data of this variable should be seperated for fits which depend
                upon it. If the number of bins is given, the width of the bins is determined automatically.

        width_of_bins : floats,
            Width of the bins. When the width of the bins is given, the number of bins is
            determined automatically.

        """
        self.dist_descriptions = dist_descriptions # compute references this attribute at plot.py

        list_number_of_intervals = []
        list_width_of_intervals = []
        for dist_description in dist_descriptions:
            list_number_of_intervals.append(dist_description.get('number_of_intervals'))
            list_width_of_intervals.append(dist_description.get('width_of_intervals'))
        for dist_description in dist_descriptions:
            dist_description['list_number_of_intervals'] = list_number_of_intervals
            dist_description['list_width_of_intervals'] = list_width_of_intervals

        # multiprocessing for more performance
        pool = Pool()
        multiple_results = []

        # Fit inspection data for each dimension
        self.multiple_fit_inspection_data = []

        # distribute work on cores
        for dimension in range(len(samples)):
            dist_description = dist_descriptions[dimension]
            multiple_results.append(
                pool.apply_async(self._get_distribution, (dimension, samples), dist_description))

        # Initialize parameters for multivariate distribution
        distributions = []
        dependencies = []

        # Get distributions
        for i, res in enumerate(multiple_results):
            distribution, dependency, fit_inspection_data, \
            used_number_of_intervals = res.get(timeout=1e6)

            # Saves distribution and dependency for particular dimension
            distributions.append(distribution)
            dependencies.append(dependency)

            # Add fit inspection data for current dimension
            self.multiple_fit_inspection_data.append(fit_inspection_data)

            # Save the used number of intervals
            for dep_index, dep in enumerate(dependency):
                if dep is not None:
                    self.dist_descriptions[dep]['used_number_of_intervals'] = used_number_of_intervals[dep_index]

        # Add used number of intervals for dimensions with no dependency
        for fit_inspection_data in self.multiple_fit_inspection_data:
            if not fit_inspection_data.used_number_of_intervals:
                fit_inspection_data.used_number_of_intervals = 1

        # Save multivariate distribution
        self.mul_var_dist = MultivariateDistribution(distributions, dependencies)

    @staticmethod
    def _fit_distribution(sample, name):
        """
        Fits the distribution and returns the parameters.

        Parameters
        ----------
        sample : list,
            raw data

        name : str,
            name of distribution (Weibull, Lognormal, Normal, KernelDensity (no dependency))

        """

        if name == 'Weibull':
            params = sts.weibull_min.fit(sample)
        elif name == 'Normal':
            params = list(sts.norm.fit(sample))
            # shape doesn't exist for normal
            params.insert(0, 0)
        elif name[:-2] == 'Lognormal':
            # For lognormal loc is set to 0
            params = sts.lognorm.fit(sample, floc=0)
        elif name == 'KernelDensity':
            dens = sm.nonparametric.KDEUnivariate(sample)
            dens.fit(gridsize=2000)
            # kernel density doesn't have shape, loc, scale
            return (dens.cdf, dens.icdf)
        return (ConstantParam(params[0]), ConstantParam(params[1]), ConstantParam(params[2]))

    @staticmethod
    def _get_function(function_name):
        """
        Returns the function.
^
        Parameters
        ----------
        function_name : str,
            options are 'f1', 'f2'
        """
        
        if function_name == 'f1':
            return _f1
        elif function_name == 'f2':
            return _f2
        elif function_name is None:
            return None
        else:
            err_msg = "Function '{}' is unknown.".format(function_name)
            raise ValueError(err_msg)

    @staticmethod
    def _append_params(name, param_values, dependency, index, fitting_values):
        """
        Distributions are being fitted and the results are appended to param_points

        Parameters
        ----------
        name : str,
            name of distribution (Weibull, Lognormal, Normal, KernelDensity (no dependency))

        param_values : list,
            contains lists that contain values for each param : order (shape, loc, scale)

        dependency : list,
            Length of 3 in the order (shape, loc, scale) contains :
            None -> no dependency
            int -> depends on particular dimension

        index : int,
            order : (shape, loc, scale) (i.e. 0 -> shape)

        fitting_values : list,
            values that are used to fit the distribution


        """

        # fit distribution
        current_params = Fit._fit_distribution(fitting_values, name)

        # Create basic fit object
        basic_fit = BasicFit(*current_params, fitting_values)

        for i in range(index, len(dependency)):
            # check if there is a dependency and whether it is the right one
            if dependency[i] is not None and \
                            dependency[i] == dependency[index]:
                # calculated parameter is appended to param_values
                param_values[i].append(current_params[i])
        return basic_fit

    @staticmethod
    def _get_fitting_values(sample, samples, name, dependency, index, number_of_intervals=None, bin_width=None):
        """
        Returns values for fitting.

        Parameters
        ----------
        sample : list,
            data to be fit

        samples : list,
            List that contains data to be fitted : samples[0] -> first variable (i.e. wave height)
                                                   samples[1] -> second variable
                                                   ...

        name : str,
            name of distribution (Weibull, Lognormal, Normal, KernelDensity (no dependency))

        dependency : list,
            Length of 3 in the order (shape, loc, scale) contains :
                None -> no dependency
                int -> depends on particular dimension

        index : int,
            order : (shape, loc, scale) (i.e. 0 -> shape)

        number_of_intervals : int,
            number of distributions used to fit shape, loc, scale

        Returns
        -------
        interval_centers :

        dist_values :

        param_values :



        """
        MIN_DATA_POINTS_FOR_FIT = 10

        # compute intervals
        if number_of_intervals:
            interval_centers, interval_width = np.linspace(0, max(samples[dependency[index]]),
                                                      num=number_of_intervals, endpoint=False, retstep=True)
            interval_centers += 0.5 * interval_width
        elif bin_width:
            interval_width = bin_width
            interval_centers = np.arange(0.5*interval_width, max(samples[dependency[index]]), interval_width)
        else:
            raise RuntimeError(
                "Either the parameters number_of_intervals or bin_width has to be specified, otherwise the intervals"
                " are not specified. Exiting."
            )
        # sort samples
        samples = np.stack((sample, samples[dependency[index]])).T
        sort_indice = np.argsort(samples[:, 1])
        sorted_samples = samples[sort_indice]
        # return values
        param_values = [[], [], []]
        dist_values = []

        # List of all basic fits
        multiple_basic_fit = []

        # look for data that is fitting to each step
        for i, step in enumerate(interval_centers):
            mask = ((sorted_samples[:, 1] >= step - 0.5 * interval_width) & (sorted_samples[:, 1] < step + 0.5 * interval_width))
            fitting_values = sorted_samples[mask, 0]
            if len(fitting_values) >= MIN_DATA_POINTS_FOR_FIT:
                try:
                    # fit distribution to selected data
                    basic_fit = Fit._append_params(name, param_values, dependency, index, fitting_values)
                    multiple_basic_fit.append(basic_fit)
                    dist_values.append(fitting_values)
                except ValueError:
                    # for case that no fitting data for the step has been found -> step is deleted
                    interval_centers = np.delete(interval_centers,i)
                    warnings.warn(
                        "There is not enough data for step '{}' in dimension '{}'. This step is skipped. "
                        "Maybe you should ckeck your data or reduce the number of steps".format(step, dependency[index]),
                        RuntimeWarning, stacklevel=2)
            else:
                # for case that to few fitting data for the step has been found -> step is deleted
                interval_centers = np.delete(interval_centers,i)
                warnings.warn(
                    "'Due to the restriction of MIN_DATA_POINTS_FOR_FIT='{}' there is not enough data (n='{}') for the interval centered at '{}' in"
                    " dimension '{}'. This step is skipped. Maybe you should ckeck your data or reduce the number "
                    "of steps".format(MIN_DATA_POINTS_FOR_FIT, len(fitting_values), step, dependency[index]),
                    RuntimeWarning, stacklevel=2)
        if len(interval_centers) < 3:
            raise RuntimeError("Your settings resulted in " + str(len(interval_centers)) + " intervals. However, "
                               "at least 3 intervals are required. Consider changing the interval width setting.")
        return interval_centers, dist_values, param_values, multiple_basic_fit

    def _get_distribution(self, dimension, samples, **kwargs):
        """
        Returns the fitted distribution, the dependency and the points for plotting the fits.

        Parameters
        ----------
        dimension : int,
            Number of the variable, e.g. 0 --> first variable (for exmaple sig. wave height)

        samples : list,
            List that contains data to be fitted : samples[0] -> first variable (for example sig. wave height)
                                                   samples[1] -> second variable
                                                   ...

        Returns
        -------
        distribution : ParametricDistribution instance,
            The fitted distribution instance

        dependency : ?

        used_number_of_intervals: int,
            TODO

        fit_inspection_data : FitInspectionData,
            TODO

        """

        # save settings for distribution
        sample = samples[dimension]
        name = kwargs.get('name', 'Weibull')
        dependency = kwargs.get('dependency', (None, None, None))
        functions = kwargs.get('functions', ('polynomial', 'polynomial', 'polynomial'))
        list_number_of_intervals = kwargs.get('list_number_of_intervals')
        list_width_of_intervals = kwargs.get('list_width_of_intervals')

        # Fit inspection data for current dimension
        fit_inspection_data = FitInspectionData()

        # handle KernelDensity separated
        if name == 'KernelDensity':
            if dependency != (None, None, None):
                raise NotImplementedError("KernelDensity can not be conditional.")
            return KernelDensityDistribution(Fit._fit_distribution(sample, name)), dependency, [
                [sample], [sample], [sample]], [None, None, None]

        # initialize params (shape, loc, scale)
        params = [None, None, None]

        # Initialize used_number_of_intervals (shape, loc, scale
        used_number_of_intervals = [None, None, None]

        for index in range(len(dependency)):

            # continue if params is yet computed
            if params[index] is not None:
                continue

            if dependency[index] is None:
                # case that there is no dependency for this param
                current_params = Fit._fit_distribution(sample, name)

                # Basic fit for no dependency
                basic_fit = BasicFit(*current_params, sample)
                for i in range(index, len(functions)):
                    # Check if the other parameters have also no dependency
                    if dependency[i] is None:

                        # Add basic fit to fit inspection data
                        # TODO maybe just use index incase of name as string
                        if i == 0:
                            fit_inspection_data.append_basic_fit('shape', basic_fit)
                        elif i == 1:
                            fit_inspection_data.append_basic_fit('loc', basic_fit)
                        elif i == 2:
                            fit_inspection_data.append_basic_fit('scale', basic_fit)

                        if i == 2 and name == 'Lognormal_2':
                            params[i] = ConstantParam(np.log(current_params[i](0)))
                        else:
                            params[i] = current_params[i]
            else:
                # Case that there is a dependency
                if list_number_of_intervals[dependency[index]]:
                    interval_centers, dist_values, param_values, multiple_basic_fit = Fit._get_fitting_values(
                        sample, samples, name, dependency, index, number_of_intervals=list_number_of_intervals[dependency[index]])
                elif list_width_of_intervals[dependency[index]]:
                    interval_centers, dist_values, param_values, multiple_basic_fit = Fit._get_fitting_values(
                        sample, samples, name, dependency, index, bin_width=list_width_of_intervals[dependency[index]])

                for i in range(index, len(functions)):
                    # Check if the other parameters have the same dependency
                    if dependency[i] is not None and dependency[i] == dependency[index]:
                        # Add basic fits to fit inspection data
                        # TODO maybe just use index incase of name as string
                        for basic_fit in multiple_basic_fit:
                            if i == 0:
                                fit_inspection_data.append_basic_fit('shape', basic_fit)
                            elif i == 1:
                                fit_inspection_data.append_basic_fit('loc', basic_fit)
                            elif i == 2:
                                fit_inspection_data.append_basic_fit('scale', basic_fit)

                        # Add used number of intervals for current parameter
                        used_number_of_intervals[i] = len(interval_centers)

                        if i == 2 and name == 'Lognormal_2':
                            fit_points = [np.log(p(None)) for p in param_values[i]]
                        else:
                            fit_points = [p(None) for p in param_values[i]]
                        # Fit params with particular function
                        try:
                            param_popt, param_pcov = curve_fit(
                                Fit._get_function(functions[i]),
                                interval_centers, fit_points, bounds=_bounds)
                        except RuntimeError:
                            # case that optimal parameters not found
                            if i == 0 and name == 'Lognormal_2':
                                param_name = "sigma"
                            elif i == 2 and name == 'Lognormal_2':
                                param_name = "mu"
                            elif i == 0:
                                param_name = "shape"
                            elif i == 1:
                                param_name = "loc"
                            elif i == 2:
                                param_name = "scale"

                            warnings.warn(
                                "Optimal Parameters not found for parameter '{}' in dimension '{}'. "
                                "Maybe switch the given function for a better fit. "
                                "Trying again with a higher number of calls to function '{}'."
                                "".format(param_name, dimension, functions[i]), RuntimeWarning,
                                stacklevel=2)
                            try:
                                param_popt, param_pcov = curve_fit(
                                    Fit._get_function(functions[i]),
                                    interval_centers, fit_points, bounds=_bounds, maxfev=int(1e6))
                            except RuntimeError:
                                raise RuntimeError(
                                    "Can't fit curve for parameter '{}' in dimension '{}'. "
                                    "Number of iterations exceeded.".format(param_name, dimension))

                        # save param
                        params[i] = FunctionParam(*param_popt, functions[i])

        # return particular distribution
        distribution = None
        if name == 'Weibull':
            distribution = WeibullDistribution(*params)
        elif name == 'Lognormal_2':
            distribution = LognormalDistribution(sigma=params[0], mu=params[2])
        elif name == 'Lognormal_1':
            distribution = LognormalDistribution(*params)
        elif name == 'Normal':
            distribution = NormalDistribution(*params)
        return distribution, dependency, used_number_of_intervals, fit_inspection_data

    def __str__(self):
        return "Fit() instance with dist_dscriptions: " + "".join([str(d) for d in self.dist_descriptions])


if __name__ == "__main__":
    import doctest
    doctest.testmod()
    # fit data by creating a Fit object

"""Module for Maximum Likelihood Estimation."""
from pyhf import get_backend
from pyhf.exceptions import UnspecifiedPOI

__all__ = ["fit", "fixed_poi_fit", "twice_nll"]


def __dir__():
    return __all__


def twice_nll(pars, data, pdf):
    r"""
    Two times the negative log-likelihood of the model parameters, :math:`\left(\mu, \boldsymbol{\theta}\right)`, given the observed data.
    It is used in the calculation of the test statistic, :math:`t_{\mu}`, as defined in Equation (8) in :xref:`arXiv:1007.1727`

    .. math::

       t_{\mu} = -2\ln\lambda\left(\mu\right)

    where :math:`\lambda\left(\mu\right)` is the profile likelihood ratio as defined in Equation (7)

    .. math::

       \lambda\left(\mu\right) = \frac{L\left(\mu, \hat{\hat{\boldsymbol{\theta}}}\right)}{L\left(\hat{\mu}, \hat{\boldsymbol{\theta}}\right)}\,.

    It serves as the objective function to minimize in :func:`~pyhf.infer.mle.fit`
    and :func:`~pyhf.infer.mle.fixed_poi_fit`.

    Example:
        >>> import pyhf
        >>> pyhf.set_backend("numpy")
        >>> model = pyhf.simplemodels.uncorrelated_background(
        ...     signal=[12.0, 11.0], bkg=[50.0, 52.0], bkg_uncertainty=[3.0, 7.0]
        ... )
        >>> observations = [51, 48]
        >>> data = pyhf.tensorlib.astensor(observations + model.config.auxdata)
        >>> parameters = model.config.suggested_init()  # nominal parameters
        >>> twice_nll = pyhf.infer.mle.twice_nll(parameters, data, model)
        >>> twice_nll
        array([30.77525435])
        >>> -2 * model.logpdf(parameters, data) == twice_nll
        array([ True])

    Args:
        pars (:obj:`tensor`): The parameters of the HistFactory model
        data (:obj:`tensor`): The data to be considered
        pdf (~pyhf.pdf.Model): The statistical model adhering to the schema model.json

    Returns:
        Tensor: Two times the negative log-likelihood, :math:`-2\ln L\left(\mu, \boldsymbol{\theta}\right)`
    """
    return -2 * pdf.logpdf(pars, data)


def _validate_fit_inputs(init_pars, par_bounds, fixed_params):
    for par_idx, (value, bound) in enumerate(zip(init_pars, par_bounds)):
        if not (bound[0] <= value <= bound[1]):
            raise ValueError(
                f"fit initialization parameter (index: {par_idx}, value: {value}) lies outside of its bounds: {bound}"
                + "\nTo correct this adjust the initialization parameter values in the model spec or those given"
                + "\nas arguments to pyhf.infer.fit. If this value is intended, adjust the range of the parameter"
                + "\nbounds."
            )


def fit(data, pdf, init_pars=None, par_bounds=None, fixed_params=None, **kwargs):
    r"""
    Run a maximum likelihood fit.
    This is done by minimizing the objective function :func:`~pyhf.infer.mle.twice_nll`
    of the model parameters given the observed data.
    This is used to produce the maximal likelihood :math:`L\left(\hat{\mu}, \hat{\boldsymbol{\theta}}\right)`
    in the profile likelihood ratio in Equation (7) in :xref:`arXiv:1007.1727`

    .. math::

       \lambda\left(\mu\right) = \frac{L\left(\mu, \hat{\hat{\boldsymbol{\theta}}}\right)}{L\left(\hat{\mu}, \hat{\boldsymbol{\theta}}\right)}


    .. note::

        :func:`twice_nll` is the objective function given to the optimizer and
        is returned evaluated at the best fit model parameters when the optional
        kwarg ``return_fitted_val`` is ``True``.

    Example:
        >>> import pyhf
        >>> pyhf.set_backend("numpy")
        >>> model = pyhf.simplemodels.uncorrelated_background(
        ...     signal=[12.0, 11.0], bkg=[50.0, 52.0], bkg_uncertainty=[3.0, 7.0]
        ... )
        >>> observations = [51, 48]
        >>> data = pyhf.tensorlib.astensor(observations + model.config.auxdata)
        >>> bestfit_pars, twice_nll = pyhf.infer.mle.fit(data, model, return_fitted_val=True)
        >>> bestfit_pars
        array([0.        , 1.0030512 , 0.96266961])
        >>> twice_nll
        array(24.98393521)
        >>> -2 * model.logpdf(bestfit_pars, data) == twice_nll
        array([ True])

    Args:
        data (:obj:`tensor`): The data
        pdf (~pyhf.pdf.Model): The statistical model adhering to the schema model.json
        init_pars (:obj:`list` of :obj:`float`): The starting values of the model parameters for minimization.
        par_bounds (:obj:`list` of :obj:`list`/:obj:`tuple`): The extrema of values the model parameters
            are allowed to reach in the fit.
            The shape should be ``(n, 2)`` for ``n`` model parameters.
        fixed_params (:obj:`tuple` or :obj:`list` of :obj:`bool`): The flag to set a parameter
            constant to its starting value during minimization.
        kwargs: Keyword arguments passed through to the optimizer API

    Returns:
        See optimizer API

    """
    _, opt = get_backend()
    init_pars = init_pars or pdf.config.suggested_init()
    par_bounds = par_bounds or pdf.config.suggested_bounds()
    fixed_params = fixed_params or pdf.config.suggested_fixed()

    _validate_fit_inputs(init_pars, par_bounds, fixed_params)

    # get fixed vals from the model
    fixed_vals = [
        (index, init)
        for index, (init, is_fixed) in enumerate(zip(init_pars, fixed_params))
        if is_fixed
    ]

    return opt.minimize(
        twice_nll, data, pdf, init_pars, par_bounds, fixed_vals, **kwargs
    )


def fixed_poi_fit(
    poi_val, data, pdf, init_pars=None, par_bounds=None, fixed_params=None, **kwargs
):
    r"""
    Run a maximum likelihood fit with the POI value fixed.
    This is done by minimizing the objective function of :func:`~pyhf.infer.mle.twice_nll`
    of the model parameters given the observed data, for a given fixed value of :math:`\mu`.
    This is used to produce the constrained maximal likelihood for the given :math:`\mu`,
    :math:`L\left(\mu, \hat{\hat{\boldsymbol{\theta}}}\right)`, in the profile
    likelihood ratio in Equation (7) in :xref:`arXiv:1007.1727`

    .. math::

       \lambda\left(\mu\right) = \frac{L\left(\mu, \hat{\hat{\boldsymbol{\theta}}}\right)}{L\left(\hat{\mu}, \hat{\boldsymbol{\theta}}\right)}

    .. note::

        :func:`twice_nll` is the objective function given to the optimizer and
        is returned evaluated at the best fit model parameters when the optional
        kwarg ``return_fitted_val`` is ``True``.

    Example:
        >>> import pyhf
        >>> pyhf.set_backend("numpy")
        >>> model = pyhf.simplemodels.uncorrelated_background(
        ...     signal=[12.0, 11.0], bkg=[50.0, 52.0], bkg_uncertainty=[3.0, 7.0]
        ... )
        >>> observations = [51, 48]
        >>> data = pyhf.tensorlib.astensor(observations + model.config.auxdata)
        >>> test_poi = 1.0
        >>> bestfit_pars, twice_nll = pyhf.infer.mle.fixed_poi_fit(
        ...     test_poi, data, model, return_fitted_val=True
        ... )
        >>> bestfit_pars
        array([1.        , 0.97224597, 0.87553894])
        >>> twice_nll
        array(28.92218013)
        >>> -2 * model.logpdf(bestfit_pars, data) == twice_nll
        array([ True])

    Args:
        data: The data
        pdf (~pyhf.pdf.Model): The statistical model adhering to the schema model.json
        init_pars (:obj:`list` of :obj:`float`): The starting values of the model parameters for minimization.
        par_bounds (:obj:`list` of :obj:`list`/:obj:`tuple`): The extrema of values the model parameters
            are allowed to reach in the fit.
            The shape should be ``(n, 2)`` for ``n`` model parameters.
        fixed_params (:obj:`tuple` or :obj:`list` of :obj:`bool`): The flag to set a parameter
            constant to its starting value during minimization.
        kwargs: Keyword arguments passed through to the optimizer API

    Returns:
        See optimizer API

    """
    if pdf.config.poi_index is None:
        raise UnspecifiedPOI(
            'No POI is defined. A POI is required to fit with a fixed POI.'
        )

    init_pars = [*(init_pars or pdf.config.suggested_init())]
    fixed_params = [*(fixed_params or pdf.config.suggested_fixed())]

    init_pars[pdf.config.poi_index] = poi_val
    fixed_params[pdf.config.poi_index] = True

    return fit(data, pdf, init_pars, par_bounds, fixed_params, **kwargs)

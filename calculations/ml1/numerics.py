"""Validated interpolation/regression primitives for digitized ML1 input data."""
import bisect
import math

from .validation import finite, finite_result


def pairs(values, label='Tabela'):
    if not isinstance(values, list) or len(values) < 2:
        raise ValueError(f'{label}: podaj co najmniej dwa punkty.')
    data = sorted((finite(x, label), finite(y, label)) for x, y in values)
    if any(a[0] == b[0] for a, b in zip(data, data[1:])):
        raise ValueError(f'{label}: współrzędne niezależne punktów muszą być różne.')
    return data


def interpolate(data, x, *, extrapolate=False):
    """Linear interpolation; data must be validated/sorted using pairs()."""
    x = finite(x, 'Argument interpolacji')
    if not extrapolate and not data[0][0] <= x <= data[-1][0]:
        raise ValueError(f'Argument {x:g} jest poza zakresem danych {data[0][0]:g}–{data[-1][0]:g}.')
    index = min(len(data)-2, max(0, bisect.bisect_right(data, (x, math.inf))-1))
    x0, y0 = data[index]
    x1, y1 = data[index+1]
    result = y0+(y1-y0)*(x-x0)/(x1-x0)
    finite_result(result)
    return result


def linear_fit(values):
    data = pairs(values, 'Aproksymacja liniowa')
    n = len(data)
    mean_x = math.fsum(x for x, _ in data)/n
    mean_y = math.fsum(y for _, y in data)/n
    sxx = math.fsum((x-mean_x)**2 for x, _ in data)
    sxy = math.fsum((x-mean_x)*(y-mean_y) for x, y in data)
    if sxx <= 0:
        raise ValueError('Aproksymacja liniowa wymaga różnych argumentów.')
    slope = sxy/sxx
    intercept = mean_y-slope*mean_x
    residual = math.fsum((y-slope*x-intercept)**2 for x, y in data)
    total = math.fsum((y-mean_y)**2 for _, y in data)
    finite_result(slope, intercept, residual, total)
    return dict(slope=slope, intercept=intercept, count=n, sum_squared_residuals=residual,
                r_squared=1-residual/total if total > 0 else (1. if residual == 0 else None))


def bracketed_root(function, low, high, *, relative_tolerance=1e-11, max_iterations=100):
    """Bisection of a bracketed physical intersection, preserving endpoint roots."""
    fl, fh = function(low), function(high)
    finite_result(fl, fh)
    if fl == 0:
        return low
    if fh == 0:
        return high
    if (fl > 0) == (fh > 0):
        raise ValueError('Brak zmiany znaku w przedziale poszukiwania rozwiązania.')
    for _ in range(max_iterations):
        middle = low+(high-low)/2
        fm = function(middle)
        finite_result(fm)
        if fm == 0 or high-low <= relative_tolerance*max(1., abs(middle)):
            return middle
        if (fm > 0) == (fl > 0):
            low, fl = middle, fm
        else:
            high, fh = middle, fm
    raise ValueError('Nie osiągnięto wymaganej dokładności rozwiązania numerycznego.')

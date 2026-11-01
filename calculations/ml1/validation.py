"""Strict numerical/data validation shared by the ML1 method implementations."""
import math


def finite(value, label, *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError(f'{label}: podaj skończoną liczbę.')
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'{label}: podaj skończoną liczbę.') from None
    if not math.isfinite(number):
        raise ValueError(f'{label}: podaj skończoną liczbę.')
    if positive and number <= 0:
        raise ValueError(f'{label}: wartość musi być dodatnia.')
    if nonnegative and number < 0:
        raise ValueError(f'{label}: wartość nie może być ujemna.')
    return number


def finite_result(*values):
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Dane prowadzą do wyniku poza skończonym zakresem obliczeń ML1.')

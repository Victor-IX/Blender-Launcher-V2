import os
from contextlib import contextmanager

from modules.settings import get_dpi_scale_factor

# https://doc.qt.io/qt-6/portingguide.html#high-dpi
# While Qt 5 supported an option called High DPI Scaling, Qt6 does not. this is now the default behavior.
# In its place, we can use a feature called QT_SCALE_FACTOR exposed by an environment variable.

DPI_OVERRIDDEN = "QT_SCALE_FACTOR" in os.environ


@contextmanager
def apply_scale_factor():
    if not DPI_OVERRIDDEN:
        os.environ["QT_SCALE_FACTOR"] = f"{get_dpi_scale_factor():.4f}"
        yield
        del os.environ["QT_SCALE_FACTOR"]
    else:
        yield

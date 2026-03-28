import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger()

_T = TypeVar("_T")

_DEFAULT_MAX_RETRIES = 10
_DEFAULT_RETRY_DELAY = 0.5


def retry_on_permission_error(
    func: Callable[..., _T],
    *args,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY,
    **kwargs,
) -> _T:
    """Call *func* with *args*/*kwargs*, retrying on :exc:`PermissionError`.

    This is intended for file-system operations (copy, rename, …) that may
    fail on Windows when antivirus software or another process holds a lock
    on the target file.

    :param func: The callable to invoke.
    :param max_retries: Maximum number of attempts before re-raising.
    :param retry_delay: Seconds to wait between attempts.
    :raises PermissionError: After *max_retries* unsuccessful attempts.
    """
    last_error: PermissionError | None = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except PermissionError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt + 1 < max_retries:
                time.sleep(retry_delay)

    logger.error(f"All {max_retries} attempts failed: {last_error}")
    raise last_error  # type: ignore

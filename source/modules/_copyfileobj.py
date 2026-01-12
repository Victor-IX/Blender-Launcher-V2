import os

# pulled from `shutil` but with callback options

# `shutil` does not expose this variable
# NOTICE: it's 256 * 1024 in 3.14 but is 64 * 1024 in 3.11
COPY_BUFSIZE = 1024 * 1024 if os.name == "nt" else 256 * 1024


def copyfileobj(fsrc, fdst, callback, length=0):
    """
    Inject support for a callback function to report
    each time another block has copied
    For more info check https://stackoverflow.com/a/29967714
    """

    try:
        # Check for optimization opportunity
        if "b" in fsrc.mode and "b" in fdst.mode and fsrc.readinto:
            _copyfileobj_readinto(fsrc, fdst, callback, length)
    except AttributeError:
        # One or both file objects do not
        # support a .mode or .readinto attribute
        pass

    if not length:
        length = COPY_BUFSIZE

    # Localize variable access to minimize overhead.
    fsrc_read = fsrc.read
    fdst_write = fdst.write

    copied = 0
    while buf := fsrc_read(length):
        fdst_write(buf)
        copied += len(buf)
        callback(copied)



def _copyfileobj_readinto(fsrc, fdst, callback, length=0):
    """readinto()/memoryview() based variant of copyfileobj().
    *fsrc* must support readinto() method and both files must be
    open in binary mode.
    """
    fsrc_readinto = fsrc.readinto
    fdst_write = fdst.write

    if not length:
        try:
            file_size = os.stat(fsrc.fileno()).st_size
        except OSError:
            file_size = COPY_BUFSIZE
        length = min(file_size, COPY_BUFSIZE)

    copied = 0
    with memoryview(bytearray(length)) as mv:
        while True:
            n = fsrc_readinto(mv)
            if not n:
                break

            if n < length:
                with mv[:n] as smv:
                    fdst_write(smv)

                callback(copied + n)
                break

            fdst_write(mv)
            copied += n
            callback(copied)

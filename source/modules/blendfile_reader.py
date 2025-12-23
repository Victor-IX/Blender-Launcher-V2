from __future__ import annotations

import contextlib
import gzip
import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import zstandard
from semver import Version

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger()

# Grabbed from https://projects.blender.org/blender/blender/src/branch/main/source/blender/blenloader_core/BLO_core_blend_header.hh
# https://projects.blender.org/blender/blender/src/branch/main/source/blender/blenloader_core/intern/blo_core_blend_header.cc

# Low level version 0: the header is 12 bytes long.
# 0-6:  'BLENDER'
# 7:    '-' for 8-byte pointers (#SmallBHead8) or '_' for 4-byte pointers (#BHead4)
# 8:    'v' for little endian or 'V' for big endian
# 9-11: 3 ASCII digits encoding #BLENDER_FILE_VERSION (e.g. '305' for Blender 3.5)
BLEND_FILE_FORMAT_VERSION_0 = re.compile(rb"BLENDER[-_][vV](\d)(\d)(\d)")
#
# Lower level version 1: the header is 17 bytes long.
# 0-6:   'BLENDER'
# 7-8:   size of the header in bytes encoded as ASCII digits (always '17' currently)
# 9:     always '-'
# 10-11: File version format as ASCII digits (always '01' currently)
# 12:    always 'v'
# 13-16: 4 ASCII digits encoding #BLENDER_FILE_VERSION (e.g. '0405' for Blender 4.5)
#
# With this header, #LargeBHead8 is always used.
BLEND_FILE_FORMAT_VERSION_1 = re.compile(rb"BLENDER\d{2}-\d{2}v(\d{2})(\d{2})")

# ! **as of now, we need to change this every time the header format size goes past our read limit**
BYTE_READ_LIMIT = 20


# See https://docs.blender.org/manual/en/latest/files/blend/open_save.html#id8
class CompressionType(Enum):
    NONE = "NONE"  # used universally
    ZSTD = "ZSTD"  # used for >=3.0
    GZIP = "GZIP"  # used for < 3.0


@dataclass
class BlendfileHeader:
    version: Version
    format_version: int
    compression_type: CompressionType


def parse_header_version(header: bytes) -> tuple[Version, int]:
    # Try version 1
    if match := BLEND_FILE_FORMAT_VERSION_1.match(header):
        major = int(match.group(1))
        minor = int(match.group(2))

        return (Version(major, minor, patch=0), 1)

    # Try version 0
    version = [x - ord("0") for x in header[9:12:]]
    major = version[0]
    minor = version[1] * 10 + version[2]

    return (Version(major, minor, patch=0), 0)


def __try_read_basic(pth: Path) -> bytes | None:
    """Tries to read the file header from an uncompressed file, returning None upon failure"""
    with pth.open("rb") as handle, contextlib.suppress(UnicodeDecodeError):
        if handle.read(7).decode() in {"BLENDER", "BULLETf"}:
            handle.seek(0, os.SEEK_SET)
            return handle.read(BYTE_READ_LIMIT)
    return None


def __try_read_gzip(pth: Path) -> bytes | None:
    """Tries to read the file header from a gzip file, returning None upon failure"""
    with gzip.open(pth, "rb") as fs, contextlib.suppress(gzip.BadGzipFile):
        return fs.read(BYTE_READ_LIMIT)
    return None


def __try_read_zstd(pth: Path) -> bytes | None:
    """Tries to read the file header from a zstandard file, returning None upon failure"""
    with zstandard.open(pth, "rb") as fs, contextlib.suppress(zstandard.ZstdError):
        return fs.read(BYTE_READ_LIMIT)
    return None


def get_blendfile_header(pth: Path) -> tuple[bytes, CompressionType] | None:
    header = __try_read_basic(pth)
    if header is not None:
        logger.debug("no compression detected, assuming none")
        return header, CompressionType.NONE

    if header is None:
        header = __try_read_gzip(pth)
        if header is not None:
            logger.debug("gzip blendfile detected")
            return header, CompressionType.GZIP

    if header is None:
        header = __try_read_zstd(pth)
        if header is not None:
            logger.debug("zstd blendfile detected")
            return header, CompressionType.ZSTD

    return None


def read_blendfile_header(pth: Path) -> BlendfileHeader | None:
    header = get_blendfile_header(pth)
    if header is None:
        raise Exception("Could not decode blendfile header")

    header, compression_type = header
    logger.debug(f"HEADER: {header}")
    version, file_ver = parse_header_version(header)

    return BlendfileHeader(version, file_ver, compression_type=compression_type)


if __name__ == "__main__":
    from pathlib import Path

    logging.basicConfig(level=logging.DEBUG)

    # Test .blender file Path
    pth = Path("Untitled.blend")
    blend_header = read_blendfile_header(pth)
    print(blend_header)

from __future__ import annotations

import contextlib
import gzip
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import zstandard
from semver import Version

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger()


# See https://docs.blender.org/manual/en/latest/files/blend/open_save.html#id8
class CompressionType(Enum):
    NONE = "NONE"  # used universally
    ZSTD = "ZSTD"  # used for >=3.0
    GZIP = "GZIP"  # used for < 3.0


@dataclass
class BlendfileHeader:
    version: Version
    compression_type: CompressionType


def parse_header_version(header: bytes):
    version = [x - ord("0") for x in header[9::]]

    return Version(
        major=version[0],
        minor=version[1] * 10 + version[2],
        patch=0,
    )


def __try_read_basic(pth: Path) -> bytes | None:
    """Tries to read the file header from an uncompressed file, returning None upon failure"""
    with pth.open("rb") as handle, contextlib.suppress(UnicodeDecodeError):
        if handle.read(7).decode() in {"BLENDER", "BULLETf"}:
            handle.seek(0, os.SEEK_SET)
            return handle.read(12)
    return None


def __try_read_gzip(pth: Path) -> bytes | None:
    """Tries to read the file header from a gzip file, returning None upon failure"""
    with gzip.open(pth, "rb") as fs, contextlib.suppress(gzip.BadGzipFile):
        return fs.read(12)
    return None


def __try_read_zstd(pth: Path) -> bytes | None:
    """Tries to read the file header from a zstandard file, returning None upon failure"""
    with zstandard.open(pth, "rb") as fs, contextlib.suppress(zstandard.ZstdError):
        return fs.read(12)
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
    version = parse_header_version(header)

    return BlendfileHeader(version, compression_type=compression_type)

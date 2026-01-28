import tempfile
from pathlib import Path

from modules.blendfile_reader import (
    BlendfileHeader,
    CompressionType,
    parse_header_version,
    read_blendfile_header,
)
from semver import Version

# This is inaccurate to a normal scenario but they should scale properly
v0_BASIC = b"BLENDER-v404"
v0_ZSTD = b"(\xb5/\xfd \x0ca\x00\x00BLENDER-v404"
v0_GZIP = b"\x1f\x8b\x08\x00]nwg\x02\xffs\xf2q\xf5sq\r\xd2-310\x01\x00\x93\xd4+E\x0c\x00\x00\x00"

v1_BASIC = b"BLENDER17-01v0501REND"
# I dont know why the ZSTD version here needs to be so long but it doesn't work unless this much of the file has been read
v1_ZSTD = (
    b"(\xb5/\xfd\xa0A\x06\x01\x00\xed\x06\x00\x84\nBLENDER17-01v0501REND\x00\x00\x00"
    b"\x00\x10\x00\x08\x01\x00\xfa\x00\x00\x00Scene\x00TEST\x00\x00\x00\x00\xe0\x92"
    b"\xb7MV\x93\xc5{\x08\x80\x00GLOB\xaa\xc0\x04  21\x15\x00\x95\x01U\x00\x00@\xf7"
    b"\xd0\x10\x8e\x86B\x1e\xd0f\x07o\xb0V|/\xf0\x02\x10\x00\x02\x00\x04\x00\x002"
    b"\x0cxi3d645e0efbecLinear Rec.709\xe5$\xd3>\x0f\xbeY>\xab[\x9e<[\x15\xb7R\x157?"
    b">Q\x1c\xf4=\x13\xd08>\xc9\xd9\x93=\x18Vs?\x12\x00\x04\xdc3\x88T\x00\xe0\x13`\x99"
    b"\x04\xa0\x1f8\x06\xa0]\xc8)H \xdbT\x80\x8e\x1f\xff\x1fh\xd9\xdd\xad,\x0c;\x96\xb0"
    b"\xee8\xc2\x95\x06*\x0e\x001\x1e\xc0\x18"
)


def test_header_parser_version_0():
    assert parse_header_version(v0_BASIC) == (Version(4, 4, 0), 0)
    with tempfile.TemporaryDirectory() as tmpdir_:
        tmpdir = Path(tmpdir_)
        gb = tmpdir / "gzip.blend"
        zb = tmpdir / "zstd.blend"
        with gb.open("wb") as g, zb.open("wb") as z:
            g.write(v0_GZIP)
            z.write(v0_ZSTD)

        assert read_blendfile_header(gb) == BlendfileHeader(Version(4, 4, 0), 0, CompressionType.GZIP)
        assert read_blendfile_header(zb) == BlendfileHeader(Version(4, 4, 0), 0, CompressionType.ZSTD)


def test_header_parser_version_1():
    # assert parse_header_version(v1_BASIC) == (Version(5, 1, 0), 1)
    with tempfile.TemporaryDirectory() as tmpdir_:
        tmpdir = Path(tmpdir_)
        zb = tmpdir / "zstd.blend"
        with zb.open("wb") as z:
            z.write(v1_ZSTD)

        assert read_blendfile_header(zb) == BlendfileHeader(Version(5, 1, 0), 1, CompressionType.ZSTD)

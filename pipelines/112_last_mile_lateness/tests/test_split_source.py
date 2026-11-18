import io

import ijson
import pytest

from lastmile.split_source import NaNToNull


class Trickle:
    """Returns at most `size` bytes per read so tokens get split across reads.
    No readinto on purpose, ijson prefers readinto and would skip read()."""

    def __init__(self, data, size):
        self.buf = io.BytesIO(data)
        self.size = size

    def read(self, n=-1):
        if n == 0:  # ijson probes with read(0) to see if it's a bytes stream
            return b""
        return self.buf.read(self.size)


DOC = (b'{"r1": {"tw": {"start": NaN, "end": NaN}, "x": 1.5}, '
       b'"r2": {"tw": {"start": "2018-07-27 16:00:00", "end": NaN}}}')


@pytest.mark.parametrize("size", [1, 2, 3, 4, 7, 64])
def test_nan_split_across_reads(size):
    items = dict(ijson.kvitems(NaNToNull(Trickle(DOC, size)), "", use_float=True))
    assert items["r1"]["tw"] == {"start": None, "end": None}
    assert items["r2"]["tw"]["end"] is None
    assert items["r1"]["x"] == 1.5


def test_strings_left_alone():
    doc = b'{"a": "NaNa", "b": NaN}'
    items = dict(ijson.kvitems(NaNToNull(io.BytesIO(doc)), ""))
    # known limitation, the wrapper is not string aware. Fine for this source
    # (ids are hex uuids) but worth a test so nobody is surprised.
    assert items["a"] == "nulla"
    assert items["b"] is None

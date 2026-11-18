import json

import pytest
from botocore.exceptions import ClientError

from lastmile.handler import DropRejected, validate_drop


class FakeS3:
    exceptions = type("E", (), {"ClientError": ClientError})

    def __init__(self, objects):
        self.objects = objects

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {"ContentLength": len(self.objects[Key])}


def drop(manifest_date="2018-07-27", sizes=None, skip=()):
    files = {"routes.jsonl": b"r\n", "packages.jsonl": b"pp\n", "sequences.jsonl": b"s\n",
             "travel_times.jsonl": b"tt\n"}
    sizes = sizes or {}
    prefix = "almrrc/dt=2018-07-27"
    objs = {f"{prefix}/{k}": v for k, v in files.items() if k not in skip}
    manifest = {"run_date": manifest_date, "files": [
        {"table": k.split(".")[0], "key": k, "rows": 1, "bytes": sizes.get(k, len(v))} for k, v in files.items()]}
    objs[f"{prefix}/_manifest.json"] = json.dumps(manifest).encode()
    return FakeS3(objs), f"{prefix}/_manifest.json"


def test_good_drop():
    s3, key = drop()
    assert validate_drop(s3, "b", key)["run_date"] == "2018-07-27"


def test_missing_file_rejected():
    s3, key = drop(skip=("travel_times.jsonl",))
    with pytest.raises(DropRejected, match="travel_times.jsonl missing"):
        validate_drop(s3, "b", key)


def test_truncated_upload_rejected():
    s3, key = drop(sizes={"packages.jsonl": 999})
    with pytest.raises(DropRejected, match="packages.jsonl is 3 bytes"):
        validate_drop(s3, "b", key)


def test_manifest_date_mismatch():
    s3, key = drop(manifest_date="2018-07-28")
    with pytest.raises(DropRejected, match="path says"):
        validate_drop(s3, "b", key)

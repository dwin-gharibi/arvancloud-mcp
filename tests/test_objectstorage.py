"""Tests for the Object Storage (S3) tools.

ArvanCloud's S3 endpoint is custom, so moto can't intercept it cleanly; instead
we inject a fake boto3 client and assert the wrapper calls the right S3
operations with the right arguments and maps results correctly.
"""

from __future__ import annotations

import base64
import datetime as dt
from unittest.mock import MagicMock

import boto3
import pytest

from arvancloud_mcp.client import ArvanClient
from arvancloud_mcp.server import build_server
from arvancloud_mcp.tools.objectstorage import _S3Holder

from .conftest import make_settings, unwrap

_NOW = dt.datetime(2026, 5, 29, 12, 0, 0)


def _fake_s3() -> MagicMock:
    s3 = MagicMock()
    s3.list_buckets.return_value = {"Buckets": [{"Name": "b1", "CreationDate": _NOW}]}
    s3.create_bucket.return_value = {}
    s3.delete_bucket.return_value = {}
    s3.put_object.return_value = {"ETag": '"etag123"'}
    body = MagicMock()
    body.read.return_value = b"hello world"
    s3.get_object.return_value = {"Body": body, "ContentType": "text/plain"}
    s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "a.txt", "Size": 11, "LastModified": _NOW, "ETag": '"e"'}],
        "IsTruncated": False,
    }
    s3.head_object.return_value = {
        "ContentLength": 11,
        "ContentType": "text/plain",
        "ETag": '"e"',
        "LastModified": _NOW,
    }
    s3.generate_presigned_url.return_value = "https://s3.example/presigned?sig=x"
    s3.delete_object.return_value = {}
    return s3


@pytest.fixture
def s3_server(monkeypatch):
    fake = _fake_s3()
    monkeypatch.setattr(boto3, "client", lambda *a, **k: fake)
    mcp, _client = build_server(
        make_settings(s3_access_key="ak", s3_secret_key="sk", s3_region="ir-thr-at1")
    )
    return mcp, fake


def test_holder_requires_credentials():
    holder = _S3Holder(ArvanClient(make_settings(s3_access_key="", s3_secret_key="")))
    with pytest.raises(RuntimeError) as excinfo:
        holder.get()
    assert "ARVAN_S3" in str(excinfo.value) or "not configured" in str(excinfo.value)


def test_endpoint_url_derives_from_region():
    s = make_settings(s3_region="ir-tbz-sh1")
    assert s.s3_endpoint_url() == "https://s3.ir-tbz-sh1.arvanstorage.ir"
    s2 = make_settings(s3_endpoint="https://custom.example/")
    assert s2.s3_endpoint_url() == "https://custom.example"


async def test_list_buckets(s3_server):
    mcp, fake = s3_server
    out = unwrap(await mcp.call_tool("arvan_s3_list_buckets", {}))
    buckets = out["buckets"]
    assert buckets[0]["name"] == "b1"
    assert buckets[0]["created_at"] == _NOW.isoformat()
    fake.list_buckets.assert_called_once()


async def test_create_bucket_passes_acl(s3_server):
    mcp, fake = s3_server
    await mcp.call_tool(
        "arvan_s3_create_bucket", {"bucket": "b1", "acl": "public-read"}
    )
    fake.create_bucket.assert_called_once_with(Bucket="b1", ACL="public-read")


async def test_put_object_text(s3_server):
    mcp, fake = s3_server
    out = unwrap(
        await mcp.call_tool(
            "arvan_s3_put_object",
            {"bucket": "b1", "key": "a.txt", "content": "hi", "content_type": "text/plain"},
        )
    )
    assert out["etag"] == '"etag123"'
    kwargs = fake.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "b1" and kwargs["Key"] == "a.txt"
    assert kwargs["Body"] == b"hi"
    assert kwargs["ContentType"] == "text/plain"


async def test_put_object_base64(s3_server):
    mcp, fake = s3_server
    payload = base64.b64encode(b"\x00\x01\x02").decode()
    await mcp.call_tool(
        "arvan_s3_put_object",
        {"bucket": "b1", "key": "bin", "content": payload, "content_base64": True},
    )
    assert fake.put_object.call_args.kwargs["Body"] == b"\x00\x01\x02"


async def test_get_object_text(s3_server):
    mcp, fake = s3_server
    out = unwrap(
        await mcp.call_tool("arvan_s3_get_object", {"bucket": "b1", "key": "a.txt"})
    )
    assert out["content"] == "hello world"
    assert out["truncated"] is False
    fake.get_object.assert_called_once_with(Bucket="b1", Key="a.txt")


async def test_get_object_binary_falls_back_to_base64(s3_server):
    mcp, fake = s3_server
    fake.get_object.return_value["Body"].read.return_value = b"\xff\xfe\x00"
    out = unwrap(
        await mcp.call_tool(
            "arvan_s3_get_object", {"bucket": "b1", "key": "x", "as_base64": True}
        )
    )
    assert base64.b64decode(out["content_base64"]) == b"\xff\xfe\x00"


async def test_list_objects(s3_server):
    mcp, fake = s3_server
    out = unwrap(
        await mcp.call_tool(
            "arvan_s3_list_objects", {"bucket": "b1", "prefix": "a"}
        )
    )
    assert out["objects"][0]["key"] == "a.txt"
    assert fake.list_objects_v2.call_args.kwargs["Prefix"] == "a"


async def test_presigned_url(s3_server):
    mcp, fake = s3_server
    out = unwrap(
        await mcp.call_tool(
            "arvan_s3_generate_presigned_url",
            {"bucket": "b1", "key": "a.txt", "expires_in": 120},
        )
    )
    assert out["url"].startswith("https://")
    assert out["expires_in"] == 120
    assert fake.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 120


async def test_sync_local_dir(s3_server, tmp_path):
    mcp, fake = s3_server
    (tmp_path / "a.txt").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("y")
    out = unwrap(
        await mcp.call_tool(
            "arvan_s3_sync_local_dir", {"bucket": "b1", "local_dir": str(tmp_path)}
        )
    )
    assert out["uploaded"] == 2
    assert fake.put_object.call_count >= 2


async def test_enable_static_website(s3_server):
    mcp, fake = s3_server
    out = unwrap(
        await mcp.call_tool("arvan_s3_enable_static_website", {"bucket": "b1"})
    )
    assert "website_endpoint" in out
    fake.put_bucket_website.assert_called_once()

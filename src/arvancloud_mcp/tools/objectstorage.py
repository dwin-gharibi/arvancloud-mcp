"""Object Storage tools (S3-compatible) — ``https://s3.<region>.arvanstorage.ir``.

ArvanCloud Object Storage speaks the S3 API and uses its own access/secret key
pair (separate from the machine-user API key). These tools wrap boto3; the
blocking calls run in a thread so they don't stall the async server.

Configure with ``ARVAN_S3_ACCESS_KEY``, ``ARVAN_S3_SECRET_KEY`` and either
``ARVAN_S3_REGION`` (e.g. ``ir-thr-at1``) or an explicit ``ARVAN_S3_ENDPOINT``.
"""

from __future__ import annotations

import asyncio
import base64
import json as _json
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient

_MAX_INLINE_BYTES = 256 * 1024


class _S3Holder:
    """Lazily builds and caches a boto3 S3 client from the server settings."""

    def __init__(self, client: ArvanClient) -> None:
        self._settings = client.settings
        self._s3: Any = None

    def get(self) -> Any:
        if self._s3 is not None:
            return self._s3
        if not (self._settings.s3_access_key and self._settings.s3_secret_key):
            raise RuntimeError(
                "Object Storage is not configured. Set ARVAN_S3_ACCESS_KEY and "
                "ARVAN_S3_SECRET_KEY (and ARVAN_S3_REGION or ARVAN_S3_ENDPOINT). "
                "Find these in the ArvanCloud Object Storage dashboard."
            )
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for Object Storage tools: pip install boto3"
            ) from exc

        self._s3 = boto3.client(
            "s3",
            endpoint_url=self._settings.s3_endpoint_url(),
            aws_access_key_id=self._settings.s3_access_key,
            aws_secret_access_key=self._settings.s3_secret_key,
            region_name=self._settings.s3_region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )
        return self._s3


def _run(fn, *args, **kwargs):
    """Execute a blocking boto3 call in a worker thread, mapping errors."""

    async def _call() -> Any:
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as exc:
            from botocore.exceptions import ClientError

            if isinstance(exc, ClientError):
                err = exc.response.get("Error", {})
                raise RuntimeError(
                    f"S3 error {err.get('Code', '?')}: {err.get('Message', exc)}"
                ) from exc
            raise

    return _call()


def register(mcp: FastMCP, client: ArvanClient) -> None:
    holder = _S3Holder(client)

    @mcp.tool()
    async def arvan_s3_list_buckets() -> Any:
        """List all Object Storage buckets."""

        s3 = holder.get()
        resp = await _run(s3.list_buckets)
        return {
            "buckets": [
                {"name": b["Name"], "created_at": b["CreationDate"].isoformat()}
                for b in resp.get("Buckets", [])
            ]
        }

    @mcp.tool()
    async def arvan_s3_create_bucket(
        bucket: str, acl: str = "private"
    ) -> Any:
        """Create a bucket. ``acl`` is one of private, public-read, public-read-write."""

        s3 = holder.get()
        await _run(s3.create_bucket, Bucket=bucket, ACL=acl)
        return {"bucket": bucket, "acl": acl, "created": True}

    @mcp.tool()
    async def arvan_s3_delete_bucket(bucket: str) -> Any:
        """Delete an (empty) bucket."""

        s3 = holder.get()
        await _run(s3.delete_bucket, Bucket=bucket)
        return {"bucket": bucket, "deleted": True}

    @mcp.tool()
    async def arvan_s3_list_objects(
        bucket: str,
        prefix: str | None = None,
        max_keys: int = 1000,
        continuation_token: str | None = None,
    ) -> Any:
        """List objects in a bucket (optionally under a prefix)."""

        s3 = holder.get()
        kwargs: dict[str, Any] = {"Bucket": bucket, "MaxKeys": max_keys}
        if prefix:
            kwargs["Prefix"] = prefix
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        resp = await _run(s3.list_objects_v2, **kwargs)
        return {
            "objects": [
                {
                    "key": o["Key"],
                    "size": o["Size"],
                    "last_modified": o["LastModified"].isoformat(),
                    "etag": o.get("ETag"),
                }
                for o in resp.get("Contents", [])
            ],
            "is_truncated": resp.get("IsTruncated", False),
            "next_continuation_token": resp.get("NextContinuationToken"),
        }

    @mcp.tool()
    async def arvan_s3_put_object(
        bucket: str,
        key: str,
        content: str,
        content_base64: bool = False,
        content_type: str | None = None,
        acl: str | None = None,
    ) -> Any:
        """Upload an object.

        Args:
            bucket: Target bucket.
            key: Object key (path) within the bucket.
            content: The object body. Plain text, or base64 if ``content_base64``.
            content_base64: Set True when ``content`` is base64-encoded binary.
            content_type: Optional MIME type, e.g. ``application/json``.
            acl: Optional ACL, e.g. ``public-read``.
        """

        s3 = holder.get()
        body = base64.b64decode(content) if content_base64 else content.encode("utf-8")
        kwargs: dict[str, Any] = {"Bucket": bucket, "Key": key, "Body": body}
        if content_type:
            kwargs["ContentType"] = content_type
        if acl:
            kwargs["ACL"] = acl
        resp = await _run(s3.put_object, **kwargs)
        return {"bucket": bucket, "key": key, "etag": resp.get("ETag"), "size": len(body)}

    @mcp.tool()
    async def arvan_s3_get_object(
        bucket: str, key: str, as_base64: bool = False
    ) -> Any:
        """Download an object. Returns text, or base64 when ``as_base64`` or binary.

        Bodies larger than 256 KiB are truncated; use a presigned URL for big files.
        """

        s3 = holder.get()
        resp = await _run(s3.get_object, Bucket=bucket, Key=key)
        raw: bytes = await asyncio.to_thread(resp["Body"].read)
        truncated = len(raw) > _MAX_INLINE_BYTES
        raw = raw[:_MAX_INLINE_BYTES]
        out: dict[str, Any] = {
            "bucket": bucket,
            "key": key,
            "content_type": resp.get("ContentType"),
            "truncated": truncated,
        }
        if as_base64:
            out["content_base64"] = base64.b64encode(raw).decode("ascii")
        else:
            try:
                out["content"] = raw.decode("utf-8")
            except UnicodeDecodeError:
                out["content_base64"] = base64.b64encode(raw).decode("ascii")
                out["note"] = "binary content returned as base64"
        return out

    @mcp.tool()
    async def arvan_s3_delete_object(bucket: str, key: str) -> Any:
        """Delete a single object."""

        s3 = holder.get()
        await _run(s3.delete_object, Bucket=bucket, Key=key)
        return {"bucket": bucket, "key": key, "deleted": True}

    @mcp.tool()
    async def arvan_s3_delete_objects(bucket: str, keys: list[str]) -> Any:
        """Delete multiple objects in one call."""

        s3 = holder.get()
        resp = await _run(
            s3.delete_objects,
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in keys]},
        )
        return {"deleted": [d["Key"] for d in resp.get("Deleted", [])]}

    @mcp.tool()
    async def arvan_s3_copy_object(
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
    ) -> Any:
        """Copy an object to another key/bucket."""

        s3 = holder.get()
        await _run(
            s3.copy_object,
            Bucket=dest_bucket,
            Key=dest_key,
            CopySource={"Bucket": source_bucket, "Key": source_key},
        )
        return {"dest_bucket": dest_bucket, "dest_key": dest_key, "copied": True}

    @mcp.tool()
    async def arvan_s3_head_object(bucket: str, key: str) -> Any:
        """Get an object's metadata (size, type, etag) without downloading it."""

        s3 = holder.get()
        resp = await _run(s3.head_object, Bucket=bucket, Key=key)
        return {
            "bucket": bucket,
            "key": key,
            "size": resp.get("ContentLength"),
            "content_type": resp.get("ContentType"),
            "etag": resp.get("ETag"),
            "last_modified": resp["LastModified"].isoformat()
            if resp.get("LastModified")
            else None,
        }

    @mcp.tool()
    async def arvan_s3_generate_presigned_url(
        bucket: str,
        key: str,
        operation: str = "get_object",
        expires_in: int = 3600,
    ) -> Any:
        """Generate a presigned URL for temporary access to an object.

        ``operation`` is ``get_object`` (download) or ``put_object`` (upload).
        """

        s3 = holder.get()
        url = await _run(
            s3.generate_presigned_url,
            operation,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return {"url": url, "expires_in": expires_in, "operation": operation}

    @mcp.tool()
    async def arvan_s3_get_bucket_policy(bucket: str) -> Any:
        """Get a bucket's access policy (JSON)."""

        s3 = holder.get()
        resp = await _run(s3.get_bucket_policy, Bucket=bucket)
        try:
            return {"bucket": bucket, "policy": _json.loads(resp.get("Policy", "{}"))}
        except ValueError:
            return {"bucket": bucket, "policy": resp.get("Policy")}

    @mcp.tool()
    async def arvan_s3_put_bucket_policy(
        bucket: str, policy: dict[str, Any]
    ) -> Any:
        """Set a bucket's access policy (an S3 policy document)."""

        s3 = holder.get()
        await _run(s3.put_bucket_policy, Bucket=bucket, Policy=_json.dumps(policy))
        return {"bucket": bucket, "policy_set": True}

    @mcp.tool()
    async def arvan_s3_set_bucket_acl(bucket: str, acl: str) -> Any:
        """Set a bucket ACL (private, public-read, public-read-write)."""

        s3 = holder.get()
        await _run(s3.put_bucket_acl, Bucket=bucket, ACL=acl)
        return {"bucket": bucket, "acl": acl}

    @mcp.tool()
    async def arvan_s3_sync_local_dir(
        bucket: str,
        local_dir: str,
        prefix: str = "",
        acl: str | None = None,
    ) -> Any:
        """Upload all files under a local directory to a bucket (recursive)."""

        import mimetypes
        import os

        s3 = holder.get()

        def _walk() -> list[str]:
            files = []
            for root, _dirs, names in os.walk(local_dir):
                for fn in names:
                    files.append(os.path.join(root, fn))
            return files[:10000]

        paths = await asyncio.to_thread(_walk)
        uploaded = []
        for path in paths:
            rel = os.path.relpath(path, local_dir).replace(os.sep, "/")
            key = f"{prefix.rstrip('/')}/{rel}" if prefix else rel

            def _put(p=path, k=key) -> None:
                with open(p, "rb") as fh:
                    body = fh.read()
                ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
                kwargs = {"Bucket": bucket, "Key": k, "Body": body, "ContentType": ctype}
                if acl:
                    kwargs["ACL"] = acl
                s3.put_object(**kwargs)

            await _run(_put)
            uploaded.append(key)
        return {"bucket": bucket, "uploaded": len(uploaded), "keys": uploaded[:200]}

    @mcp.tool()
    async def arvan_s3_enable_static_website(
        bucket: str,
        index_document: str = "index.html",
        error_document: str = "error.html",
        make_public: bool = True,
    ) -> Any:
        """Configure a bucket for static website hosting (optionally make it public)."""

        s3 = holder.get()
        await _run(
            s3.put_bucket_website,
            Bucket=bucket,
            WebsiteConfiguration={
                "IndexDocument": {"Suffix": index_document},
                "ErrorDocument": {"Key": error_document},
            },
        )
        if make_public:
            await _run(s3.put_bucket_acl, Bucket=bucket, ACL="public-read")
        region = client.settings.s3_region
        return {
            "bucket": bucket,
            "index_document": index_document,
            "website_endpoint": f"https://{bucket}.s3.{region}.arvanstorage.ir/{index_document}",
            "public": make_public,
        }

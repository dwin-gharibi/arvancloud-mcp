"""Video on Demand (VOD) tools — ``/vod/2.0``."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import ArvanClient


def register(mcp: FastMCP, client: ArvanClient) -> None:
    @mcp.tool()
    async def arvan_vod_list_channels(
        page: int | None = None, per_page: int | None = None
    ) -> Any:
        """List VOD channels."""

        params = {k: v for k, v in {"page": page, "per_page": per_page}.items() if v}
        return await client.request("GET", "/vod/2.0/channels", params=params)

    @mcp.tool()
    async def arvan_vod_get_channel(channel_id: str) -> Any:
        """Get a VOD channel by id."""

        return await client.request("GET", f"/vod/2.0/channels/{channel_id}")

    @mcp.tool()
    async def arvan_vod_create_channel(
        title: str, description: str = "", extra: dict[str, Any] | None = None
    ) -> Any:
        """Create a VOD channel."""

        body: dict[str, Any] = {"title": title, "description": description}
        if extra:
            body.update(extra)
        return await client.request("POST", "/vod/2.0/channels", json=body)

    @mcp.tool()
    async def arvan_vod_update_channel(
        channel_id: str, fields: dict[str, Any]
    ) -> Any:
        """Update a VOD channel with the given fields."""

        return await client.request(
            "PATCH", f"/vod/2.0/channels/{channel_id}", json=fields
        )

    @mcp.tool()
    async def arvan_vod_delete_channel(channel_id: str) -> Any:
        """Delete a VOD channel by id."""

        return await client.request("DELETE", f"/vod/2.0/channels/{channel_id}")

    @mcp.tool()
    async def arvan_vod_list_videos(
        channel_id: str, page: int | None = None, per_page: int | None = None
    ) -> Any:
        """List videos in a channel."""

        params = {k: v for k, v in {"page": page, "per_page": per_page}.items() if v}
        return await client.request(
            "GET", f"/vod/2.0/channels/{channel_id}/videos", params=params
        )

    @mcp.tool()
    async def arvan_vod_get_video(video_id: str) -> Any:
        """Get a VOD video by id."""

        return await client.request("GET", f"/vod/2.0/videos/{video_id}")

    @mcp.tool()
    async def arvan_vod_create_video(
        channel_id: str, fields: dict[str, Any]
    ) -> Any:
        """Create a video in a channel.

        ``fields`` typically includes ``title``, ``description`` and a
        ``file_id`` previously obtained by uploading to the channel's files
        endpoint, plus optional ``convert_mode``, ``watermark_id`` etc.
        """

        return await client.request(
            "POST", f"/vod/2.0/channels/{channel_id}/videos", json=fields
        )

    @mcp.tool()
    async def arvan_vod_update_video(video_id: str, fields: dict[str, Any]) -> Any:
        """Update a VOD video with the given fields."""

        return await client.request(
            "PATCH", f"/vod/2.0/videos/{video_id}", json=fields
        )

    @mcp.tool()
    async def arvan_vod_delete_video(video_id: str) -> Any:
        """Delete a VOD video by id."""

        return await client.request("DELETE", f"/vod/2.0/videos/{video_id}")

    @mcp.tool()
    async def arvan_vod_list_audios(channel_id: str) -> Any:
        """List audio tracks in a channel."""

        return await client.request(
            "GET", f"/vod/2.0/channels/{channel_id}/audios"
        )

    @mcp.tool()
    async def arvan_vod_create_audio(
        channel_id: str, fields: dict[str, Any]
    ) -> Any:
        """Create an audio item in a channel."""

        return await client.request(
            "POST", f"/vod/2.0/channels/{channel_id}/audios", json=fields
        )

    @mcp.tool()
    async def arvan_vod_delete_audio(audio_id: str) -> Any:
        """Delete an audio item by id."""

        return await client.request("DELETE", f"/vod/2.0/audios/{audio_id}")

    @mcp.tool()
    async def arvan_vod_list_subtitles(video_id: str) -> Any:
        """List subtitles for a video."""

        return await client.request(
            "GET", f"/vod/2.0/videos/{video_id}/subtitles"
        )

    @mcp.tool()
    async def arvan_vod_create_subtitle(
        video_id: str, fields: dict[str, Any]
    ) -> Any:
        """Create a subtitle for a video (e.g. ``{"lang": "fa", "file_id": "..."}``)."""

        return await client.request(
            "POST", f"/vod/2.0/videos/{video_id}/subtitles", json=fields
        )

    @mcp.tool()
    async def arvan_vod_delete_subtitle(subtitle_id: str) -> Any:
        """Delete a subtitle by id."""

        return await client.request(
            "DELETE", f"/vod/2.0/subtitles/{subtitle_id}"
        )

    @mcp.tool()
    async def arvan_vod_get_audio(audio_id: str) -> Any:
        """Get an audio item by id."""

        return await client.request("GET", f"/vod/2.0/audios/{audio_id}")

    @mcp.tool()
    async def arvan_vod_update_audio(audio_id: str, fields: dict[str, Any]) -> Any:
        """Update an audio item with the given fields."""

        return await client.request(
            "PATCH", f"/vod/2.0/audios/{audio_id}", json=fields
        )

    @mcp.tool()
    async def arvan_vod_get_subtitle(subtitle_id: str) -> Any:
        """Get a subtitle by id."""

        return await client.request("GET", f"/vod/2.0/subtitles/{subtitle_id}")

    @mcp.tool()
    async def arvan_vod_get_file(file_id: str) -> Any:
        """Get an uploaded source file by id."""

        return await client.request("GET", f"/vod/2.0/files/{file_id}")

    @mcp.tool()
    async def arvan_vod_delete_file(file_id: str) -> Any:
        """Delete an uploaded source file by id."""

        return await client.request("DELETE", f"/vod/2.0/files/{file_id}")

    @mcp.tool()
    async def arvan_vod_list_files(channel_id: str) -> Any:
        """List uploaded source files in a channel."""

        return await client.request(
            "GET", f"/vod/2.0/channels/{channel_id}/files"
        )

    @mcp.tool()
    async def arvan_vod_list_watermarks(channel_id: str) -> Any:
        """List watermarks in a channel."""

        return await client.request(
            "GET", f"/vod/2.0/channels/{channel_id}/watermarks"
        )

    @mcp.tool()
    async def arvan_vod_get_watermark(watermark_id: str) -> Any:
        """Get a watermark by id."""

        return await client.request("GET", f"/vod/2.0/watermarks/{watermark_id}")

    @mcp.tool()
    async def arvan_vod_create_watermark(
        channel_id: str, fields: dict[str, Any]
    ) -> Any:
        """Create a watermark in a channel (e.g. ``{"title":..., "file_id":...}``)."""

        return await client.request(
            "POST", f"/vod/2.0/channels/{channel_id}/watermarks", json=fields
        )

    @mcp.tool()
    async def arvan_vod_update_watermark(
        watermark_id: str, fields: dict[str, Any]
    ) -> Any:
        """Update a watermark with the given fields."""

        return await client.request(
            "PATCH", f"/vod/2.0/watermarks/{watermark_id}", json=fields
        )

    @mcp.tool()
    async def arvan_vod_delete_watermark(watermark_id: str) -> Any:
        """Delete a watermark by id."""

        return await client.request(
            "DELETE", f"/vod/2.0/watermarks/{watermark_id}"
        )

    @mcp.tool()
    async def arvan_vod_list_profiles(channel_id: str) -> Any:
        """List encoding profiles in a channel."""

        return await client.request(
            "GET", f"/vod/2.0/channels/{channel_id}/profiles"
        )

    @mcp.tool()
    async def arvan_vod_get_profile(profile_id: str) -> Any:
        """Get an encoding profile by id."""

        return await client.request("GET", f"/vod/2.0/profiles/{profile_id}")

    @mcp.tool()
    async def arvan_vod_create_profile(
        channel_id: str, fields: dict[str, Any]
    ) -> Any:
        """Create an encoding profile in a channel."""

        return await client.request(
            "POST", f"/vod/2.0/channels/{channel_id}/profiles", json=fields
        )

    @mcp.tool()
    async def arvan_vod_update_profile(
        profile_id: str, fields: dict[str, Any]
    ) -> Any:
        """Update an encoding profile with the given fields."""

        return await client.request(
            "PATCH", f"/vod/2.0/profiles/{profile_id}", json=fields
        )

    @mcp.tool()
    async def arvan_vod_delete_profile(profile_id: str) -> Any:
        """Delete an encoding profile by id."""

        return await client.request("DELETE", f"/vod/2.0/profiles/{profile_id}")

    @mcp.tool()
    async def arvan_vod_get_domain() -> Any:
        """Get the VOD user domain (the delivery domain for this account)."""

        return await client.request("GET", "/vod/2.0/domain")

    @mcp.tool()
    async def arvan_vod_create_domain(fields: dict[str, Any]) -> Any:
        """Create/set the VOD user domain."""

        return await client.request("POST", "/vod/2.0/domain", json=fields)

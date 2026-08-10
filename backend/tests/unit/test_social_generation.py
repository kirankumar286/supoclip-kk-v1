import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ai import (
    generate_social_media_pack,
    SocialMediaPack,
    InstagramMetadata,
    TikTokMetadata,
    YouTubeMetadata,
    FacebookMetadata,
    SnapchatMetadata,
    PinterestMetadata,
    XThreadsMetadata
)


@pytest.mark.asyncio
async def test_generate_social_media_pack_empty():
    pack = await generate_social_media_pack("")
    assert pack.youtube.best_title == ""
    assert pack.tiktok.caption == ""


@pytest.mark.asyncio
async def test_generate_social_media_pack_with_content(monkeypatch):
    mock_agent = MagicMock()
    mock_result = MagicMock()
    
    mock_pack = SocialMediaPack(
        instagram=InstagramMetadata(
            hook_options=["Insta Title 1", "Insta Title 2"],
            best_cover_text="Insta Cover",
            caption="Insta Desc",
            hashtags=["insta", "reels"],
            keywords=["insta"],
            cta="Watch now"
        ),
        tiktok=TikTokMetadata(
            hook_options=["TikTok Title 1", "TikTok Title 2"],
            caption="TikTok Desc",
            hashtags=["tiktok", "viral"],
            keywords=["tiktok"],
            cta="Follow for more"
        ),
        youtube=YouTubeMetadata(
            title_options=["YouTube Title 1", "YouTube Title 2"],
            best_title="YouTube Best Title",
            description="YouTube Desc",
            hashtags=["yt", "shorts"],
            keywords=["shorts"],
            cta="Subscribe"
        ),
        facebook=FacebookMetadata(
            title="FB Title",
            caption="FB Desc",
            hashtags=["fb", "reels"],
            cta="Share"
        ),
        snapchat=SnapchatMetadata(
            hook="Snap Title",
            caption="Snap Desc",
            hashtags=["snap"]
        ),
        pinterest=PinterestMetadata(
            title="Pin Title",
            description="Pin Desc",
            keywords=["pinterest"]
        ),
        x_threads=XThreadsMetadata(
            post="X post"
        )
    )
    mock_result.output = mock_pack
    mock_agent.run = AsyncMock(return_value=mock_result)

    monkeypatch.setattr("src.ai.get_social_agent", lambda: mock_agent)

    pack = await generate_social_media_pack("This is the transcript content of our video clip.", "Headline Hook")
    
    assert pack.youtube.best_title == "YouTube Best Title"
    assert pack.tiktok.caption == "TikTok Desc"
    assert pack.instagram.caption == "Insta Desc"
    assert pack.facebook.title == "FB Title"
    assert pack.snapchat.hook == "Snap Title"
    assert pack.pinterest.title == "Pin Title"
    assert pack.x_threads.post == "X post"

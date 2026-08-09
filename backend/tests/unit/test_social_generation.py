import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ai import generate_social_media_pack, SocialMediaPack, PlatformMetadata


@pytest.mark.asyncio
async def test_generate_social_media_pack_empty():
    pack = await generate_social_media_pack("")
    assert pack.youtube.title == ""
    assert pack.tiktok.title == ""


@pytest.mark.asyncio
async def test_generate_social_media_pack_with_content(monkeypatch):
    mock_agent = MagicMock()
    mock_result = MagicMock()
    
    mock_pack = SocialMediaPack(
        youtube=PlatformMetadata(title="YouTube Title", description="YouTube Desc", hashtags=["yt", "shorts"]),
        tiktok=PlatformMetadata(title="TikTok Title", description="TikTok Desc", hashtags=["tiktok", "viral"]),
        instagram=PlatformMetadata(title="Insta Title", description="Insta Desc", hashtags=["insta", "reels"]),
        facebook=PlatformMetadata(title="FB Title", description="FB Desc", hashtags=["fb", "reels"])
    )
    mock_result.output = mock_pack
    mock_agent.run = AsyncMock(return_value=mock_result)

    monkeypatch.setattr("src.ai.get_social_agent", lambda: mock_agent)

    pack = await generate_social_media_pack("This is the transcript content of our video clip.", "Headline Hook")
    
    assert pack.youtube.title == "YouTube Title"
    assert pack.tiktok.title == "TikTok Title"
    assert pack.instagram.title == "Insta Title"
    assert pack.facebook.title == "FB Title"

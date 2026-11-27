from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints
from pydantic.alias_generators import to_camel

from social_downloader.domain.options import (
    AudioBitrate,
    AudioFormat,
    DownloadMode,
    FilenameStyle,
    LocalProcessing,
    VideoQuality,
    YoutubeVideoCodec,
    YoutubeVideoContainer,
)

type LangCode = Annotated[
    str, StringConstraints(min_length=2, max_length=8, pattern=r"^[0-9a-zA-Z\-]+$")
]


class ApiRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")

    url: Annotated[str, StringConstraints(min_length=1)]
    audio_bitrate: AudioBitrate = "128"
    audio_format: AudioFormat = "mp3"
    download_mode: DownloadMode = "auto"
    filename_style: FilenameStyle = "basic"
    youtube_video_codec: YoutubeVideoCodec = "h264"
    youtube_video_container: YoutubeVideoContainer = "auto"
    video_quality: VideoQuality = "1080"
    local_processing: LocalProcessing = "disabled"
    youtube_dub_lang: LangCode | None = None
    subtitle_lang: LangCode | None = None
    disable_metadata: StrictBool = False
    allow_h265: StrictBool = False
    convert_gif: StrictBool = True
    tiktok_full_audio: StrictBool = False
    always_proxy: StrictBool = False
    youtube_hls: StrictBool = Field(default=False, alias="youtubeHLS")
    youtube_better_audio: StrictBool = False


class ResponseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, serialize_by_alias=True
    )


class RedirectResponse(ResponseModel):
    status: Literal["redirect"] = "redirect"
    url: str
    filename: str


class TunnelResponse(ResponseModel):
    status: Literal["tunnel"] = "tunnel"
    url: str
    filename: str


class PickerItem(ResponseModel):
    type: Literal["photo", "video", "gif"]
    url: str
    thumb: str | None = None


class PickerResponse(ResponseModel):
    status: Literal["picker"] = "picker"
    picker: list[PickerItem]
    audio: str | None = None
    audio_filename: str | None = None


class FileMetadata(BaseModel):
    album: str | None = None
    composer: str | None = None
    genre: str | None = None
    copyright: str | None = None
    title: str | None = None
    artist: str | None = None
    album_artist: str | None = None
    track: str | None = None
    date: str | None = None
    sublanguage: str | None = None


class OutputInfo(ResponseModel):
    type: str
    filename: str
    metadata: FileMetadata | None = None
    subtitles: bool | None = None


class AudioInfo(ResponseModel):
    copy_: bool = Field(alias="copy")
    format: str
    bitrate: str
    cover: bool | None = None
    crop_cover: bool | None = None


class LocalProcessingResponse(ResponseModel):
    status: Literal["local-processing"] = "local-processing"
    type: Literal["merge", "mute", "audio", "gif", "remux"]
    service: str
    tunnel: list[str]
    output: OutputInfo
    audio: AudioInfo | None = None
    is_hls: bool | None = Field(default=None, alias="isHLS")


class ErrorContext(ResponseModel):
    service: str | None = None
    limit: int | None = None


class ErrorInfo(ResponseModel):
    code: str
    context: ErrorContext | None = None


class ErrorResponse(ResponseModel):
    status: Literal["error"] = "error"
    error: ErrorInfo
    critical: bool | None = None


type ApiResponse = Annotated[
    RedirectResponse
    | TunnelResponse
    | PickerResponse
    | LocalProcessingResponse
    | ErrorResponse,
    Field(discriminator="status"),
]

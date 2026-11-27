from typing import Literal

type AudioBitrate = Literal["320", "256", "128", "96", "64", "8"]
type AudioFormat = Literal["best", "mp3", "ogg", "wav", "opus"]
type DownloadMode = Literal["auto", "audio", "mute"]
type FilenameStyle = Literal["classic", "pretty", "basic", "nerdy"]
type YoutubeVideoCodec = Literal["h264", "av1", "vp9"]
type YoutubeVideoContainer = Literal["auto", "mp4", "webm", "mkv"]
type VideoQuality = Literal[
    "max", "4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"
]
type LocalProcessing = Literal["disabled", "preferred", "forced"]

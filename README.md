# Local converter

FastAPI + plain JavaScript, with no accounts or external services. Drop one video or picture, choose a format and export preferences, then download the result.

## Ubuntu setup

Install Python 3.12+, its venv module, and FFmpeg:

```sh
sudo apt update
sudo apt install python3 python3-venv ffmpeg
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Open port 8000 in your local browser. Keep the server bound to loopback: this is a local tool without authentication, not a public upload service.

## Configuration

`formats.json` contains the curated export profiles, codec requirements, quality arguments, width choices, upload limit, and official FFmpeg documentation sources. Edit this file to change the available presets. Restart the server after editing. The browser and backend share the configuration. Only profiles with all required encoders installed are offered.

Video: MP4/H.264, MOV/H.264, MKV/H.264, WebM/VP9, animated GIF. Pictures: JPEG, PNG, WebP, BMP, TIFF. Input decoding depends on your FFmpeg build; examples include MP4, MOV, MKV, WebM, AVI, JPEG, PNG, WebP, BMP and TIFF. This is a curated subset of FFmpeg's capabilities, not every possible conversion. See the source links in the JSON and `ffmpeg -formats`, `ffmpeg -encoders`, `ffmpeg -decoders`.

Image exports take the first frame; GIF uses 12 fps. Quality presets affect lossy formats only. Width changes preserve aspect ratio; selecting a larger width upscales. Video dimensions are rounded to even pixels. Audio is re-encoded when retained, and only the first video and first audio stream are used. Metadata and subtitles are omitted. HDR tone mapping, animation preservation for picture outputs, progress percentages, and batch conversion are not implemented.

Uploads are limited to 512 MiB and conversions to ten minutes. Temporary conversion files are removed after the download or on failure; abrupt process termination may leave `web-tools-*` folders in the system temporary directory. Uploads are parsed into temporary spooled files before the conversion endpoint applies its size limit. Use only trusted local files; do not expose this process to untrusted networks. Conversion errors are shown in the interface.

## Validation

```sh
.venv/bin/python -m pytest -q
```

Tests generate a small video with audio, convert every configured profile, probe the downloaded results, convert a picture, and exercise invalid-file and invalid-format errors. FFmpeg and ffprobe must be on PATH.

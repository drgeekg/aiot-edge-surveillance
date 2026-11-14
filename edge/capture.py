import os
import shutil
import time
import cv2
import numpy as np


def resolve_youtube_stream_url(url: str) -> str:
    """Extract direct media stream URL from YouTube without downloading to disk."""
    import yt_dlp

    ydl_opts = {
        "format": "bestvideo[height<=720]/bestvideo/best",
        "quiet": True,
        "no_warnings": True,
    }
    node_bin = shutil.which("node")
    if node_bin:
        ydl_opts["js_runtimes"] = {"node": {}}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("url") or url


class VideoSource:
    """Unified OpenCV video source reader supporting webcams, looping files, RTSP, and YouTube."""

    def __init__(self, src: str | int):
        """Classify source type, open OpenCV VideoCapture, and minimize live camera buffering."""
        self.raw_src = src
        self.stream_url = None

        if isinstance(src, str) and src.isdigit():
            self.src: str | int = int(src)
            self.source_kind = "live"
        elif isinstance(src, int):
            self.src = src
            self.source_kind = "live"
        elif isinstance(src, str) and ("youtube.com" in src or "youtu.be" in src):
            self.source_kind = "youtube"
            self.stream_url = resolve_youtube_stream_url(src)
            self.src = self.stream_url
        elif isinstance(src, str) and (
            src.startswith("http://")
            or src.startswith("https://")
            or src.startswith("rtsp://")
        ):
            self.src = src
            self.source_kind = "url"
        else:
            self.src = str(src)
            self.source_kind = "file"
            if not os.path.exists(self.src):
                raise RuntimeError(
                    f"Video file not found: {self.src}. Provide a valid file path, YouTube URL, RTSP URL, or webcam index."
                )

        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open video source '{src}'. If streaming a YouTube or network URL, check your connection."
            )
        if self.source_kind == "live":
            # Keep only the latest webcam frame so processing never lags behind real time
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.file_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 25.0)
        self.loop_start = time.time()

    def read(self) -> np.ndarray | None:
        """Read the next BGR frame, looping local files at EOF and reconnecting dropped streams."""
        ok, frame = self.cap.read()
        if not ok or frame is None:
            if self.source_kind == "file":
                self.loop_start = time.time()
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
                if ok and frame is not None:
                    return frame
            elif self.source_kind == "youtube":
                # If stream ended or connection dropped, attempt to reconnect
                try:
                    self.cap.release()
                    self.stream_url = resolve_youtube_stream_url(str(self.raw_src))
                    self.cap = cv2.VideoCapture(self.stream_url)
                    ok, frame = self.cap.read()
                    if ok and frame is not None:
                        return frame
                except Exception:
                    pass
            return None
        return frame

    def release(self) -> None:
        """Release the underlying OpenCV VideoCapture resource if opened."""
        if self.cap is not None:
            self.cap.release()

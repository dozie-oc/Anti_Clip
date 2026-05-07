import ffmpeg
import os

class VideoService:
    @staticmethod
    def extract_audio(video_path: str, output_audio_path: str):
        """
        Extract audio from video using FFmpeg.
        """
        try:
            (
                ffmpeg
                .input(video_path)
                .output(output_audio_path, acodec='pcm_s16le', ac=1, ar='16k')
                .overwrite_output()
                .run(quiet=True)
            )
            return output_audio_path
        except ffmpeg.Error as e:
            print(f"Error extracting audio: {e}")
            raise

    @staticmethod
    def get_video_info(video_path: str):
        """
        Get video metadata using ffprobe.
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            return {
                "width": int(video_stream['width']),
                "height": int(video_stream['height']),
                "duration": float(probe['format']['duration'])
            }
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None

video_service = VideoService()

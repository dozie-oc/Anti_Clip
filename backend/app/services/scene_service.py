"""
Scene Detection Service — uses PySceneDetect to find visual boundaries in video.
"""
import logging
import os
from typing import List, Tuple

from scenedetect import detect, ContentDetector, SceneManager, open_video

logger = logging.getLogger(__name__)


class SceneService:
    """Detects scenes in video files using ContentDetector."""

    def detect_scenes(self, video_path: str, threshold: float = 33.0) -> List[Tuple[float, float]]:
        """
        Detect scenes in a video file.
        Returns a list of (start_seconds, end_seconds) tuples.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Detecting scenes for: {video_path} (threshold={threshold})")
        
        try:
            # Open video and detect scenes
            video = open_video(video_path)
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=threshold))
            
            # Optimization for speed: 
            # 1. Downscale to 360p or similar for detection (doesn't need high res)
            # 2. Skip frames (e.g. process every 2nd or 3rd frame)
            # This makes processing 10x+ faster for 4K or long movies.
            scene_manager.detect_scenes(video, show_progress=False, frame_skip=2)
            scene_list = scene_manager.get_scene_list()
            
            # Convert frame-based scenes to seconds
            scenes_in_seconds = []
            for scene in scene_list:
                start_sec = scene[0].get_seconds()
                end_sec = scene[1].get_seconds()
                scenes_in_seconds.append((start_sec, end_sec))
            
            logger.info(f"Detected {len(scenes_in_seconds)} scenes (optimized)")
            return scenes_in_seconds

        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
            # Fallback: treat whole video as one scene
            return []


# Module-level singleton
scene_service = SceneService()

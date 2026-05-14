"""
Narration Engine — orchestrates narration script generation, TTS, and video assembly.

Pipeline: Structured Script → Per-Segment TTS → Scene-Synced Video Assembly
"""
import json
import logging
import os
import re
import subprocess
from typing import List, Dict, Any, Optional

from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.video_service import video_service
from app.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Data structures for the narration pipeline
# ═══════════════════════════════════════════════════════════════════════════

class NarrationBlock:
    """A single narration segment: spoken text + the video scene it maps to."""

    def __init__(self, index: int, narration: str, scene_start: float, scene_end: float,
                 tts_path: str = None, tts_duration: float = 0.0):
        self.index = index
        self.narration = narration
        self.scene_start = scene_start
        self.scene_end = scene_end
        self.tts_path = tts_path
        self.tts_duration = tts_duration

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "narration": self.narration,
            "scene_start": self.scene_start,
            "scene_end": self.scene_end,
            "tts_path": self.tts_path,
            "tts_duration": self.tts_duration,
        }


class NarrationEngine:
    """Handles the full narration summary pipeline with scene-synced assembly."""

    # Approximate speaking rate for duration estimation (words per second)
    WORDS_PER_SECOND = 2.5

    def process_narration_mode(
        self,
        project_id: str,
        transcript_segments: List[Dict[str, Any]],
        target_minutes: int,
        video_path: str,
        output_dir: str,
        progress_callback: callable = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes the narration summary pipeline:
        1. Format transcript with timestamps for the LLM
        2. Generate structured narration script (JSON blocks)
        3. Synthesize TTS for each narration block
        4. Assemble final video: narration audio over matching source footage
        """
        os.makedirs(output_dir, exist_ok=True)
        tts_dir = os.path.join(output_dir, "tts_segments")
        os.makedirs(tts_dir, exist_ok=True)

        # Get video duration for validation
        video_duration = video_service.get_video_duration(video_path) or 0.0

        # ── Step 1: Format transcript with timestamps ────────────────────
        if progress_callback:
            progress_callback(56, "Formatting transcript for narration...")

        formatted_transcript = self._format_transcript_with_timestamps(transcript_segments)

        # ── Step 2: Generate structured narration script ─────────────────
        if progress_callback:
            progress_callback(60, "Writing narration script via AI...")

        logger.info(f"[{project_id}] Generating structured narration script ({target_minutes} min target)...")
        raw_script = llm_service.generate_narration_script(formatted_transcript, target_minutes)
        blocks = self._parse_structured_script(raw_script, video_duration)

        if not blocks:
            logger.warning(f"[{project_id}] No narration blocks parsed, using fallback...")
            blocks = self._generate_fallback_blocks(transcript_segments, target_minutes, video_duration)

        # Validate and fix timestamps
        blocks = self._validate_and_fix_blocks(blocks, video_duration)
        logger.info(f"[{project_id}] Narration script: {len(blocks)} blocks")

        # ── Step 3: Synthesize TTS per block ─────────────────────────────
        if progress_callback:
            progress_callback(70, f"Synthesizing voice for {len(blocks)} narration segments...")

        for i, block in enumerate(blocks):
            tts_path = os.path.join(tts_dir, f"narration_{i:03d}.wav")
            try:
                tts_service.generate_speech(block.narration, tts_path)
                block.tts_path = tts_path
                # Get actual TTS audio duration for timing
                block.tts_duration = self._get_audio_duration(tts_path)
                logger.info(f"  Block {i}: TTS={block.tts_duration:.1f}s, Scene={block.scene_start:.1f}-{block.scene_end:.1f}s")
            except Exception as e:
                logger.error(f"  Block {i} TTS failed: {e}")
                block.tts_path = None
                block.tts_duration = 0.0

            if progress_callback:
                sub_progress = 70 + int(((i + 1) / len(blocks)) * 15)
                progress_callback(sub_progress, f"Voice {i + 1}/{len(blocks)} synthesized")

        # Filter out blocks where TTS failed
        valid_blocks = [b for b in blocks if b.tts_path and os.path.exists(b.tts_path)]
        if not valid_blocks:
            logger.error(f"[{project_id}] All TTS blocks failed!")
            return [{
                "id": "summary_01",
                "filename": "narration_summary.mp4",
                "script": raw_script,
                "tts_path": "",
                "status": "failed_tts"
            }]

        # ── Step 4: Assemble final video ─────────────────────────────────
        if progress_callback:
            progress_callback(88, "Assembling final narration video...")

        final_video_path = os.path.join(output_dir, "narration_summary.mp4")

        try:
            self._assemble_narrated_video(video_path, valid_blocks, final_video_path)
            logger.info(f"[{project_id}] Narration video assembled at {final_video_path}")
            status = "completed"
        except Exception as e:
            logger.error(f"[{project_id}] Video assembly failed: {e}", exc_info=True)
            # Attempt simpler fallback assembly
            try:
                self._assemble_simple_fallback(video_path, valid_blocks, final_video_path)
                logger.info(f"[{project_id}] Fallback assembly succeeded")
                status = "completed"
            except Exception as e2:
                logger.error(f"[{project_id}] Fallback assembly also failed: {e2}")
                status = "failed_render"

        # Build the human-readable script for display
        readable_script = self._blocks_to_readable_script(valid_blocks)

        return [{
            "id": "summary_01",
            "filename": "narration_summary.mp4",
            "script": readable_script,
            "tts_path": os.path.join(tts_dir, "narration_000.wav"),
            "blocks": [b.to_dict() for b in valid_blocks],
            "status": status,
        }]

    # ═══════════════════════════════════════════════════════════════════════
    # Step 1: Transcript Formatting
    # ═══════════════════════════════════════════════════════════════════════

    def _format_transcript_with_timestamps(self, segments: List[Dict[str, Any]]) -> str:
        """
        Formats transcript segments into a timestamped layout the LLM can reference.
        Example: [00:15 - 00:42] Speaker talks about the main topic...
        """
        lines = []
        for seg in segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "").strip()
            if not text:
                continue
            start_fmt = self._format_timestamp(start)
            end_fmt = self._format_timestamp(end)
            lines.append(f"[{start_fmt} - {end_fmt}] {text}")
        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Convert seconds to MM:SS or HH:MM:SS format."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def _timestamp_to_seconds(ts: str) -> float:
        """Convert MM:SS or HH:MM:SS or raw number to seconds."""
        ts = ts.strip()
        # Try raw float first
        try:
            return float(ts)
        except ValueError:
            pass
        # Try MM:SS or HH:MM:SS
        parts = ts.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except (ValueError, IndexError):
            pass
        return 0.0

    # ═══════════════════════════════════════════════════════════════════════
    # Step 2: Structured Script Parsing
    # ═══════════════════════════════════════════════════════════════════════

    def _parse_structured_script(self, raw_script: str, video_duration: float) -> List[NarrationBlock]:
        """
        Parse the LLM output into NarrationBlocks.
        
        Supports two formats:
        1. JSON array: [{"narration": "...", "scene_start": "01:15", "scene_end": "01:42"}, ...]
        2. Markdown with markers: 
           [SCENE: 01:15 - 01:42]
           Narration text here...
        """
        blocks = []

        # ── Try JSON parse first ────────────────────────────────────────
        blocks = self._try_parse_json_script(raw_script)
        if blocks:
            return blocks

        # ── Fallback to marker-based parsing ────────────────────────────
        blocks = self._parse_marker_script(raw_script, video_duration)
        return blocks

    def _try_parse_json_script(self, raw_script: str) -> List[NarrationBlock]:
        """Try to parse the script as a JSON array of narration blocks."""
        blocks = []
        try:
            clean = raw_script.strip()
            # Remove markdown fences
            if "```" in clean:
                clean = re.sub(r'```json\s*|\s*```', '', clean)
            
            # Find the first [ and the last ]
            start_idx = clean.find('[')
            end_idx = clean.rfind(']')
            
            if start_idx == -1 or end_idx == -1:
                # Maybe it's a dict with a list inside?
                start_idx = clean.find('{')
                end_idx = clean.rfind('}')
                if start_idx == -1: return []
            
            json_str = clean[start_idx:end_idx+1]
            parsed = json.loads(json_str)

            # If it's a dict, try to find the list inside
            if isinstance(parsed, dict):
                for key in ["blocks", "script", "narration", "recap", "scenes"]:
                    if key in parsed and isinstance(parsed[key], list):
                        parsed = parsed[key]
                        break
            
            if not isinstance(parsed, list):
                return []

            for i, item in enumerate(parsed):
                if not isinstance(item, dict): continue
                narration = item.get("narration", item.get("text", item.get("script", "")))
                if not narration: continue

                scene_start = self._timestamp_to_seconds(str(item.get("scene_start", item.get("start", "0"))))
                scene_end = self._timestamp_to_seconds(str(item.get("scene_end", item.get("end", "30"))))

                # Min duration check
                if scene_end - scene_start < 2.0:
                    scene_end = scene_start + 5.0

                blocks.append(NarrationBlock(
                    index=i,
                    narration=narration.strip(),
                    scene_start=scene_start,
                    scene_end=scene_end,
                ))

            return blocks
        except Exception as e:
            logger.debug(f"JSON parse failed: {e}")
            return []

    def _parse_marker_script(self, raw_script: str, video_duration: float) -> List[NarrationBlock]:
        """
        Parse [SCENE: start - end] marker format.
        Each marker is followed by narration text until the next marker.
        """
        blocks = []

        # Pattern for [SCENE: timestamp - timestamp] with flexible formats
        # Supports: [SCENE: 01:15 - 01:42], [SCENE: 75 - 102], [SCENE: 1:15:00 - 1:42:30]
        pattern = r'\[SCENE:\s*([^\]]+?)\s*-\s*([^\]]+?)\s*\]'
        
        # Split the script by scene markers
        parts = re.split(pattern, raw_script)

        if len(parts) < 4:
            # No markers found — treat entire script as one block
            clean_text = re.sub(r'\[SCENE:[^\]]*\]', '', raw_script).strip()
            if clean_text:
                blocks.append(NarrationBlock(
                    index=0,
                    narration=clean_text,
                    scene_start=0,
                    scene_end=min(30.0, video_duration) if video_duration > 0 else 30.0,
                ))
            return blocks

        # parts[0] = text before first marker (intro narration if any)
        # parts[1] = first start time
        # parts[2] = first end time
        # parts[3] = text after first marker (narration for that scene)
        # parts[4] = second start time ... etc.

        block_idx = 0

        # Handle text before first marker as intro narration
        intro_text = parts[0].strip()
        if intro_text and len(intro_text.split()) > 5:
            # Use the first scene's start for intro
            if len(parts) >= 4:
                first_start = self._timestamp_to_seconds(parts[1])
                blocks.append(NarrationBlock(
                    index=block_idx,
                    narration=intro_text,
                    scene_start=max(0, first_start - 2),
                    scene_end=first_start,
                ))
                block_idx += 1

        # Parse marker groups
        i = 1
        while i + 2 < len(parts):
            start_ts = parts[i]
            end_ts = parts[i + 1]
            narration_text = parts[i + 2].strip() if i + 2 < len(parts) else ""

            if narration_text:
                scene_start = self._timestamp_to_seconds(start_ts)
                scene_end = self._timestamp_to_seconds(end_ts)

                # Add 1-2s padding
                scene_start = max(0, scene_start - 1.0)
                if video_duration > 0:
                    scene_end = min(video_duration, scene_end + 1.0)
                else:
                    scene_end = scene_end + 1.0

                blocks.append(NarrationBlock(
                    index=block_idx,
                    narration=narration_text,
                    scene_start=scene_start,
                    scene_end=scene_end,
                ))
                block_idx += 1

            i += 3

        if blocks:
            logger.info(f"Parsed {len(blocks)} narration blocks from marker format")
        return blocks

    # ═══════════════════════════════════════════════════════════════════════
    # Validation & Fixing
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_and_fix_blocks(self, blocks: List[NarrationBlock], video_duration: float) -> List[NarrationBlock]:
        """Validate timestamp ranges and resolve overlaps."""
        if not blocks:
            return blocks

        fixed = []
        for block in blocks:
            # Clamp to video duration
            if video_duration > 0:
                block.scene_start = max(0, min(block.scene_start, video_duration - 1))
                block.scene_end = max(block.scene_start + 1, min(block.scene_end, video_duration))
            else:
                block.scene_start = max(0, block.scene_start)
                block.scene_end = max(block.scene_start + 1, block.scene_end)

            # Estimate required scene duration from narration length
            word_count = len(block.narration.split())
            estimated_speech_seconds = word_count / self.WORDS_PER_SECOND
            scene_duration = block.scene_end - block.scene_start

            # If scene is much shorter than speech, extend it
            if scene_duration < estimated_speech_seconds:
                new_end = block.scene_start + estimated_speech_seconds + 2.0
                if video_duration > 0:
                    block.scene_end = min(new_end, video_duration)
                else:
                    block.scene_end = new_end

            fixed.append(block)

        # Sort by scene start time
        fixed.sort(key=lambda b: b.scene_start)

        # Resolve overlaps: ensure each block's start >= previous block's end
        for i in range(1, len(fixed)):
            if fixed[i].scene_start < fixed[i - 1].scene_end:
                # Shift current block's start to after previous block's end
                gap = 0.5  # small gap between scenes
                fixed[i].scene_start = fixed[i - 1].scene_end + gap
                # Also ensure end > start
                if fixed[i].scene_end <= fixed[i].scene_start:
                    word_count = len(fixed[i].narration.split())
                    fixed[i].scene_end = fixed[i].scene_start + max(5.0, word_count / self.WORDS_PER_SECOND)

        return fixed

    def _generate_fallback_blocks(self, segments: List[Dict[str, Any]], target_minutes: int,
                                   video_duration: float) -> List[NarrationBlock]:
        """Generate basic narration blocks when LLM parsing fails."""
        blocks = []
        # Pick evenly spaced segments from the transcript
        total_segments = len(segments)
        if total_segments == 0:
            return [NarrationBlock(
                index=0,
                narration="This video contains a variety of content. Here is a quick summary.",
                scene_start=0,
                scene_end=min(30, video_duration) if video_duration > 0 else 30,
            )]

        # Pick ~5-8 segments spread across the video
        num_picks = min(8, max(3, total_segments // 4))
        step = max(1, total_segments // num_picks)

        for i, idx in enumerate(range(0, total_segments, step)):
            if idx >= total_segments:
                break
            seg = segments[idx]
            blocks.append(NarrationBlock(
                index=i,
                narration=f"[AI Fallback] {seg.get('text', '').strip()}",
                scene_start=seg.get("start", i * 10),
                scene_end=seg.get("end", i * 10 + 15),
            ))

        return blocks[:num_picks]

    # ═══════════════════════════════════════════════════════════════════════
    # Step 4: Video Assembly
    # ═══════════════════════════════════════════════════════════════════════

    def _assemble_narrated_video(self, video_path: str, blocks: List[NarrationBlock], output_path: str):
        """
        Assemble the final narration video using FFmpeg.
        
        Improvements:
        - Burns in captions (subtitles) for each segment.
        - Mixes in background music if available.
        - Better audio ducking and transitions.
        """
        ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")
        temp_parts = []
        
        # Check for background music
        bg_music_path = os.path.join("storage", "assets", "bg_music.mp3")
        has_bg_music = os.path.exists(bg_music_path)

        try:
            for i, block in enumerate(blocks):
                part_path = output_path.replace(".mp4", f"_part_{i:03d}.mp4")
                temp_parts.append(part_path)

                scene_duration = block.scene_end - block.scene_start
                tts_duration = block.tts_duration

                # Use the longer of scene duration or TTS duration for the segment
                segment_duration = max(scene_duration, tts_duration + 0.5)

                # Build FFmpeg command for this segment
                srt_path = self._create_segment_srt(block, segment_duration)
                srt_path_fixed = srt_path.replace("\\", "/").replace(":", "\\:")
                sub_style = "FontSize=18,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=1,Outline=1,Shadow=1,Alignment=2,MarginV=30"
                
                cmd = [
                    ffmpeg_bin, "-y",
                    "-ss", str(block.scene_start),
                    "-t", str(segment_duration),
                    "-i", video_path,
                    "-i", block.tts_path,
                    "-filter_complex",
                    f"[0:v]subtitles='{srt_path_fixed}':force_style='{sub_style}'[v_subs];"
                    "[0:a]volume=0.1[bg];[1:a]volume=1.0[tts];"
                    "[bg][tts]amix=inputs=2:duration=first:dropout_transition=0.5[aout]",
                    "-map", "[v_subs]", "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                    "-c:a", "aac", "-b:a", "192k", "-shortest",
                    part_path,
                ]

                logger.info(f"  Rendering segment {i+1}/{len(blocks)}...")
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if result.returncode != 0:
                    logger.warning(f"  Subtitle render failed, retrying without subtitles...")
                    cmd_no_subs = [
                        ffmpeg_bin, "-y", "-ss", str(block.scene_start), "-t", str(segment_duration),
                        "-i", video_path, "-i", block.tts_path,
                        "-filter_complex", "[0:a]volume=0.1[bg];[1:a]volume=1.0[tts];[bg][tts]amix=inputs=2:duration=first[aout]",
                        "-map", "0:v", "-map", "[aout]",
                        "-c:v", "libx264", "-preset", "ultrafast", part_path
                    ]
                    result = subprocess.run(cmd_no_subs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if os.path.exists(srt_path):
                    try: os.remove(srt_path)
                    except: pass
                    
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed for segment {i}: {result.stderr.decode(errors='replace')}")

            # ── Concatenate all parts ────────────────────────────────────
            if len(temp_parts) == 1:
                # Just rename the single part
                os.replace(temp_parts[0], output_path)
            else:
                self._concat_video_parts(temp_parts, output_path, ffmpeg_bin)

            # ── Add Background Music (Final Pass) ────────────────────────
            if has_bg_music:
                self._apply_background_music(output_path, bg_music_path, ffmpeg_bin)

        finally:
            # Clean up temp parts
            for part in temp_parts:
                if os.path.exists(part) and part != output_path:
                    try:
                        os.remove(part)
                    except OSError:
                        pass

    def _create_segment_srt(self, block: NarrationBlock, duration: float) -> str:
        """Creates a temporary .srt file for a single narration block."""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".srt")
        
        # We want the text to appear for the duration of the TTS
        # or split it into smaller chunks if it's too long
        text = block.narration.strip()
        words = text.split()
        
        # Simple splitting: 7 words per subtitle line
        chunk_size = 7
        chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
        
        # Divide duration among chunks
        chunk_duration = duration / max(1, len(chunks))
        
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(chunks):
                start_time = i * chunk_duration
                end_time = (i + 1) * chunk_duration
                
                def format_time(seconds):
                    h = int(seconds // 3600)
                    m = int((seconds % 3600) // 60)
                    sec = int(seconds % 60)
                    ms = int((seconds % 1) * 1000)
                    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

                f.write(f"{i+1}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{' '.join(chunk)}\n\n")
        return path

    def _apply_background_music(self, video_path: str, music_path: str, ffmpeg_bin: str):
        """Overlay a subtle music track over the entire video."""
        temp_output = video_path.replace(".mp4", "_music.mp4")
        
        cmd = [
            ffmpeg_bin, "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            # Music at 8% volume, loop if necessary
            "[1:a]aloop=loop=-1:size=2e+09,volume=0.08[music];"
            "[0:a][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy", # No re-encoding video
            "-c:a", "aac", "-b:a", "192k",
            temp_output
        ]
        
        logger.info("Applying background music track...")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        # Replace original with the music version
        os.replace(temp_output, video_path)

    def _concat_video_parts(self, parts: List[str], output_path: str, ffmpeg_bin: str):
        """Concatenate video parts using FFmpeg concat demuxer."""
        # Create concat file list
        concat_file = output_path.replace(".mp4", "_concat.txt")
        try:
            with open(concat_file, "w", encoding="utf-8") as f:
                for part in parts:
                    # FFmpeg concat demuxer needs forward slashes or escaped backslashes
                    safe_path = part.replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                ffmpeg_bin, "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                output_path,
            ]

            logger.info(f"Concatenating {len(parts)} segments into final video...")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")[-500:]
                raise RuntimeError(f"Concat failed: {stderr}")

        finally:
            if os.path.exists(concat_file):
                try:
                    os.remove(concat_file)
                except OSError:
                    pass

    def _assemble_simple_fallback(self, video_path: str, blocks: List[NarrationBlock], output_path: str):
        """
        Simplified fallback: concatenate all TTS into one audio track,
        then overlay on the first N seconds of the source video.
        """
        ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")

        # Merge all TTS files into one
        tts_paths = [b.tts_path for b in blocks if b.tts_path]
        if not tts_paths:
            raise RuntimeError("No TTS audio available for fallback assembly")

        merged_tts = output_path.replace(".mp4", "_merged_tts.wav")
        try:
            if len(tts_paths) == 1:
                merged_tts = tts_paths[0]
            else:
                # Concatenate TTS files
                concat_filter = "".join(f"[{i}:a]" for i in range(len(tts_paths)))
                concat_filter += f"concat=n={len(tts_paths)}:v=0:a=1[aout]"

                cmd = [ffmpeg_bin, "-y"]
                for p in tts_paths:
                    cmd.extend(["-i", p])
                cmd.extend([
                    "-filter_complex", concat_filter,
                    "-map", "[aout]",
                    merged_tts,
                ])
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # Get total TTS duration
            total_tts_duration = sum(b.tts_duration for b in blocks)

            # Overlay merged TTS on video (from start)
            cmd = [
                ffmpeg_bin, "-y",
                "-i", video_path,
                "-i", merged_tts,
                "-t", str(total_tts_duration + 2),
                "-filter_complex",
                "[0:a]volume=0.15[bg];[1:a]apad[tts];[bg][tts]amix=inputs=2:duration=first[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                output_path,
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        finally:
            if merged_tts != tts_paths[0] and os.path.exists(merged_tts):
                try:
                    os.remove(merged_tts)
                except OSError:
                    pass

    # ═══════════════════════════════════════════════════════════════════════
    # Utility methods
    # ═══════════════════════════════════════════════════════════════════════

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of an audio file using ffprobe."""
        ffprobe_bin = getattr(settings, "FFPROBE_PATH", "ffprobe")
        try:
            cmd = [
                ffprobe_bin, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return float(result.stdout.decode().strip())
        except Exception:
            # Estimate from file size (16-bit mono 22050Hz WAV)
            try:
                size = os.path.getsize(audio_path)
                return size / (22050 * 2)  # rough estimate
            except Exception:
                return 5.0

    def _blocks_to_readable_script(self, blocks: List[NarrationBlock]) -> str:
        """Convert narration blocks back into a human-readable script with markers."""
        lines = []
        for block in blocks:
            start_fmt = self._format_timestamp(block.scene_start)
            end_fmt = self._format_timestamp(block.scene_end)
            lines.append(f"[SCENE: {start_fmt} - {end_fmt}]")
            lines.append(block.narration)
            lines.append("")
        return "\n".join(lines)


narration_engine = NarrationEngine()

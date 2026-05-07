from moviepy.editor import VideoFileClip
import os
import uuid

class ClipEngine:
    @staticmethod
    def select_clips(segments, prompt, min_duration=5, max_duration=60):
        """
        Simulate AI selection based on segments and prompt.
        For now, we select segments that have longer text (more information).
        """
        # In a real scenario, this would use an LLM to analyze the segments against the prompt.
        # Here we just pick the top 5 longest segments as a proxy for "interesting" content.
        
        sorted_segments = sorted(segments, key=lambda x: len(x['text']), reverse=True)
        selected = sorted_segments[:5]
        
        clips_metadata = []
        for i, seg in enumerate(selected):
            start = seg['start']
            end = seg['end']
            duration = end - start
            
            # Ensure minimum duration
            if duration < min_duration:
                end = start + min_duration
            
            clips_metadata.append({
                "id": str(uuid.uuid4()),
                "start": start,
                "end": end,
                "text": seg['text'],
                "index": i
            })
            
        return clips_metadata

    @staticmethod
    def generate_clips(video_path: str, clips_metadata, output_dir: str):
        """
        Generate video files for each clip.
        """
        os.makedirs(output_dir, exist_ok=True)
        generated_files = []
        
        video = VideoFileClip(video_path)
        
        for clip_meta in clips_metadata:
            start = clip_meta['start']
            end = min(clip_meta['end'], video.duration)
            
            output_filename = f"clip_{clip_meta['id']}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            # Cut and save
            subclip = video.subclip(start, end)
            
            # For "viral shorts" simulation, we could crop to 9:16 here if needed.
            # For now, just save as is.
            subclip.write_videofile(output_path, codec="libx264", audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True, verbose=False, logger=None)
            
            generated_files.append({
                "id": clip_meta['id'],
                "filename": output_filename,
                "path": output_path,
                "start": start,
                "end": end,
                "text": clip_meta['text']
            })
            
        video.close()
        return generated_files

clip_engine = ClipEngine()

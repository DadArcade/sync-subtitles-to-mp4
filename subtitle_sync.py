import os
import re
import argparse
import subprocess
import difflib
import tempfile
from faster_whisper import WhisperModel

# --- HELPER FUNCTIONS ---

def parse_srt_time(time_str):
    """Converts an SRT timestamp (HH:MM:SS,mmm) into pure seconds."""
    hours, minutes, seconds = time_str.split(':')
    seconds, milliseconds = seconds.split(',')
    total_seconds = (int(hours) * 3600) + (int(minutes) * 60) + int(seconds) + (int(milliseconds) / 1000.0)
    return total_seconds

def get_srt_blocks(srt_path):
    """Parses the opening sequences of an SRT file into a structured list of blocks."""
    timestamp_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})')
    blocks = []
    
    current_start = None
    current_text_lines = []
    
    with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_str = line.strip()
            match = timestamp_pattern.search(line_str)
            
            if match:
                if current_start is not None and current_text_lines:
                    blocks.append({'start': current_start, 'text': " ".join(current_text_lines)})
                current_start = parse_srt_time(match.group(1))
                current_text_lines = []
                continue
                
            if current_start is not None:
                if line_str == "" or line_str.isdigit():
                    continue
                else:
                    current_text_lines.append(line_str)
                    
        # Catch trailing buffer block if present
        if current_start is not None and current_text_lines:
            blocks.append({'start': current_start, 'text': " ".join(current_text_lines)})
            
    return blocks

def clean_text_for_matching(text):
    """Strips punctuation and downcases text to normalize fuzzy comparison metrics."""
    return re.sub(r'[^\w\s]', '', text.strip().lower())

def find_best_srt_match(whisper_text, srt_blocks, max_window=3):
    """
    Compares Whisper text against sliding window combinations of SRT cards
    to locate the highest similarity match.
    """
    cleaned_whisper = clean_text_for_matching(whisper_text)
    best_score = 0.0
    best_match_time = None
    best_match_text = ""
    
    # Check the first 50 subtitle blocks to safely bypass ambient tags or multi-line music descriptions
    search_limit = min(50, len(srt_blocks))
    
    for i in range(search_limit):
        for window_size in range(1, max_window + 1):
            if i + window_size > search_limit:
                break
                
            # Combine text content from the current window chain of subtitle cards
            window_blocks = srt_blocks[i:i+window_size]
            combined_srt_text = " ".join([b['text'] for b in window_blocks])
            cleaned_srt = clean_text_for_matching(combined_srt_text)
            
            # Calculate the sequence similarity ratio
            score = difflib.SequenceMatcher(None, cleaned_whisper, cleaned_srt).ratio()
            
            if score > best_score:
                best_score = score
                best_match_time = window_blocks[0]['start']  # Lock anchor to the first card in window
                best_match_text = combined_srt_text
                
    return best_match_time, best_match_text, best_score

# --- MAIN EXECUTION ---
def main():
    parser = argparse.ArgumentParser(description="Auto-align subtitles using Whisper audio analysis.")
    parser.add_argument("--video", required=True, help="Path to the input MP4 video file.")
    parser.add_argument("--srt", required=True, help="Path to the input SRT subtitle file.")
    parser.add_argument("--audio-track", type=int, default=0, help="Zero-indexed audio track (default: 0).")
    parser.add_argument("--translate", action="store_true", help="Translate foreign audio to English.")
    args = parser.parse_args()

    # Generate a unique temp file to avoid collisions on concurrent runs
    temp_fd, temp_audio = tempfile.mkstemp(suffix=".wav", prefix="subtitle_sync_")
    os.close(temp_fd)  # Close file descriptor so FFmpeg can write to it

    try:
        # 1. Parse opening SRT structural footprint blocks
        print(f"[1/5] Analyzing structural timestamps in: {args.srt}")
        srt_blocks = get_srt_blocks(args.srt)
        
        if not srt_blocks:
            print("[-] Error: Could not parse any valid timestamps inside the provided SRT file.")
            return
            


        # 2. Extract the audio track via FFmpeg (Safe list format for spaces)
        print("[2/5] Extracting audio stream from video...")
        ffmpeg_extract_cmd = [
            "ffmpeg", "-y", "-i", args.video, "-vn", 
            "-map", f"0:a:{args.audio_track}",
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", temp_audio
        ]
        subprocess.run(ffmpeg_extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(temp_audio):
            print(f"[-] Error: Audio extraction failed. Verify that your MP4 path is valid and that --audio-track {args.audio_track} exists.")
            return

        # 3. Initialize Whisper with Deterministic Parameters
        print("[3/5] Launching Whisper engine to isolate genuine spoken sentences...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        whisper_task = "translate" if args.translate else "transcribe"
        
        segments, _ = model.transcribe(
            temp_audio, 
            beam_size=5,
            task=whisper_task,                # Dynamically set to translate or transcribe
            temperature=0.0,                  # Forced determinism to stop changing results
            condition_on_previous_text=False
        )
        
        best_whisper_start = None
        best_whisper_text = ""
        final_srt_match_start = None
        final_srt_match_text = ""
        best_overall_confidence = 0.0
        
        attempts = 0

        for segment in segments:
            raw_text = segment.text.strip()
            text_clean = raw_text.lower()
            words = [w for w in text_clean.split() if w not in [",", ".", "!", "?", "-"]]

            # Reject known non-speech ambient description tags
            if text_clean in ["music", "[music]", "(music)", "applause", "laughter"]:
                continue
                
            # Enforce the 5-word minimum threshold
            if len(words) < 5:
                continue
                
            # 4. Perform sliding-window fuzzy matching on THIS candidate
            srt_match_start, srt_match_text, match_confidence = find_best_srt_match(
                raw_text, srt_blocks
            )

            # Keep track of the best match we have seen so far
            if match_confidence > best_overall_confidence:
                best_overall_confidence = match_confidence
                best_whisper_start = segment.start
                best_whisper_text = raw_text
                final_srt_match_start = srt_match_start
                final_srt_match_text = srt_match_text

            # If we find a confident match (>= 50%), securely lock it in and stop checking
            if match_confidence >= 0.50:
                break
                
            # Failsafe: Prevent scanning the entire movie. Give up after 10 valid speech candidates.
            attempts += 1
            if attempts >= 10:
                break

        if best_whisper_start is None or best_overall_confidence < 0.35:
            print("[-] Error: Fuzzy matching engine could not safely map any audio text to SRT file patterns.")
            return

        whisper_first_start = best_whisper_start
        whisper_first_text = best_whisper_text
        srt_match_start = final_srt_match_start
        srt_match_text = final_srt_match_text
        match_confidence = best_overall_confidence

        # --- SIDE-BY-SIDE PRINT REPORT ---
        print("\n=================== FUZZY MATCH COMPARISON ===================")
        print(f"AUDIO (Whisper) [{whisper_first_start:.2f}s]: \"{whisper_first_text}\"")
        print(f"SUBTITLE (SRT)  [{srt_match_start:.2f}s]: \"{srt_match_text}\"")
        print(f"MATCH SIMILARITY CONFIDENCE: {match_confidence:.2%}")
        print("=============================================================\n")

        # 5. Evaluate the drift time delta based on matched anchors
        time_delta = whisper_first_start - srt_match_start
        print(f"[4/5] Evaluating synchronization metrics... (Drift Delta: {time_delta:+.2f} seconds)")

        if abs(time_delta) > 2.0:
            output_srt = os.path.splitext(args.srt)[0] + "_synced.srt"
            print(f"[5/5] Subtitle drift exceeds 2 seconds threshold. Commencing shift pipeline...")
            
            ffmpeg_sync_cmd = [
                "ffmpeg", "-y", "-itsoffset", f"{time_delta:.3f}", 
                "-i", args.srt, "-c", "copy", output_srt
            ]
            subprocess.run(ffmpeg_sync_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print(f"\n✨ Sync completed successfully!")
            print(f"👉 New adjusted subtitle generated at: {output_srt}")
        else:
            print("\n✅ Subtitle drift is within acceptable bounds (<= 2 seconds). No modification required.")

    finally:
        # File integrity cleanup
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

if __name__ == "__main__":
    main()

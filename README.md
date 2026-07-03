# Subtitle Sync Tool

Automatically syncs SRT subtitles to MP4 videos using AI audio transcription (`faster-whisper`).

## Prerequisites

- `python3`
- `ffmpeg` (e.g., `sudo apt install ffmpeg`)

*(Python dependencies install automatically on first run)*

## How to Run

1. Download both `run_sync.sh` and `subtitle_sync.py` to the same folder.
2. Run the included wrapper script:

```bash
./run_sync.sh --video "path/to/movie.mp4" --srt "path/to/subtitles.srt"
```

*Note: The script creates a new `_synced.srt` file in the same directory if adjustments are made. Your original file is left untouched.*

### Options

| Argument | Description | Required |
|----------|-------------|----------|
| `--video` | Path to the MP4 file | **Yes** |
| `--srt` | Path to the SRT file | **Yes** |
| `--audio-track` | Audio track number to use (Default: `0`) | No |
| `--translate` | Translates foreign audio to English before syncing | No |
| `--cleanup` | Deletes the generated Python virtual environment | No |

### Examples

**Basic Synchronization**
```bash
./run_sync.sh --video /videos/movie.mp4 --srt /videos/subtitles.srt 
```

**Custom Audio Track** (e.g., track 1 instead of 0)
```bash
./run_sync.sh --video /videos/movie.mp4 --srt /videos/subtitles.srt --audio-track 1
```

**Foreign Audio** (Translates foreign speech to match English subtitles)
```bash
./run_sync.sh --video /videos/foreign_movie.mp4 --srt /videos/english.srt --translate
```

## How It Works

1. **Extract**: Isolates the video's audio using FFmpeg.
2. **Listen**: Transcribes the spoken audio to text using AI.
3. **Match**: Finds the best match between the spoken text and your subtitle file.
4. **Compare**: Calculates the time difference between the two.
5. **Fix**: If the difference is larger than 2 seconds, creates a corrected `_synced.srt` file.

## Example
<details>
  <summary>Expand example:</summary>

```bash

./run_sync.sh --video /videos/Notorious\ \(1946\).mp4 --srt /videos/Notorious\ \(1946\).eng.srt 
[1/5] Analyzing structural timestamps in: /videos/Notorious (1946).eng.srt
[2/5] Extracting audio stream from video...
[3/5] Launching Whisper engine to isolate genuine spoken sentences...

=================== FUZZY MATCH COMPARISON ===================
AUDIO (Whisper) [90.00s]: "To be the reason why sin should not be pronounced."
SUBTITLE (SRT)  [105.97s]: "Is there any legal reason why sentence should not be pronounced?"
MATCH SIMILARITY CONFIDENCE: 76.79%
=============================================================

[4/5] Evaluating synchronization metrics... (Drift Delta: -15.97 seconds)
[5/5] Subtitle drift exceeds 2 seconds threshold. Commencing shift pipeline...

✨ Sync completed successfully!
👉 New adjusted subtitle generated at: /videos/Notorious (1946).eng_synced.srt

```
</details>

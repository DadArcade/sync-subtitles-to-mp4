# Subtitle Sync Tool

This tool automatically detects and corrects out-of-sync SRT subtitle files for MP4 videos. Instead of manually guessing time offsets, this script uses `faster-whisper` for audio-transcription comparison to dynamically identify audio drift and shift your subtitles into perfect sync.

## Prerequisites

To run this tool, ensure the following core dependencies are available on your system:
- `python3`
- `ffmpeg` (e.g., `sudo apt install ffmpeg`)

*Note: Python dependencies like `faster-whisper` will be automatically installed into an isolated virtual environment.*

## How to Run

The simplest way to execute the synchronization tool is by using the included `run_sync.sh` wrapper script. 

When you run `run_sync.sh` for the first time, it automatically verifies your system dependencies, creates a Python virtual environment (`venv/`), installs `faster-whisper`, and passes your arguments directly to the main Python script.

```bash
./run_sync.sh --video "path/to/movie.mp4" --srt "path/to/subtitles.srt"
```

*Note: The script does not overwrite your original file. If a sync adjustment is necessary, it will generate a new synchronized file with the `_synced.srt` suffix in the same directory.*

### Cleanup

If you want to remove the generated Python virtual environment and clean up your directory to save space:

```bash
./run_sync.sh --cleanup
```

## Command Line Arguments

All arguments passed through `run_sync.sh` fall straight through to the underlying `subtitle_sync.py` script.

| Argument | Description | Required |
|----------|-------------|----------|
| `--video` | Path to the input MP4 video file. | **Yes** |
| `--srt` | Path to the input SRT subtitle file. | **Yes** |
| `--audio-track` | Indicates which audio stream index to extract. Default: `0`. | No |
| `--translate` | Instructs Whisper to translate foreign language audio to English before attempting a fuzzy match. Use this if the audio doesn't natively match the English SRT text. | No |

### Examples

**Basic Synchronization**
Syncs the first audio track (index 0) of the target movie:
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

**Custom Audio Track**
If your MP4 file has multiple audio tracks (e.g., Director's Commentary on track 0, standard English audio on track 1):
```bash
./run_sync.sh --video /movies/inception.mp4 --srt /movies/inception.srt --audio-track 1
```

**Foreign Audio Translation**
If the movie is in Spanish, but you are trying to sync English subtitles. Passing the `--translate` flag enables Whisper's translation engine prior to matching against the English subtitle file:
```bash
./run_sync.sh --video /movies/pans_labyrinth.mp4 --srt /movies/pans_labyrinth.srt --translate
```

## How It Works

The script follows a 5-step pipeline to analyze and adjust subtitle timing:

1. **Parse Subtitles**: It reads the opening structural timestamps and text contents from the provided SRT file.
2. **Audio Extraction**: It isolates the designated audio channel from the provided MP4 video and exports a small temporary `.wav` file using FFmpeg.
3. **Whisper Analysis**: It uses the `faster-whisper` AI engine (running deterministically on your CPU) to transcribe spoken phrases in the audio file, ignoring known non-speech ambient tags (like "music", "applause").
4. **Fuzzy Text Matching**: It applies a sliding-window text similarity algorithm (fuzzy matching) to compare Whisper's transcription against the original SRT block text. Once a confident match is located, it locks onto the timestamps of both the audio and the SRT card.
5. **Sync & Shift**: It evaluates the time drift difference between the spoken audio and the subtitle card. If the drift exceeds a 2-second threshold, it automatically uses FFmpeg to generate a new, fully synchronized `_synced.srt` copy of your file.
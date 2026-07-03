### Summary of What We Achieved

We built a robust, fully automated Linux command-line pipeline in Python to dynamically detect and repair timeline sync errors (drift) between any video file (`.mp4`) and its corresponding subtitle file (`.srt`).

Instead of relying on manual timing adjustments, the script uses acoustic machine learning to find the true moment human speech begins, references that against the text timeline inside the subtitle file, and permanently repairs the file using `ffmpeg` if the timing is off by more than 2 seconds.

---

### How We Achieved It (Technical Breakdown)

To make this script bulletproof against varying file styles, silent openings, and AI hallucinations, we designed a multi-stage engineering pipeline:

1. **Robust Terminal Parsing:** We migrated the script's core execution from raw terminal string execution (`shell=True`) to structured array execution components (`subprocess.run(["..."])`). This ensures filenames with standard Linux terminal escaped spaces are handled natively without crashing.
2. **Deterministic Audio Analysis:** We used `faster-whisper` (running the compact, multilingual `tiny` model configuration) to analyze an extracted mono audio track. To stop the AI from generating different timings or phrases across different runs, we locked down its parameters using strict determinism (`temperature=0.0`) and disabled creative fallback loops.
* **The 15-Second Buffer:** The script checks the SRT file first and dynamically ignores any Whisper audio detection occurring more than 15 seconds before the first subtitle card is scheduled.
* **The 5-Word Minimum:** It skips single-word boundary artifacts (like `"The"` or `"You"`) and ambient audio captioning tags (like `"music"`).


4. **Sliding-Window Fuzzy Matching:** Because Whisper often groups multiple sentences together or mishears words slightly due to background audio mixing, we abandoned strict string matching. We utilized Python's native `difflib.SequenceMatcher` to run fuzzy text comparisons against a sliding group combination of the first 10 subtitle blocks. This securely anchors the true matching timeline to the closest semantic equivalent.
5. **Non-Destructive Delta Syncing:** Once a high-confidence text match is confirmed between the audio and the subtitle file, the script subtracts the two timestamps to get a precise `time_delta`. If the delta crosses the 2-second threshold, it triggers `ffmpeg` with the `-itsoffset` flag to write a cleanly shifted copy named `[filename]_synced.srt` right next to your original file.
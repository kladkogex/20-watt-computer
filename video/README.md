# Videos

YouTube episodes (one per chapter, from the short edition) and Shorts, made with
[Manim](https://www.manim.community/) and an offline neural voice ([Piper](https://github.com/rhasspy/piper)).

| Folder | What |
|---|---|
| `ep01/` | Episode 1, "A bag of parts" (neuron types): `script.json` (narration by segment), `episode.py` (animation), `episode01.en.srt` (subtitles) |
| `short01/` | Short, "Dopamine is not a pleasure signal" (vertical 1080×1920) |
| `out/` | rendered MP4s (not in git) |

## Build

    # narration (Piper, voice en_US-ryan-high), one WAV per segment + durations.json
    piper -m en_US-ryan-high.onnx --length-scale 1.12 --sentence-silence 0.35 -f ep01/audio/<segment>.wav < text
    # animation + audio, 1080p30
    docker run --rm -v "$PWD":/w -w /w/ep01 manimcommunity/manim:stable \
        manim --resolution 1920,1080 --frame_rate 30 --media_dir /w/ep01/media episode.py Episode01

Each segment's animation is timed to its narration (`durations.json`), so a new voice or language only needs
new WAV files. Other languages: translate `script.json`, synthesize with a Piper voice of that language, and
upload the result as an extra audio track of the same YouTube video.

# 0013: Derive Plex track gain from per-track loudness, not the stream's `gain`

Date: 2026-10-04

## Decision

`PlexService._extract_loudness` (`backend/app/services/plex.py`) computes `track_gain_db` as
`-18 - loudness` from the audio stream's per-track `loudness` (LUFS) attribute, rounded to 0.01 dB.
It only falls back to the stream's `gain` attribute when `loudness` is missing. `peak`, `albumGain`
and `albumPeak` are still used as Plex reports them.

## Reasoning

Plex's stream `gain` is the album gain, not the track gain. On a 24-track album, every track had
`gain` equal to `albumGain` (-11.39 dB), while `loudness` and `peak` differed per track and matched
an independent measurement of the files (pyloudnorm: -7.58 vs. Plex's -7.54 LUFS, and -6.88 vs.
-6.84). Gainbridge copied `gain` into `REPLAYGAIN_TRACK_GAIN`, so every track on an album was
written with the album's gain, off by up to about 1 dB per track.

Asking Plex to reanalyze the album (`PUT /library/metadata/{id}/analyze`) didn't change any value.
Plex's analysis queue was busy with unrelated TV jobs at the time, so this doesn't prove that
reanalysis can never fix it. Either way, `loudness` is already correct, so deriving the track gain
from it doesn't depend on Plex's behavior here. The Jellyfin service already uses the same
`-18 - LUFS` formula as a fallback.

## Consequence

Track gains written from Plex now differ per track. On the next sync, `fix` mode rewrites existing
files whose `REPLAYGAIN_TRACK_GAIN` is outside tolerance of the new value. If Plex ever starts
reporting a real per-track `gain`, it will still be ignored whenever `loudness` is present. The
two should agree to within rounding.

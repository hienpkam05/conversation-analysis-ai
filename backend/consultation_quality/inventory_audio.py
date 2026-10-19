"""Inspect local audio headers and select a deterministic pilot without copying audio."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import av


def inspect_audio(path):
    try:
        with av.open(str(path)) as container:
            streams = list(container.streams.audio)
            if not streams:
                raise ValueError("No audio stream")
            stream = streams[0]
            duration = (
                float(stream.duration * stream.time_base)
                if stream.duration is not None and stream.time_base is not None
                else container.duration / av.time_base if container.duration is not None else None
            )
            return {
                "duration_seconds": round(duration, 3) if duration is not None else None,
                "channels": stream.codec_context.channels,
                "sample_rate": stream.codec_context.sample_rate,
                "status": "ok", "error": "",
            }
    except Exception as exc:
        return {"duration_seconds": None, "channels": None, "sample_rate": None,
                "status": "error", "error": type(exc).__name__}


def bucket(duration):
    if duration is None:
        return "unknown"
    if duration < 15:
        return "under_15s"
    if duration < 60:
        return "15_to_60s"
    if duration < 180:
        return "60_to_180s"
    if duration < 600:
        return "180_to_600s"
    return "600s_plus"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve(strict=True)
    if not root.is_dir():
        parser.error("Source must be a directory")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, path in enumerate(sorted(root.rglob("*.mp3")), 1):
        info = inspect_audio(path)
        rows.append({"call_id": f"call_{index:04d}", "source_path": str(path),
                     "size_bytes": path.stat().st_size, **info,
                     "duration_group": bucket(info["duration_seconds"])})
    if not rows:
        parser.error("No MP3 files found")
    with (args.output / "inventory.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pilot = []
    for group in ("under_15s", "15_to_60s", "60_to_180s", "180_to_600s", "600s_plus"):
        candidates = sorted(
            (r for r in rows if r["status"] == "ok" and r["duration_group"] == group),
            key=lambda r: (r["duration_seconds"], r["call_id"]),
        )
        count = min(4, len(candidates))
        indices = [round(i * (len(candidates) - 1) / max(count - 1, 1)) for i in range(count)]
        pilot.extend(candidates[i] for i in indices)
    summary = {
        "audio_count": len(rows), "total_hours": round(sum(r["duration_seconds"] or 0 for r in rows) / 3600, 2),
        "header_errors": sum(r["status"] != "ok" for r in rows),
        "duration_groups": dict(Counter(r["duration_group"] for r in rows)),
        "channels": dict(Counter(str(r["channels"]) for r in rows)),
        "sample_rates": dict(Counter(str(r["sample_rate"]) for r in rows)),
        "pilot_count": len(pilot),
        "inspection": "Header metadata only; successful inspection does not prove full decode or speech quality.",
        "pilot_method": "Up to four evenly spaced durations in each duration group; no content labels inferred.",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "pilot.json").write_text(json.dumps(pilot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

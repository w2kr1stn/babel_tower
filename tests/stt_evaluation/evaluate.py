from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import jiwer


def load_sentences(script_dir: Path) -> list[dict[str, Any]]:
    sentences_path = script_dir / "sentences.json"
    if not sentences_path.exists():
        print(f"Error: {sentences_path} not found")
        sys.exit(1)
    with open(sentences_path) as f:
        data: list[dict[str, Any]] = json.load(f)
    return data


def wav_path_for_id(wav_dir: Path, sentence_id: int) -> Path:
    return wav_dir / f"sentence_{sentence_id:02d}.wav"


def transcribe(wav_path: Path, stt_url: str) -> str:
    url = f"{stt_url}/v1/audio/transcriptions"
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"model": "large-v3", "language": "de"}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, files=files, data=data)
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    text: str = result.get("text", "")
    return text.strip()


def print_report(results: list[dict[str, Any]]) -> None:
    print("\n## STT Evaluation Report\n")
    print("| ID | WER | Expected | Transcript |")
    print("|----|-----|----------|------------|")

    wer_values: list[float] = []
    for r in results:
        wer_val: float = r["wer"]
        wer_values.append(wer_val)
        wer_pct = f"{wer_val:.1%}"
        print(f"| {r['id']:2d} | {wer_pct:>6s} | {r['expected']} | {r['transcript']} |")

    if wer_values:
        avg_wer = sum(wer_values) / len(wer_values)
        print(f"\n**Average WER: {avg_wer:.1%}** ({len(wer_values)} sentences evaluated)")
    else:
        print("\nNo sentences evaluated.")


def print_recording_instructions(sentences: list[dict[str, Any]], wav_dir: Path) -> None:
    print("No WAV files found. Record sentences with these steps:\n")
    print(f"1. Create WAV files in: {wav_dir.resolve()}")
    print("2. Use 16kHz mono WAV format (matching the STT pipeline config)")
    print("3. File naming: sentence_01.wav, sentence_02.wav, ...\n")
    print("Example using ffmpeg to convert from any audio format:")
    print("  ffmpeg -i input.mp3 -ar 16000 -ac 1 sentence_01.wav\n")
    print("Sentences to record:\n")
    for s in sentences:
        sid: int = s["id"]
        print(f"  {sid:2d}. {s['expected']}")
        print(f"      -> sentence_{sid:02d}.wav")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate STT accuracy using Word Error Rate")
    parser.add_argument(
        "--stt-url",
        default="http://localhost:9000",
        help="STT service URL (default: http://localhost:9000)",
    )
    parser.add_argument(
        "--wav-dir",
        default=".",
        help="Directory containing WAV files (default: current directory)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    wav_dir = Path(args.wav_dir)
    stt_url: str = args.stt_url

    sentences = load_sentences(script_dir)

    matched: list[tuple[dict[str, Any], Path]] = []
    for s in sentences:
        wp = wav_path_for_id(wav_dir, s["id"])
        if wp.exists():
            matched.append((s, wp))

    if not matched:
        print_recording_instructions(sentences, wav_dir)
        sys.exit(0)

    print(f"Found {len(matched)}/{len(sentences)} WAV files. Evaluating against {stt_url} ...\n")

    results: list[dict[str, Any]] = []
    for sentence, wp in matched:
        try:
            transcript = transcribe(wp, stt_url)
        except httpx.HTTPError as e:
            print(f"  Error transcribing sentence {sentence['id']}: {e}")
            continue

        expected: str = sentence["expected"]
        wer_val: float = jiwer.wer(expected, transcript)

        results.append(
            {
                "id": sentence["id"],
                "expected": expected,
                "transcript": transcript,
                "wer": wer_val,
            }
        )

    print_report(results)


if __name__ == "__main__":
    main()

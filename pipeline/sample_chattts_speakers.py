import argparse
import json
from pathlib import Path

import numpy as np
from scipy.io.wavfile import write as wav_write


def score_audio(wav, sr):
    if wav.ndim > 1:
        wav = wav[:, 0]
    wav = wav.astype(np.float32)
    if np.max(np.abs(wav)) > 0:
        wav = wav / np.max(np.abs(wav))
    max_len = int(sr * 6)
    if wav.shape[0] > max_len:
        start = (wav.shape[0] - max_len) // 2
        wav = wav[start:start + max_len]
    if wav.shape[0] < int(sr * 0.5):
        return 0.0, 0.0, 0.0
    window = np.hanning(wav.shape[0])
    spectrum = np.abs(np.fft.rfft(wav * window)) ** 2
    freqs = np.fft.rfftfreq(wav.shape[0], 1.0 / sr)

    def band_energy(low, high):
        idx = (freqs >= low) & (freqs < high)
        return float(np.sum(spectrum[idx]))

    low = band_energy(80, 300)
    mid = band_energy(300, 2000)
    high = band_energy(2000, 8000)
    breathy = high / (low + mid + 1e-9)
    warm = low / (mid + high + 1e-9)
    score = breathy * warm
    return score, breathy, warm


def load_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def main():
    parser = argparse.ArgumentParser(description="Sample ChatTTS speakers for auditions.")
    parser.add_argument("--config", default="D:/Dev/stroybook/pipeline/config.json")
    parser.add_argument("--out", default="D:/Dev/stroybook/book1/_output/tts_auditions")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--per-round", type=int, default=10)
    parser.add_argument("--text", default=(
        "It is a softly bright day in the woods, warm and kind. "
        "Zak whispers, I do not like the dark. "
        "Rig says, I am here with you."
    ))
    args = parser.parse_args()

    cfg = load_config(args.config)
    tts_cfg = cfg.get("tts", {})
    model_path = tts_cfg["chattts_model_path"]
    speed_prompt = tts_cfg.get("chattts_speed", "[speed_4]")

    import ChatTTS
    chat = ChatTTS.Chat()
    ok = chat.load(source="custom", custom_path=model_path)
    if not ok:
        raise RuntimeError("ChatTTS failed to load models")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "text": args.text,
        "speed_prompt": speed_prompt,
        "samples": []
    }

    total = args.rounds * args.per_round
    sample_idx = 0
    for round_id in range(1, args.rounds + 1):
        round_dir = out_dir / f"round_{round_id:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, args.per_round + 1):
            sample_idx += 1
            spk = chat.sample_random_speaker()
            params_infer = chat.InferCodeParams(spk_emb=spk, prompt=speed_prompt)
            wavs = chat.infer(
                args.text,
                split_text=False,
                params_infer_code=params_infer,
            )
            if not wavs:
                raise RuntimeError("ChatTTS produced no audio")
            wav = np.clip(wavs[0], -1.0, 1.0)
            wav_path = round_dir / f"speaker_{i:02d}.wav"
            wav_write(str(wav_path), 24000, (wav * 32767).astype(np.int16))
            spk_path = round_dir / f"speaker_{i:02d}.txt"
            spk_path.write_text(spk, encoding="utf-8")

            score, breathy, warm = score_audio(wav, 24000)
            summary["samples"].append({
                "round": round_id,
                "index": i,
                "id": f"r{round_id:02d}_s{i:02d}",
                "wav": str(wav_path),
                "speaker": str(spk_path),
                "score": score,
                "breathy": breathy,
                "warm": warm
            })
            print(f"{sample_idx}/{total} -> {wav_path.name}")

    ranked = sorted(summary["samples"], key=lambda s: s["score"], reverse=True)
    summary["top5"] = ranked[:5]
    (out_dir / "audition_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )
    top_dir = out_dir / "top5"
    top_dir.mkdir(exist_ok=True)
    for item in summary["top5"]:
        wav_src = Path(item["wav"])
        spk_src = Path(item["speaker"])
        wav_dst = top_dir / wav_src.name
        spk_dst = top_dir / spk_src.name
        wav_dst.write_bytes(wav_src.read_bytes())
        spk_dst.write_text(spk_src.read_text(encoding="utf-8"), encoding="utf-8")

    print("Top 5 saved to", top_dir)


if __name__ == "__main__":
    main()

import os
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.io.wavfile import write as wav_write

_CHAT_TTS = None
_CHAT_TTS_SPK = {}


def speak_sapi(text, wav_path, voice="Microsoft Hazel Desktop", rate=0):
    wav_path = str(wav_path)
    # Use a here-string to keep punctuation intact
    safe_text = text.replace("'", "''")
    ps_script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('{voice}')
$synth.Rate = {rate}
$synth.SetOutputToWaveFile('{wav_path.replace("'", "''")}')
$synth.Speak(@'
{safe_text}
'@)
$synth.Dispose()
"""
    subprocess.run(["powershell", "-NoLogo", "-Command", ps_script], check=True)


def _load_chattts(model_path):
    global _CHAT_TTS
    if _CHAT_TTS is not None:
        return _CHAT_TTS
    import ChatTTS
    chat = ChatTTS.Chat()
    ok = chat.load(source="custom", custom_path=model_path)
    if not ok:
        raise RuntimeError("ChatTTS failed to load models")
    _CHAT_TTS = chat
    return chat


def _load_chattts_speaker(chat, speaker_path):
    global _CHAT_TTS_SPK
    spk_path = Path(speaker_path)
    key = str(spk_path.resolve())
    if key in _CHAT_TTS_SPK:
        return _CHAT_TTS_SPK[key]
    if spk_path.exists():
        spk = spk_path.read_text(encoding="utf-8").strip()
    else:
        spk = chat.sample_random_speaker()
        spk_path.parent.mkdir(parents=True, exist_ok=True)
        spk_path.write_text(spk, encoding="utf-8")
    _CHAT_TTS_SPK[key] = spk
    return spk


def speak_chattts(text, wav_path, model_path, speaker_path, speed_prompt="[speed_5]"):
    # ChatTTS has limited punctuation support; clean to avoid invalid chars.
    clean = (
        text.replace('"', "")
        .replace("'", "")
        .replace("…", ".")
    )
    clean = " ".join(clean.split())
    chat = _load_chattts(model_path)
    spk = _load_chattts_speaker(chat, speaker_path)
    params_infer = chat.InferCodeParams(spk_emb=spk, prompt=speed_prompt)
    wavs = chat.infer(
        clean,
        split_text=False,
        params_infer_code=params_infer,
    )
    if not wavs:
        raise RuntimeError("ChatTTS produced no audio")
    wav = wavs[0]
    wav = np.clip(wav, -1.0, 1.0)
    wav_write(str(wav_path), 24000, (wav * 32767).astype(np.int16))


def wav_duration(path):
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def concat_wavs(wav_paths, out_path, gap_seconds=0.15):
    if not wav_paths:
        return 0.0
    out_path = Path(out_path)
    with wave.open(str(wav_paths[0]), "rb") as first:
        params = first.getparams()
        out_frames = []
        out_frames.append(first.readframes(first.getnframes()))
        rate = first.getframerate()
        sampwidth = first.getsampwidth()
        nchannels = first.getnchannels()

    gap_frames = int(gap_seconds * rate)
    gap_bytes = b"\x00" * gap_frames * sampwidth * nchannels

    with wave.open(str(out_path), "wb") as out_wav:
        out_wav.setparams(params)
        out_wav.writeframes(out_frames[0])
        for wav_path in wav_paths[1:]:
            out_wav.writeframes(gap_bytes)
            with wave.open(str(wav_path), "rb") as wf:
                out_wav.writeframes(wf.readframes(wf.getnframes()))

    total = wav_duration(out_path)
    return total


def write_vtt(cues, out_path):
    def ts(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    lines = ["WEBVTT", ""]
    for start, end, text in cues:
        lines.append(f"{ts(start)} --> {ts(end)}")
        lines.append(text)
        lines.append("")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def generate_page_audio_and_vtt(page, out_dir, voice, rate, sentence_gap, tts_config):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    page_id = int(page["page"])
    sentence_files = []
    cues = []
    t = 0.0

    for idx, sentence in enumerate(page["sentences"], start=1):
        wav_path = out_dir / f"page_{page_id:02d}_sent_{idx:02d}.wav"
        engine = tts_config.get("engine", "sapi")
        if engine == "chattts":
            speak_chattts(
                sentence,
                wav_path,
                model_path=tts_config["chattts_model_path"],
                speaker_path=tts_config["chattts_speaker_path"],
                speed_prompt=tts_config.get("chattts_speed", "[speed_5]"),
            )
        else:
            speak_sapi(sentence, wav_path, voice=voice, rate=rate)
        dur = wav_duration(wav_path)
        cues.append((t, t + dur, sentence))
        t = t + dur + sentence_gap
        sentence_files.append(wav_path)

    page_wav = out_dir / f"page_{page_id:02d}.wav"
    total = concat_wavs(sentence_files, page_wav, gap_seconds=sentence_gap)

    vtt_path = out_dir / f"page_{page_id:02d}.vtt"
    write_vtt(cues, vtt_path)

    return {
        "audio_path": str(page_wav),
        "vtt_path": str(vtt_path),
        "duration": total
    }

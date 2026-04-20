import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st

from story_engine import load_story, save_story, add_scene_emotion, normalize_sentences, infer_emotion
from tts_engine import speak_sapi, speak_chattts, wav_duration, concat_wavs, write_vtt

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

STEP_LABELS = [
    "0. Project & Spec",
    "1. Script Builder",
    "2. Voice Lab",
    "3. Regression Pack",
    "4. Batch Generate",
    "5. Review & Select",
    "6. Post-process",
    "7. Mix Timeline",
    "8. Export & QC",
]


def load_json(path, default):
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def resolve_paths(config):
    output_root = Path(config.get("output_root", Path(__file__).resolve().parent / "_output"))
    state_root = output_root / "audio_pipeline"
    audio_root = state_root / "audio"
    return {
        "output_root": output_root,
        "state_root": state_root,
        "audio_root": audio_root,
        "lines_dir": audio_root / "lines",
        "pages_dir": audio_root / "pages",
        "mix_dir": audio_root / "mix",
        "subtitles_dir": state_root / "subtitles",
        "previews_dir": state_root / "previews",
        "auditions_dir": state_root / "auditions",
        "spec_path": state_root / "project_spec.json",
        "script_path": state_root / "script.json",
        "voices_path": state_root / "voice_presets.json",
        "regression_path": state_root / "regression_pack.json",
        "takes_path": state_root / "takes.json",
        "selection_path": state_root / "selection.json",
        "pages_manifest_path": state_root / "pages_manifest.json",
        "post_path": state_root / "post_process.json",
        "mix_path": state_root / "mix_plan.json",
        "qc_path": state_root / "qc_report.json",
        "story_audio_path": state_root / "story_audio.json",
        "export_dir": state_root / "exports",
    }


def default_spec(config):
    web = config.get("web", {})
    return {
        "title": web.get("title", "Storybook Audio"),
        "output_type": "audio",
        "accent": "UK Southern",
        "target_age": "5-8",
        "page_duration_min": 10,
        "page_duration_max": 18,
        "sentence_gap_s": 0.3,
        "paragraph_gap_s": 1.0,
        "page_gap_s": 1.1,
        "roles": ["Narrator", "Kid"],
        "control_priority": True,
    }


def slugify(value):
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip())
    return cleaned.strip("_").lower() or "role"


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def infer_role(text, roles):
    if not roles:
        return "Narrator"
    if len(roles) == 1:
        return roles[0]
    lower = text.lower()
    if '"' in text or " says " in lower or " whispers " in lower or " asks " in lower:
        return roles[1]
    return roles[0]


def max_words_for_role(role, roles):
    if len(roles) < 2:
        return 14
    return 10 if role == roles[1] else 15


def line_risks(text, role, roles):
    risks = []
    words = text.split()
    if len(words) > max_words_for_role(role, roles):
        risks.append("long_sentence")
    if re.search(r"[A-Z]{3,}", text):
        risks.append("all_caps")
    if re.search(r"\d", text):
        risks.append("digits")
    if re.search(r"(.)\1{3,}", text):
        risks.append("stretched")
    if "??" in text or "!!" in text:
        risks.append("strong_punct")
    return risks


def build_script_from_story(story, roles, spec):
    story = normalize_sentences(story)
    story = add_scene_emotion(story)
    lines = []
    for page in story.get("pages", []):
        page_id = int(page.get("page", 0))
        sentences = page.get("sentences") or split_sentences(page.get("text", ""))
        for idx, sentence in enumerate(sentences, start=1):
            role = infer_role(sentence, roles)
            line_id = f"p{page_id:02d}_l{idx:02d}"
            lines.append(
                {
                    "id": line_id,
                    "page": page_id,
                    "index": idx,
                    "role": role,
                    "text": sentence,
                    "emotion": infer_emotion(sentence),
                    "pause_after": spec.get("sentence_gap_s", 0.3),
                    "risk": line_risks(sentence, role, roles),
                }
            )
    return {
        "meta": {
            "source_story": str(story.get("meta", {}).get("title", "")),
            "roles": roles,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        "lines": lines,
    }


def reindex_script_lines(lines):
    lines_by_page = {}
    for line in lines:
        lines_by_page.setdefault(line["page"], []).append(line)
    new_lines = []
    for page_id in sorted(lines_by_page.keys()):
        page_lines = lines_by_page[page_id]
        page_lines.sort(key=lambda x: x["index"])
        for idx, line in enumerate(page_lines, start=1):
            line["index"] = idx
            line["id"] = f"p{page_id:02d}_l{idx:02d}"
            new_lines.append(line)
    return new_lines


def shorten_text(text):
    if "," in text:
        parts = [p.strip() for p in text.split(",", 1) if p.strip()]
        if len(parts) == 2:
            return [parts[0] + ".", parts[1]]
    if " and " in text:
        parts = [p.strip() for p in text.split(" and ", 1) if p.strip()]
        if len(parts) == 2:
            return [parts[0] + ".", parts[1]]
    return [text]


def apply_shorten(lines, roles):
    new_lines = []
    for line in lines:
        max_words = max_words_for_role(line["role"], roles)
        if len(line["text"].split()) <= max_words:
            new_lines.append(line)
            continue
        split_lines = shorten_text(line["text"])
        for idx, text in enumerate(split_lines, start=1):
            cloned = line.copy()
            cloned["text"] = text
            new_lines.append(cloned)
    return reindex_script_lines(new_lines)


def update_risks(lines, roles):
    for line in lines:
        line["risk"] = line_risks(line["text"], line["role"], roles)
        line["emotion"] = infer_emotion(line["text"])


@st.cache_data(show_spinner=False)
def list_sapi_voices():
    ps_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoLogo", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    voices = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return voices


def pick_default_voice(voices):
    if not voices:
        return ""
    for name in voices:
        lowered = name.lower()
        if "uk" in lowered or "united kingdom" in lowered or "hazel" in lowered:
            return name
    return voices[0]


def build_default_voice_presets(config, roles, spec, voices):
    tts_cfg = config.get("tts", {})
    engine = tts_cfg.get("engine", "sapi")
    if spec.get("control_priority", True):
        engine = "sapi"
    default_voice = tts_cfg.get("voice") or pick_default_voice(voices)
    presets = {"roles": {}}
    for role in roles:
        presets["roles"][role] = {
            "engine": engine,
            "voice": default_voice,
            "rate": int(tts_cfg.get("rate", 0)),
            "sentence_gap": float(tts_cfg.get("sentence_gap", spec.get("sentence_gap_s", 0.3))),
            "chattts_model_path": tts_cfg.get("chattts_model_path", ""),
            "chattts_speaker_path": tts_cfg.get(
                "chattts_speaker_path",
                str(Path(config.get("output_root", ".")) / "chattts_speaker.txt"),
            ),
            "chattts_speed": tts_cfg.get("chattts_speed", "[speed_4]"),
        }
    return presets


def ensure_voice_presets(paths, config, roles, spec):
    voices = list_sapi_voices()
    presets = load_json(paths["voices_path"], {})
    if not presets:
        presets = build_default_voice_presets(config, roles, spec, voices)
    presets.setdefault("roles", {})
    for role in roles:
        if role not in presets["roles"]:
            defaults = build_default_voice_presets(config, [role], spec, voices)
            presets["roles"][role] = defaults["roles"][role]
    return presets


def synth_line(text, out_path, role_cfg):
    engine = role_cfg.get("engine", "sapi")
    if engine == "chattts":
        model_path = role_cfg.get("chattts_model_path")
        speaker_path = role_cfg.get("chattts_speaker_path")
        if not model_path or not Path(model_path).exists():
            raise FileNotFoundError("ChatTTS model path not found")
        if not speaker_path:
            raise FileNotFoundError("ChatTTS speaker path missing")
        speak_chattts(
            text,
            out_path,
            model_path=model_path,
            speaker_path=speaker_path,
            speed_prompt=role_cfg.get("chattts_speed", "[speed_4]"),
        )
    else:
        speak_sapi(
            text,
            out_path,
            voice=role_cfg.get("voice", "Microsoft Hazel Desktop"),
            rate=int(role_cfg.get("rate", 0)),
        )


def generate_line_audio(lines, presets, out_dir, takes):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {"generated_at": datetime.now().isoformat(timespec="seconds"), "lines": {}}
    for line in lines:
        line_id = line["id"]
        role = line["role"]
        role_cfg = presets.get("roles", {}).get(role, {})
        entry = {
            "page": line["page"],
            "index": line["index"],
            "role": role,
            "text": line["text"],
            "takes": [],
            "status": "ok",
        }
        for take in range(1, takes + 1):
            role_tag = slugify(role)
            wav_path = out_dir / f"{line_id}_take_{take:02d}_{role_tag}.wav"
            try:
                synth_line(line["text"], wav_path, role_cfg)
                duration = wav_duration(wav_path)
                entry["takes"].append(
                    {"take": take, "path": str(wav_path), "duration": duration, "ok": True}
                )
            except Exception as exc:
                entry["takes"].append(
                    {"take": take, "path": str(wav_path), "duration": 0, "ok": False, "error": str(exc)}
                )
                entry["status"] = "failed"
        results["lines"][line_id] = entry
    return results


def load_lines_from_script(script):
    return script.get("lines", []) if script else []


def assemble_pages(lines, takes_data, selection, pages_dir, subtitles_dir, gap_s):
    pages_dir = Path(pages_dir)
    subtitles_dir = Path(subtitles_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    selection = selection or {}
    pages_manifest = []

    for page_id in sorted({line["page"] for line in lines}):
        page_lines = [l for l in lines if l["page"] == page_id]
        page_lines.sort(key=lambda x: x["index"])
        wavs = []
        cues = []
        t = 0.0
        for line in page_lines:
            line_id = line["id"]
            take = selection.get(line_id, 1)
            takes_entry = takes_data["lines"].get(line_id, {})
            takes = takes_entry.get("takes", [])
            chosen = next((t for t in takes if t.get("take") == take), None)
            if not chosen:
                continue
            wav_path = Path(chosen["path"])
            if not wav_path.exists():
                continue
            wavs.append(wav_path)
            dur = wav_duration(wav_path)
            cues.append((t, t + dur, line["text"]))
            t += dur + gap_s
        if not wavs:
            continue
        page_wav = pages_dir / f"page_{page_id:02d}.wav"
        total = concat_wavs(wavs, page_wav, gap_seconds=gap_s)
        vtt_path = subtitles_dir / f"page_{page_id:02d}.vtt"
        write_vtt(cues, vtt_path)
        pages_manifest.append(
            {"page": page_id, "audio": str(page_wav), "vtt": str(vtt_path), "duration": total}
        )
    return pages_manifest


def build_story_audio(story_path, pages_manifest, out_path):
    if not story_path.exists():
        return None
    story = load_story(story_path)
    pages_by_id = {p["page"]: p for p in story.get("pages", [])}
    for entry in pages_manifest:
        page = pages_by_id.get(entry["page"])
        if not page:
            continue
        page["audio"] = entry["audio"]
        page["vtt"] = entry["vtt"]
        page["duration"] = entry["duration"]
    save_story(out_path, story)
    return out_path


def build_mix_timeline(pages_manifest, page_gap_s):
    timeline = []
    cursor = 0.0
    for page in pages_manifest:
        timeline.append(
            {
                "page": page["page"],
                "start": cursor,
                "duration": page["duration"],
                "audio": page["audio"],
                "vtt": page.get("vtt"),
            }
        )
        cursor += page["duration"] + page_gap_s
    return {"timeline": timeline, "total_duration": cursor}


def run_qc(spec, script, pages_manifest):
    issues = []
    if not script.get("lines"):
        issues.append("No script lines found.")
    if not pages_manifest:
        issues.append("No page audio built.")
    min_dur = spec.get("page_duration_min", 10)
    max_dur = spec.get("page_duration_max", 18)
    for page in pages_manifest:
        dur = page.get("duration", 0)
        if dur < min_dur or dur > max_dur:
            issues.append(f"Page {page['page']:02d} duration out of range ({dur:.1f}s).")
    status = "pass" if not issues else "fail"
    return {"status": status, "issues": issues, "checked_at": datetime.now().isoformat(timespec="seconds")}


def step_project(config, paths):
    st.header("0. Project & Spec")
    spec = load_json(paths["spec_path"], default_spec(config))

    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Project title", value=spec.get("title", "Storybook Audio"))
        accent = st.selectbox("Accent", ["UK Southern", "UK RP (fallback)", "US General"], index=0)
        target_age = st.text_input("Target age", value=spec.get("target_age", "5-8"))
        roles_raw = st.text_input("Roles (comma separated)", value=", ".join(spec.get("roles", [])))
    with col2:
        page_range = st.slider(
            "Target page duration (sec)",
            min_value=6,
            max_value=24,
            value=(spec.get("page_duration_min", 10), spec.get("page_duration_max", 18)),
        )
        sentence_gap = st.slider("Sentence gap (sec)", 0.1, 0.6, float(spec.get("sentence_gap_s", 0.3)))
        page_gap = st.slider("Page gap (sec)", 0.6, 2.0, float(spec.get("page_gap_s", 1.1)))
        control_priority = st.checkbox("Control priority (stable)", value=spec.get("control_priority", True))

    if st.button("Save Spec"):
        roles = [r.strip() for r in roles_raw.split(",") if r.strip()]
        spec.update(
            {
                "title": title,
                "accent": accent,
                "target_age": target_age,
                "page_duration_min": page_range[0],
                "page_duration_max": page_range[1],
                "sentence_gap_s": sentence_gap,
                "page_gap_s": page_gap,
                "roles": roles,
                "control_priority": control_priority,
            }
        )
        save_json(paths["spec_path"], spec)
        st.success("Spec saved")

    st.subheader("Model & Paths")
    st.caption("These are read from config.json. Update them if your story or output path changed.")
    st.code(str(CONFIG_PATH), language="text")
    st.json({"story_json": config.get("story_json"), "output_root": str(paths["output_root"])})


def step_script_builder(config, paths):
    st.header("1. Script Builder")
    spec = load_json(paths["spec_path"], default_spec(config))
    roles = spec.get("roles", ["Narrator", "Kid"])

    story_path = Path(config.get("story_json", ""))
    if not story_path.exists():
        st.error("Story JSON not found. Update config.json first.")
        return

    script = load_json(paths["script_path"], {})

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Auto Split (Build Script)"):
            story = load_story(story_path)
            script = build_script_from_story(story, roles, spec)
            save_json(paths["script_path"], script)
            st.success("Script generated")
    with col2:
        if st.button("Apply Shorten (Long Sentences)"):
            if script.get("lines"):
                script["lines"] = apply_shorten(script["lines"], roles)
                update_risks(script["lines"], roles)
                save_json(paths["script_path"], script)
                st.success("Long sentences shortened")

    if not script.get("lines"):
        st.info("Generate a script to start editing.")
        return

    update_risks(script["lines"], roles)
    risk_count = sum(1 for line in script["lines"] if line.get("risk"))
    st.caption(f"Total lines: {len(script['lines'])} | Risk lines: {risk_count}")

    page_groups = {}
    for line in script["lines"]:
        page_groups.setdefault(line["page"], []).append(line)

    for page_id in sorted(page_groups.keys()):
        with st.expander(f"Page {page_id:02d}", expanded=False):
            for line in sorted(page_groups[page_id], key=lambda x: x["index"]):
                cols = st.columns([1, 1, 5])
                with cols[0]:
                    role = st.selectbox(
                        "Role",
                        roles,
                        index=roles.index(line["role"]) if line["role"] in roles else 0,
                        key=f"role_{line['id']}",
                    )
                with cols[1]:
                    pause = st.number_input(
                        "Pause",
                        min_value=0.0,
                        max_value=1.5,
                        value=float(line.get("pause_after", spec.get("sentence_gap_s", 0.3))),
                        step=0.05,
                        key=f"pause_{line['id']}",
                    )
                with cols[2]:
                    text = st.text_area(
                        "Line",
                        value=line["text"],
                        key=f"text_{line['id']}",
                        height=70,
                    )
                line["role"] = role
                line["pause_after"] = pause
                line["text"] = text.strip()
                line["risk"] = line_risks(line["text"], role, roles)
                if line["risk"]:
                    st.warning(f"Risks: {', '.join(line['risk'])}")

    if st.button("Save Script"):
        script["lines"] = reindex_script_lines(script["lines"])
        update_risks(script["lines"], roles)
        save_json(paths["script_path"], script)
        st.success("Script saved")


def step_voice_lab(config, paths):
    st.header("2. Voice Lab")
    spec = load_json(paths["spec_path"], default_spec(config))
    roles = spec.get("roles", ["Narrator", "Kid"])

    if st.button("Refresh SAPI Voices"):
        list_sapi_voices.clear()
    voices = list_sapi_voices()
    presets = ensure_voice_presets(paths, config, roles, spec)

    if "preview_paths" not in st.session_state:
        st.session_state.preview_paths = {}

    sample_text = st.text_input(
        "Preview text",
        value="It is a softly bright day in the woods, warm and kind.",
    )

    tabs = st.tabs(roles)
    for idx, role in enumerate(roles):
        role_cfg = presets["roles"].get(role, {})
        with tabs[idx]:
            engine = st.selectbox(
                "Engine",
                ["sapi", "chattts"],
                index=0 if role_cfg.get("engine") != "chattts" else 1,
                key=f"engine_{role}",
            )
            role_cfg["engine"] = engine

            if engine == "sapi":
                voice = st.selectbox(
                    "Voice",
                    voices or ["(no voices detected)"],
                    index=voices.index(role_cfg.get("voice")) if role_cfg.get("voice") in voices else 0,
                    key=f"voice_{role}",
                )
                rate = st.slider("Rate", -5, 5, int(role_cfg.get("rate", 0)), key=f"rate_{role}")
                role_cfg.update({"voice": voice, "rate": rate})
            else:
                model_path = st.text_input(
                    "ChatTTS model path", value=role_cfg.get("chattts_model_path", ""), key=f"model_{role}"
                )
                speaker_path = st.text_input(
                    "Speaker file path", value=role_cfg.get("chattts_speaker_path", ""), key=f"speaker_{role}"
                )
                speed = st.selectbox(
                    "Speed prompt",
                    ["[speed_3]", "[speed_4]", "[speed_5]"],
                    index=1,
                    key=f"speed_{role}",
                )
                role_cfg.update(
                    {
                        "chattts_model_path": model_path,
                        "chattts_speaker_path": speaker_path,
                        "chattts_speed": speed,
                    }
                )
                if model_path and not Path(model_path).exists():
                    st.warning("ChatTTS model path not found.")

            gap = st.slider(
                "Sentence gap (sec)",
                0.1,
                0.6,
                float(role_cfg.get("sentence_gap", spec.get("sentence_gap_s", 0.3))),
                key=f"gap_{role}",
            )
            role_cfg["sentence_gap"] = gap

            if st.button(f"Generate Preview ({role})", key=f"preview_{role}"):
                preview_dir = paths["previews_dir"]
                preview_dir.mkdir(parents=True, exist_ok=True)
                preview_path = preview_dir / f"preview_{slugify(role)}.wav"
                try:
                    synth_line(sample_text, preview_path, role_cfg)
                    st.session_state.preview_paths[role] = str(preview_path)
                    st.success("Preview generated")
                except Exception as exc:
                    st.error(str(exc))

            if role in st.session_state.preview_paths:
                st.audio(st.session_state.preview_paths[role])

            presets["roles"][role] = role_cfg

    if st.button("Save Presets"):
        save_json(paths["voices_path"], presets)
        st.success("Voice presets saved")


def step_regression_pack(config, paths):
    st.header("3. Regression Pack")
    spec = load_json(paths["spec_path"], default_spec(config))
    roles = spec.get("roles", ["Narrator", "Kid"])
    script = load_json(paths["script_path"], {})
    lines = load_lines_from_script(script)

    if not lines:
        st.info("Build your script first.")
        return

    max_lines = st.slider("Lines in pack", 10, 20, 12)
    if st.button("Generate Pack"):
        scored = []
        for line in lines:
            score = len(line["text"].split()) + (3 * len(line.get("risk", [])))
            if "!" in line["text"] or "?" in line["text"]:
                score += 2
            scored.append((score, line))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [item[1] for item in scored[:max_lines]]
        save_json(paths["regression_path"], {"lines": picked})
        st.success("Regression pack saved")

    pack = load_json(paths["regression_path"], {"lines": []})
    if pack.get("lines"):
        st.caption(f"Pack size: {len(pack['lines'])}")
        for line in pack["lines"]:
            st.write(f"{line['id']} ({line['role']}): {line['text']}")

    presets = load_json(paths["voices_path"], {})
    st.subheader("Quick A/B")
    line_ids = [line["id"] for line in pack.get("lines", [])]
    if line_ids:
        selected = st.selectbox("Pick a line", line_ids)
        line = next((l for l in pack["lines"] if l["id"] == selected), None)
        if line:
            role_cfg = presets.get("roles", {}).get(line["role"], {})
            if st.button("Run A/B for selected line"):
                auditions_dir = paths["auditions_dir"] / selected
                auditions_dir.mkdir(parents=True, exist_ok=True)
                variants = []
                if role_cfg.get("engine") == "chattts":
                    speeds = ["[speed_3]", "[speed_4]", "[speed_5]"]
                    for speed in speeds:
                        cfg = role_cfg.copy()
                        cfg["chattts_speed"] = speed
                        out_path = auditions_dir / f"{selected}_{speed.strip('[]')}.wav"
                        try:
                            synth_line(line["text"], out_path, cfg)
                            variants.append({"label": speed, "path": out_path})
                        except Exception as exc:
                            st.error(str(exc))
                else:
                    base_rate = int(role_cfg.get("rate", 0))
                    for offset in (-1, 0, 1):
                        rate = max(-5, min(5, base_rate + offset))
                        cfg = role_cfg.copy()
                        cfg["rate"] = rate
                        out_path = auditions_dir / f"{selected}_rate_{rate:+d}.wav"
                        try:
                            synth_line(line["text"], out_path, cfg)
                            variants.append({"label": f"rate {rate:+d}", "path": out_path})
                        except Exception as exc:
                            st.error(str(exc))

                for var in variants:
                    st.write(var["label"])
                    st.audio(str(var["path"]))


def step_batch_generate(config, paths):
    st.header("4. Batch Generate")
    spec = load_json(paths["spec_path"], default_spec(config))
    roles = spec.get("roles", ["Narrator", "Kid"])
    script = load_json(paths["script_path"], {})
    lines = load_lines_from_script(script)
    presets = load_json(paths["voices_path"], {})
    pack = load_json(paths["regression_path"], {"lines": []})

    if not lines:
        st.info("Build your script first.")
        return
    if not presets.get("roles"):
        st.info("Configure voice presets first.")
        return

    take_count = st.slider("Takes per line", 1, 3, 2)
    mode = st.selectbox("Scope", ["All lines", "Regression pack only", "Risk lines only"])
    gap_s = st.slider("Sentence gap (sec)", 0.1, 0.6, float(spec.get("sentence_gap_s", 0.3)))

    def filter_lines():
        if mode == "Regression pack only":
            pack_ids = {line["id"] for line in pack.get("lines", [])}
            return [line for line in lines if line["id"] in pack_ids]
        if mode == "Risk lines only":
            return [line for line in lines if line.get("risk")]
        return lines

    selected_lines = filter_lines()
    st.caption(f"Selected lines: {len(selected_lines)}")

    if st.button("Generate Lines"):
        with st.spinner("Generating line audio..."):
            results = generate_line_audio(selected_lines, presets, paths["lines_dir"], take_count)
            save_json(paths["takes_path"], results)
        st.success("Line audio generated")

    if st.button("Retry Failed"):
        takes = load_json(paths["takes_path"], {})
        failed_ids = [k for k, v in takes.get("lines", {}).items() if v.get("status") == "failed"]
        retry_lines = [line for line in lines if line["id"] in failed_ids]
        if not retry_lines:
            st.info("No failed lines to retry.")
        else:
            with st.spinner("Retrying failed lines..."):
                results = generate_line_audio(retry_lines, presets, paths["lines_dir"], take_count)
                existing = load_json(paths["takes_path"], {})
                existing.setdefault("lines", {}).update(results.get("lines", {}))
                save_json(paths["takes_path"], existing)
            st.success("Retries complete")

    if st.button("Assemble Pages + VTT"):
        takes = load_json(paths["takes_path"], {})
        if not takes.get("lines"):
            st.error("No line audio found. Generate lines first.")
        else:
            selection = load_json(paths["selection_path"], {})
            pages_manifest = assemble_pages(
                lines,
                takes,
                selection,
                paths["pages_dir"],
                paths["subtitles_dir"],
                gap_s,
            )
            save_json(paths["pages_manifest_path"], pages_manifest)
            story_path = Path(config.get("story_json", ""))
            build_story_audio(story_path, pages_manifest, paths["story_audio_path"])
            st.success("Pages assembled")


def step_review_select(config, paths):
    st.header("5. Review & Select")
    takes = load_json(paths["takes_path"], {})
    if not takes.get("lines"):
        st.info("Generate line audio first.")
        return

    selection = load_json(paths["selection_path"], {})
    if st.button("Auto Select Best (take 1)"):
        selection = {line_id: 1 for line_id in takes["lines"].keys()}
        save_json(paths["selection_path"], selection)
        st.success("Selection saved")

    line_ids = list(takes["lines"].keys())
    selected_line = st.selectbox("Pick a line", line_ids)
    entry = takes["lines"].get(selected_line, {})
    if entry:
        st.write(f"{selected_line} ({entry.get('role')}): {entry.get('text')}")
        take_options = [t["take"] for t in entry.get("takes", [])]
        for take in entry.get("takes", []):
            st.write(f"Take {take['take']}")
            st.audio(take["path"])
        if not take_options:
            st.warning("No takes available for this line.")
            return
        chosen = st.radio("Select take", take_options, index=0)
        if st.button("Save Selection"):
            selection[selected_line] = chosen
            save_json(paths["selection_path"], selection)
            st.success("Selection updated")


def step_post_process(config, paths):
    st.header("6. Post-process")
    defaults = {
        "noise_reduction_db": 6,
        "highpass_hz": 90,
        "presence_db": 2,
        "deesser": "light",
        "compressor_ratio": "2:1",
        "lufs_target": -16,
        "true_peak": -1,
    }
    settings = load_json(paths["post_path"], defaults)
    col1, col2 = st.columns(2)
    with col1:
        settings["noise_reduction_db"] = st.slider("Noise reduction (dB)", 0, 12, settings["noise_reduction_db"])
        settings["highpass_hz"] = st.slider("High-pass (Hz)", 60, 140, settings["highpass_hz"])
        settings["presence_db"] = st.slider("Presence boost (dB)", 0, 4, settings["presence_db"])
    with col2:
        settings["deesser"] = st.selectbox("De-esser", ["off", "light", "medium"], index=1)
        settings["compressor_ratio"] = st.selectbox("Compressor", ["off", "2:1", "3:1"], index=1)
        settings["lufs_target"] = st.number_input("LUFS target", value=settings["lufs_target"])
        settings["true_peak"] = st.number_input("True peak (dBTP)", value=settings["true_peak"])

    if st.button("Save Post-process Plan"):
        save_json(paths["post_path"], settings)
        st.success("Post-process settings saved")
    st.info("Processing is manual in your DAW; this page stores the plan and defaults.")


def step_mix_timeline(config, paths):
    st.header("7. Mix Timeline")
    spec = load_json(paths["spec_path"], default_spec(config))
    pages_manifest = load_json(paths["pages_manifest_path"], [])
    if not pages_manifest:
        st.info("Assemble pages first.")
        return

    page_gap = st.slider("Page gap (sec)", 0.6, 2.0, float(spec.get("page_gap_s", 1.1)))
    bgm_path = st.text_input("BGM path (optional)", value="")
    ducking_db = st.slider("Ducking (dB)", 6, 18, 12)

    if st.button("Build Timeline"):
        mix_plan = build_mix_timeline(pages_manifest, page_gap)
        mix_plan["bgm_path"] = bgm_path
        mix_plan["ducking_db"] = ducking_db
        save_json(paths["mix_path"], mix_plan)
        st.success("Mix plan saved")

    if st.button("Render Full Audio (no BGM)"):
        mix_dir = paths["mix_dir"]
        mix_dir.mkdir(parents=True, exist_ok=True)
        page_wavs = [Path(page["audio"]) for page in pages_manifest if Path(page["audio"]).exists()]
        if not page_wavs:
            st.error("No page audio found.")
        else:
            out_path = mix_dir / "story_full.wav"
            concat_wavs(page_wavs, out_path, gap_seconds=page_gap)
            st.success("Full audio rendered")
            st.audio(str(out_path))


def step_export_qc(config, paths):
    st.header("8. Export & QC")
    spec = load_json(paths["spec_path"], default_spec(config))
    script = load_json(paths["script_path"], {})
    pages_manifest = load_json(paths["pages_manifest_path"], [])

    if st.button("Run QC"):
        report = run_qc(spec, script, pages_manifest)
        save_json(paths["qc_path"], report)
        if report["status"] == "pass":
            st.success("QC passed")
        else:
            st.error("QC failed")
        if report["issues"]:
            for issue in report["issues"]:
                st.warning(issue)

    export_dir = paths["export_dir"]
    export_dir.mkdir(parents=True, exist_ok=True)
    mix_dir = paths["mix_dir"]
    master_path = mix_dir / "story_full.wav"

    if st.button("Export Master (WAV)"):
        if not master_path.exists():
            st.error("Full audio not found. Render it first.")
        else:
            dest = export_dir / "master.wav"
            shutil.copy2(master_path, dest)
            st.success(f"Exported: {dest}")

    st.caption("MP3 export requires ffmpeg on PATH.")
    if st.button("Export MP3"):
        if not master_path.exists():
            st.error("Full audio not found.")
            return
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            st.error("ffmpeg not found on PATH.")
            return
        dest = export_dir / "preview.mp3"
        subprocess.run([ffmpeg, "-y", "-i", str(master_path), str(dest)], check=False)
        if dest.exists():
            st.success(f"Exported: {dest}")


def main():
    st.set_page_config(page_title="Storybook Audio Pipeline", layout="wide")
    st.title("Storybook Audio Pipeline")
    config = load_config()
    paths = resolve_paths(config)

    st.sidebar.title("Steps")
    step = st.sidebar.radio("Go to", STEP_LABELS)

    if step == "0. Project & Spec":
        step_project(config, paths)
    elif step == "1. Script Builder":
        step_script_builder(config, paths)
    elif step == "2. Voice Lab":
        step_voice_lab(config, paths)
    elif step == "3. Regression Pack":
        step_regression_pack(config, paths)
    elif step == "4. Batch Generate":
        step_batch_generate(config, paths)
    elif step == "5. Review & Select":
        step_review_select(config, paths)
    elif step == "6. Post-process":
        step_post_process(config, paths)
    elif step == "7. Mix Timeline":
        step_mix_timeline(config, paths)
    elif step == "8. Export & QC":
        step_export_qc(config, paths)


if __name__ == "__main__":
    main()

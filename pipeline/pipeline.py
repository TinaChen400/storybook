import json
import os
import shutil
from pathlib import Path

from comfyui_client import (
    ensure_server,
    prepare_style_image,
    build_prompt,
    queue_prompt,
    wait_for_history,
    extract_output_images,
)
from story_engine import load_story, save_story, add_scene_emotion, normalize_sentences
from tts_engine import generate_page_audio_and_vtt


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def generate_images(config, story, output_dir):
    api_url = config["api_url"]
    start_bat = config.get("start_bat")
    if not ensure_server(api_url, start_bat=start_bat):
        raise RuntimeError("ComfyUI server not available")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    comfy_root = Path(r"D:\ComfyUI\ComfyUI")
    comfy_input = comfy_root / "input"
    comfy_output = comfy_root / "output"

    base_seed = config.get("seed", 12345)
    seed_offset = config.get("seed_offset_per_page", 0)

    for page in story["pages"]:
        page_id = int(page["page"])
        style_name = f"style_page_{page_id:02d}{Path(page['style_ref']).suffix}"
        style_image_name = prepare_style_image(
            page["style_ref"],
            comfy_input,
            style_name,
            blur_radius=config.get("style_blur_radius", 0),
        )

        prefix = f"storybook/book1/page_{page_id:02d}"
        seed = base_seed + page_id * seed_offset
        prompt = build_prompt(
            config,
            page,
            prefix,
            style_image_name,
            story.get("meta", {}),
            seed,
        )

        resp = queue_prompt(api_url, prompt)
        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"Failed to queue prompt for page {page_id}")

        history = wait_for_history(api_url, prompt_id)
        images = extract_output_images(history)
        if not images:
            raise RuntimeError(f"No images returned for page {page_id}")

        # copy first image output
        img = images[0]
        src = comfy_output / img["filename"]
        if img.get("subfolder"):
            src = comfy_output / img["subfolder"] / img["filename"]
        if not src.exists():
            raise FileNotFoundError(f"Missing output image: {src}")

        dest = output_dir / f"page_{page_id:02d}.png"
        shutil.copy2(src, dest)
        page["image"] = str(dest)


def generate_audio_and_subtitles(story, output_audio_dir, output_vtt_dir, tts_config):
    output_audio_dir = Path(output_audio_dir)
    output_vtt_dir = Path(output_vtt_dir)
    output_audio_dir.mkdir(parents=True, exist_ok=True)
    output_vtt_dir.mkdir(parents=True, exist_ok=True)

    voice = tts_config.get("voice", "Microsoft Hazel Desktop")
    rate = tts_config.get("rate", 0)
    gap = tts_config.get("sentence_gap", 0.15)

    for page in story["pages"]:
        result = generate_page_audio_and_vtt(page, output_audio_dir, voice, rate, gap, tts_config)
        audio_path = Path(result["audio_path"])
        vtt_path = Path(result["vtt_path"])

        # move vtt into subtitles dir
        target_vtt = output_vtt_dir / vtt_path.name
        if vtt_path != target_vtt:
            shutil.copy2(vtt_path, target_vtt)

        page["audio"] = str(audio_path)
        page["vtt"] = str(target_vtt)
        page["duration"] = result["duration"]


def build_web_output(story, output_root, web_src_dir):
    output_root = Path(output_root)
    web_out = output_root / "web"
    # copy static web files
    if web_out.exists():
        pass
    web_src_dir = Path(web_src_dir)
    for item in web_src_dir.iterdir():
        dest = web_out / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    assets_dir = web_out / "assets"
    img_dir = assets_dir / "images"
    audio_dir = assets_dir / "audio"
    vtt_dir = assets_dir / "vtt"

    img_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    vtt_dir.mkdir(parents=True, exist_ok=True)

    # copy assets and rewrite story paths
    def _resolve_asset(path_value, fallback_dir):
        src = Path(path_value)
        if src.is_absolute() and src.exists():
            return src
        # if relative and exists under web output
        candidate = web_out / src
        if candidate.exists():
            return candidate
        # fallback by filename
        return Path(fallback_dir) / src.name

    for page in story["pages"]:
        if "image" in page:
            img_src = _resolve_asset(page["image"], output_root / "images_360")
            img_dest = img_dir / img_src.name
            shutil.copy2(img_src, img_dest)
            page["image"] = f"assets/images/{img_dest.name}"

        if "audio" in page:
            audio_src = _resolve_asset(page["audio"], output_root / "audio")
            audio_dest = audio_dir / audio_src.name
            shutil.copy2(audio_src, audio_dest)
            page["audio"] = f"assets/audio/{audio_dest.name}"

        if "vtt" in page:
            vtt_src = _resolve_asset(page["vtt"], output_root / "subtitles")
            vtt_dest = vtt_dir / vtt_src.name
            shutil.copy2(vtt_src, vtt_dest)
            page["vtt"] = f"assets/vtt/{vtt_dest.name}"

    story_path = web_out / "story.json"
    story_path.write_text(json.dumps(story, indent=2), encoding="utf-8")
    return web_out


def run_all(config_path):
    config = load_config(config_path)
    story = load_story(config["story_json"])

    meta = story.setdefault("meta", {})
    meta["image_resolution"] = f"{config['comfyui']['width']}x{config['comfyui']['height']}"
    meta["image_aspect"] = "2:1 equirectangular"
    if "viewer" in config:
        meta["viewer"] = config["viewer"]

    story = normalize_sentences(story)
    story = add_scene_emotion(story)

    output_root = Path(config["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)

    # Step 1: 360 images
    images_out = output_root / "images_360"
    generate_images(config["comfyui"], story, images_out)

    # Step 2: audio + subtitles
    audio_out = output_root / "audio"
    vtt_out = output_root / "subtitles"
    generate_audio_and_subtitles(story, audio_out, vtt_out, config["tts"])

    # Step 3: web package
    web_out = build_web_output(story, output_root, Path(r"D:\Dev\stroybook\pipeline\web"))

    # Save enriched story
    enriched = output_root / "story_16p_full.json"
    save_story(enriched, story)

    return {
        "images": str(images_out),
        "audio": str(audio_out),
        "subtitles": str(vtt_out),
        "web": str(web_out),
        "story": str(enriched)
    }


if __name__ == "__main__":
    results = run_all(r"D:\Dev\stroybook\pipeline\config.json")
    print(json.dumps(results, indent=2))

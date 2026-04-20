import json
import os
import shutil
import time
import urllib.request
import urllib.error
from pathlib import Path

DEFAULT_TIMEOUT = 1800


def _http_get(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")


def _http_post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_server_up(api_url):
    try:
        _http_get(api_url.rstrip("/") + "/system_stats")
        return True
    except Exception:
        return False


def start_server(start_bat):
    import subprocess
    start_bat = str(start_bat)
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    with open(os.devnull, "wb") as devnull:
        subprocess.Popen([start_bat], stdout=devnull, stderr=devnull, creationflags=creationflags, shell=True)


def ensure_server(api_url, start_bat=None, timeout=120):
    if is_server_up(api_url):
        return True
    if start_bat:
        start_server(start_bat)
    start = time.time()
    while time.time() - start < timeout:
        if is_server_up(api_url):
            return True
        time.sleep(2)
    return False


def prepare_style_image(style_ref, input_dir, target_name, blur_radius=0):
    input_dir = Path(input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    src = Path(style_ref)
    if not src.exists():
        raise FileNotFoundError(f"Style ref not found: {src}")
    dest = input_dir / target_name
    if dest.exists():
        return dest.name
    if blur_radius and blur_radius > 0:
        from PIL import Image, ImageFilter
        with Image.open(src) as img:
            img = img.convert("RGB").filter(ImageFilter.GaussianBlur(radius=blur_radius))
            img.save(dest)
    else:
        shutil.copy2(src, dest)
    return dest.name


def build_prompt(config, page, output_prefix, style_image_name, meta, seed):
    prompt_base = meta.get("prompt_base", "").strip()
    negative_base = meta.get("negative_prompt", "").strip()
    skybox_prompt = config.get("skybox_prompt", "").strip()
    depth_prompt = config.get("depth_prompt", "").strip()
    background_only = "background only, empty environment, no characters, no animals"
    positive = ", ".join(
        p for p in [
            prompt_base,
            skybox_prompt,
            depth_prompt,
            background_only,
            page.get("prompt", "")
        ] if p
    )
    negative = ", ".join(
        p for p in [
            negative_base,
            config.get("no_characters_negative", "").strip(),
            config.get("panorama_negative", "").strip(),
            "text, watermark, logo"
        ] if p
    )

    prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": config["model"]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": config["width"], "height": config["height"], "batch_size": 1}},
        "5": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": config["clip_vision"]}},
        "6": {"class_type": "LoadImage", "inputs": {"image": style_image_name}},
        "7": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": config["ipadapter"]}},
        "8": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["1", 0],
                "ipadapter": ["7", 0],
                "image": ["6", 0],
                "weight": config["ipadapter_weight"],
                "weight_type": "style transfer",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": "V only",
                "clip_vision": ["5", 0]
            }
        },
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": config["steps"],
                "cfg": config["cfg"],
                "sampler_name": config["sampler"],
                "scheduler": config["scheduler"],
                "denoise": 1.0,
                "model": ["8", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0]
            }
        },
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": output_prefix}}
    }
    return prompt


def queue_prompt(api_url, prompt, client_id="storybook-pipeline"):
    payload = {"prompt": prompt, "client_id": client_id}
    return _http_post_json(api_url.rstrip("/") + "/prompt", payload)


def get_history(api_url, prompt_id):
    data = _http_get(api_url.rstrip("/") + f"/history/{prompt_id}")
    return json.loads(data)


def wait_for_history(api_url, prompt_id, timeout=DEFAULT_TIMEOUT):
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(api_url, prompt_id)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")


def extract_output_images(history_item):
    images = []
    outputs = history_item.get("outputs", {})
    for node_id, node_data in outputs.items():
        for image in node_data.get("images", []):
            images.append(image)
    return images

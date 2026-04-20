import json
from pathlib import Path


def load_story(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_story(path, story):
    Path(path).write_text(json.dumps(story, indent=2), encoding="utf-8")


def infer_emotion(text):
    t = text.lower()
    if any(k in t for k in ["afraid", "scared", "dark", "worry", "worried", "whispers"]):
        return "nervous"
    if any(k in t for k in ["laugh", "giggle", "play", "chase", "bright", "sunny"]):
        return "happy"
    if any(k in t for k in ["calm", "quiet", "soft", "slow breath", "relax"]):
        return "calm"
    if any(k in t for k in ["thanks", "friend", "together", "comfort"]):
        return "warm"
    return "gentle"


def add_scene_emotion(story):
    base = story.get("meta", {}).get("prompt_base", "")
    for page in story.get("pages", []):
        prompt = page.get("prompt", "")
        scene = prompt.replace(base, "").strip(", ")
        page["scene"] = scene if scene else prompt
        page["emotion"] = infer_emotion(page.get("text", ""))
    return story


def normalize_sentences(story):
    import re
    for page in story.get("pages", []):
        text = page.get("text", "")
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        page["sentences"] = sentences
    return story

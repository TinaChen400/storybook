# Storybook Pipeline

This pipeline builds a 16-page 360 storybook with audio and subtitles, then packages it as a web reader.

## Paths
- Config: `D:\Dev\stroybook\pipeline\config.json`
- Story input: `D:\Dev\stroybook\book1\_output\story_16p.json`
- Output root: `D:\Dev\stroybook\book1\_output`

## Run All (CLI)
```
D:\Dev\stroybook\pipeline\run_pipeline.bat
```

## Streamlit UI
```
D:\Dev\stroybook\pipeline\run_streamlit.bat
```

## Web Viewer
After generation, open the web build from a local server:
```
cd /d D:\Dev\stroybook\book1\_output\web
D:\ComfyUI\venv\Scripts\python.exe -m http.server 8090
```
Then visit `http://localhost:8090`.

## Notes
- ComfyUI server must be running on `http://127.0.0.1:8188`.
- TTS uses Windows SAPI voice `Microsoft Hazel Desktop`.
- 360 images are generated at 1024x512.

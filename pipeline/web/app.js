const state = {
  story: null,
  index: 0,
  cues: [],
  viewer: null,
  auto: false,
  lastCueIndex: -1,
};

const DEFAULT_VIEWER = {
  pitch: 0,
  yaw: 0,
  hfov: 80,
  minHfov: 60,
  maxHfov: 95,
  minPitch: -35,
  maxPitch: 35,
};

const audioEl = document.getElementById('audio');
const flipAudio = document.getElementById('flipAudio');
const pageText = document.getElementById('pageText');
const pageIndicator = document.getElementById('pageIndicator');

function parseTimestamp(ts) {
  const parts = ts.replace(',', '.').split(':');
  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const s = parseFloat(parts[2]);
  return h * 3600 + m * 60 + s;
}

function parseVtt(text) {
  const lines = text.split(/\r?\n/);
  const cues = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.includes('-->')) {
      const [start, end] = line.split('-->').map(s => s.trim());
      const cueText = lines[i + 1] || '';
      cues.push({
        start: parseTimestamp(start),
        end: parseTimestamp(end),
        text: cueText.trim()
      });
      i += 1;
    }
  }
  return cues;
}

async function loadVtt(url) {
  const res = await fetch(url);
  if (!res.ok) {
    return [];
  }
  const text = await res.text();
  return parseVtt(text);
}

function renderCues(cues) {
  pageText.innerHTML = '';
  cues.forEach((cue, idx) => {
    const div = document.createElement('div');
    div.className = 'cue';
    div.dataset.index = idx;
    div.textContent = cue.text;
    pageText.appendChild(div);
  });
}

function updateCueHighlight(time) {
  if (!state.cues.length) {
    return;
  }
  let activeIndex = -1;
  for (let i = 0; i < state.cues.length; i++) {
    const cue = state.cues[i];
    if (time >= cue.start && time <= cue.end) {
      activeIndex = i;
      break;
    }
  }
  const nodes = pageText.querySelectorAll('.cue');
  nodes.forEach((node, idx) => {
    const isActive = idx === activeIndex;
    node.classList.toggle('active', isActive);
    if (isActive && state.lastCueIndex !== activeIndex) {
      node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  state.lastCueIndex = activeIndex;
}

function getViewerOptions() {
  const metaViewer = state.story && state.story.meta && state.story.meta.viewer
    ? state.story.meta.viewer
    : {};
  return { ...DEFAULT_VIEWER, ...metaViewer };
}

function applyViewerDefaults(options) {
  if (!state.viewer) {
    return;
  }
  const opts = options || getViewerOptions();
  if (opts.minPitch !== undefined && opts.maxPitch !== undefined) {
    state.viewer.setPitchBounds([opts.minPitch, opts.maxPitch]);
  }
  if (opts.minHfov !== undefined && opts.maxHfov !== undefined) {
    state.viewer.setHfovBounds([opts.minHfov, opts.maxHfov]);
  }
  if (opts.pitch !== undefined) {
    state.viewer.setPitch(opts.pitch);
  }
  if (opts.yaw !== undefined) {
    state.viewer.setYaw(opts.yaw);
  }
  if (opts.hfov !== undefined) {
    state.viewer.setHfov(opts.hfov);
  }
}

function initViewer(imagePath) {
  const options = getViewerOptions();
  if (state.viewer) {
    state.viewer.setPanorama(imagePath);
    applyViewerDefaults(options);
    return;
  }
  state.viewer = pannellum.viewer('viewer', {
    type: 'equirectangular',
    panorama: imagePath,
    autoLoad: true,
    compass: false,
    showZoomCtrl: true,
    showFullscreenCtrl: true,
    pitch: options.pitch,
    yaw: options.yaw,
    hfov: options.hfov,
    minPitch: options.minPitch,
    maxPitch: options.maxPitch,
    minHfov: options.minHfov,
    maxHfov: options.maxHfov,
  });
}

async function renderPage(index) {
  const pages = state.story.pages;
  if (index < 0 || index >= pages.length) {
    return;
  }
  state.index = index;
  const page = pages[index];

  pageIndicator.textContent = `Page ${page.page} / ${pages.length}`;
  initViewer(page.image);

  if (page.vtt) {
    state.cues = await loadVtt(page.vtt);
    renderCues(state.cues);
  } else {
    state.cues = [];
    pageText.textContent = page.text || '';
  }

  if (page.audio) {
    audioEl.src = page.audio;
    audioEl.load();
  }
}

function bindControls() {
  document.getElementById('prevBtn').addEventListener('click', () => {
    if (flipAudio) {
      flipAudio.currentTime = 0;
      flipAudio.play();
    }
    renderPage(state.index - 1);
  });
  document.getElementById('nextBtn').addEventListener('click', () => {
    if (flipAudio) {
      flipAudio.currentTime = 0;
      flipAudio.play();
    }
    renderPage(state.index + 1);
  });
  document.getElementById('playBtn').addEventListener('click', () => {
    if (audioEl.paused) {
      audioEl.play();
    } else {
      audioEl.pause();
    }
  });
  document.getElementById('autoBtn').addEventListener('click', (e) => {
    state.auto = !state.auto;
    e.currentTarget.classList.toggle('active', state.auto);
    if (state.auto && audioEl.paused) {
      audioEl.play();
    }
  });
  document.getElementById('resetBtn').addEventListener('click', () => {
    applyViewerDefaults();
  });

  audioEl.addEventListener('timeupdate', () => {
    updateCueHighlight(audioEl.currentTime);
  });

  audioEl.addEventListener('ended', async () => {
    if (!state.auto) {
      return;
    }
    if (state.index + 1 < state.story.pages.length) {
      if (flipAudio) {
        flipAudio.currentTime = 0;
        flipAudio.play();
      }
      await renderPage(state.index + 1);
      audioEl.play();
    }
  });
}

async function init() {
  const res = await fetch('story.json');
  state.story = await res.json();
  bindControls();
  renderPage(0);
}

init();

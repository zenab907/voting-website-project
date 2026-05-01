/**
 * DEMS Face Recognition — Frontend (Upgraded v3)
 *
 * Uses face-api.js to:
 *   1. Open camera
 *   2. Detect face & extract 128-D descriptor (Float32Array → plain array)
 *   3. POST { national_id, descriptor: [128 floats] } to /api/face/check/
 *   4. Handle responses: registered / verified / mismatch
 *
 * Cross-device: embeddings are stored in the central database, NOT localStorage.
 * No images are ever sent to or stored by the server.
 */

const FACE_API_CDN = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
const MODELS_URL   = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/weights';

let faceAPILoaded      = false;
let videoStream        = null;
let capturedDescriptor = null;

// ── Load face-api.js + models dynamically ─────────────────────────────────────
async function loadFaceAPI() {
  if (faceAPILoaded) return true;
  if (window.faceapi) {
    faceAPILoaded = true;
    return true;
  }
  return new Promise((resolve, reject) => {
    const script    = document.createElement('script');
    script.src      = FACE_API_CDN;
    script.onload   = async () => {
      try {
        await Promise.all([
          faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_URL),
          faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODELS_URL),
          faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL),
        ]);
        faceAPILoaded = true;
        resolve(true);
      } catch (e) {
        reject(new Error('Failed to load face recognition models: ' + e.message));
      }
    };
    script.onerror = () => reject(new Error('Failed to load face-api.js from CDN.'));
    document.head.appendChild(script);
  });
}

// ── Camera management ─────────────────────────────────────────────────────────
async function startCamera() {
  const btn     = document.getElementById('start-camera-btn');
  const initial = document.getElementById('face-initial-state');
  const wrapper = document.getElementById('face-video-wrapper');
  const actions = document.getElementById('face-actions');

  if (btn) { btn.disabled = true; btn.textContent = '⏳ Loading…'; }
  setFaceStatus('info', '⏳ Loading face recognition models…');

  try {
    await loadFaceAPI();
    setFaceStatus('info', '📷 Accessing camera…');

    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
    });

    const video    = document.getElementById('face-video');
    video.srcObject = videoStream;
    await new Promise(r => { video.onloadedmetadata = r; });
    await video.play();

    if (initial) initial.style.display = 'none';
    if (wrapper) wrapper.style.display = 'block';
    if (actions) actions.style.display = 'flex';
    setFaceStatus('info', '👤 Position your face inside the circle and click Capture');

  } catch (err) {
    console.error('Camera/model error:', err);
    const msg = err.name === 'NotAllowedError'
      ? '🚫 Camera permission denied. Please allow camera access and reload.'
      : err.name === 'NotFoundError'
        ? '📷 No camera found. Please connect a camera and try again.'
        : `❌ Error: ${err.message}`;
    setFaceStatus('error', msg);
    if (btn) { btn.disabled = false; btn.textContent = '📷 Start Camera'; }
  }
}

function cancelCamera() {
  stopStream();
  capturedDescriptor = null;
  const initial = document.getElementById('face-initial-state');
  const wrapper = document.getElementById('face-video-wrapper');
  const actions = document.getElementById('face-actions');
  if (initial) initial.style.display = 'block';
  if (wrapper) wrapper.style.display = 'none';
  if (actions) actions.style.display = 'none';
  setFaceStatus('', '');
}

function retakeFace() {
  capturedDescriptor = null;
  const preview       = document.getElementById('face-preview-wrapper');
  const wrapper       = document.getElementById('face-video-wrapper');
  const actions       = document.getElementById('face-actions');
  const retakeActions = document.getElementById('face-retake-actions');
  if (preview)       preview.style.display       = 'none';
  if (wrapper)       wrapper.style.display       = 'block';
  if (actions)       actions.style.display       = 'flex';
  if (retakeActions) retakeActions.style.display = 'none';

  // Restart stream if it was stopped
  if (!videoStream) {
    startCamera();
  } else {
    setFaceStatus('info', '👤 Position your face inside the circle');
  }
}

function stopStream() {
  if (videoStream) {
    videoStream.getTracks().forEach(t => t.stop());
    videoStream = null;
  }
}

// ── Capture & extract 128-D descriptor ───────────────────────────────────────
async function captureFace() {
  const video      = document.getElementById('face-video');
  const canvas     = document.getElementById('face-canvas');
  const captureBtn = document.getElementById('capture-btn');

  if (!video || !canvas) return;

  captureBtn.disabled    = true;
  captureBtn.textContent = '⏳ Detecting…';
  setFaceStatus('info', '🔍 Detecting face…');

  try {
    // Snapshot current video frame for preview
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    // Detect face and extract 128-D descriptor
    const detection = await faceapi
      .detectSingleFace(
        video,
        new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 })
      )
      .withFaceLandmarks(true)
      .withFaceDescriptor();

    if (!detection) {
      setFaceStatus('error',
        '❌ No face detected. Try: better lighting, face camera directly, remove glasses.');
      captureBtn.disabled    = false;
      captureBtn.textContent = '📸 Capture Face';
      return;
    }

    // Float32Array(128) → plain JS array (JSON-serializable)
    capturedDescriptor = Array.from(detection.descriptor);

    // Show preview snapshot; hide live camera
    stopStream();
    const wrapper       = document.getElementById('face-video-wrapper');
    const preview       = document.getElementById('face-preview-wrapper');
    const actions       = document.getElementById('face-actions');
    const retakeActions = document.getElementById('face-retake-actions');
    if (wrapper)       wrapper.style.display       = 'none';
    if (preview)       preview.style.display       = 'block';
    if (actions)       actions.style.display       = 'none';
    if (retakeActions) retakeActions.style.display = 'flex';

    setFaceStatus('success', '✅ Face captured! Click "Verify Identity" to continue.');

  } catch (err) {
    console.error('Capture error:', err);
    setFaceStatus('error', `❌ Detection error: ${err.message}`);
  } finally {
    captureBtn.disabled    = false;
    captureBtn.textContent = '📸 Capture Face';
  }
}

// ── Send embedding to backend ─────────────────────────────────────────────────
async function lookupVoter() {
  const nationalIdEl = document.getElementById('national-id-input');
  const lookupBtn    = document.getElementById('lookup-btn');
  const lookupText   = document.getElementById('lookup-text');
  const spinner      = document.getElementById('lookup-spinner');

  const nationalId = nationalIdEl ? nationalIdEl.value.trim() : '';

  // Validate NID
  if (!nationalId || !/^\d{14}$/.test(nationalId)) {
    showNidError('Please enter a valid 14-digit National ID.');
    return;
  }

  // Ensure face was captured
  if (!capturedDescriptor || capturedDescriptor.length !== 128) {
    showNidError('Please capture your face first.');
    return;
  }

  if (lookupBtn)   lookupBtn.disabled   = true;
  if (lookupText)  lookupText.style.display = 'none';
  if (spinner)     spinner.style.display    = 'inline';

  try {
    const resp = await fetch('/api/face/check/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Only sending 128 floats — no image data ever leaves the browser
      body: JSON.stringify({ national_id: nationalId, descriptor: capturedDescriptor })
    });

    const data = await resp.json();

    if (data.success && data.status === 'verified') {
      setFaceStatus('success', data.message || 'Identity verified ✓');
      setTimeout(() => { window.location.href = '/vote/'; }, 1200);

    } else if (data.success && data.status === 'registered') {
      // Face registered for first time — do NID login to create session
      setFaceStatus('success', data.message || 'Face registered ✓ Logging in…');
      await doNationalIdLogin(nationalId);

    } else if (data.status === 'mismatch') {
      setFaceStatus('error', data.message_en || 'Face mismatch. Please retake and try again.');

    } else {
      showNidError(data.error || 'Verification failed. Please try again.');
    }

  } catch (err) {
    console.error('API error:', err);
    showNidError('Network error. Please check your connection and try again.');
  } finally {
    if (lookupBtn)  lookupBtn.disabled   = false;
    if (lookupText) lookupText.style.display = 'inline';
    if (spinner)    spinner.style.display    = 'none';
  }
}

// Fallback: NID-only login after first-time face registration
async function doNationalIdLogin(nationalId) {
  try {
    const resp = await fetch('/api/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ national_id: nationalId })
    });
    const data = await resp.json();
    if (data.success) {
      window.location.href = '/vote/';
    } else {
      showNidError(data.error || 'Login failed. Please try again.');
    }
  } catch (e) {
    showNidError('Network error during login.');
  }
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function setFaceStatus(type, msg) {
  const el = document.getElementById('face-status');
  if (!el) return;
  el.innerHTML  = msg;
  el.className  = 'face-status';
  if (type === 'error')   el.classList.add('face-status-error');
  if (type === 'success') el.classList.add('face-status-success');
  if (type === 'info')    el.classList.add('face-status-info');
}

function showNidError(msg) {
  const el = document.getElementById('nid-error');
  if (el) {
    el.textContent    = msg;
    el.style.display  = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 6000);
  }
}

// Cleanup camera on page unload
window.addEventListener('beforeunload', stopStream);

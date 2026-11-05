// Flip through a talk's PDF in the browser. The PDF is the only copy of the
// slides: nothing is pre-rendered. Without JavaScript, or if this fails, the
// page still has its download link.
import * as pdfjs from '/assets/pdfjs/pdf.min.mjs';

pdfjs.GlobalWorkerOptions.workerSrc = '/assets/pdfjs/pdf.worker.min.mjs';

const root = document.getElementById('flip');
const frame = root.querySelector('.flip__frame');
const canvas = root.querySelector('canvas');
const status = root.querySelector('.flip__status');
const count = root.querySelector('[aria-live]');
const prev = root.querySelector('[data-go="-1"]');
const next = root.querySelector('[data-go="1"]');
let doc;
let current = 1;
let task = null;

status.textContent = 'Loading slides…';

async function draw(number) {
  current = number;
  count.textContent = `${number} / ${doc.numPages}`;
  prev.disabled = number === 1;
  next.disabled = number === doc.numPages;
  if (task) task.cancel();
  const page = await doc.getPage(number);
  if (current !== number) return;
  const size = page.getViewport({ scale: 1 });
  const pixels = Math.min(frame.clientWidth * Math.min(devicePixelRatio || 1, 2), 1920);
  const viewport = page.getViewport({ scale: pixels / size.width });
  // Draw off screen and copy across, so a flip never shows a half-drawn slide.
  const buffer = document.createElement('canvas');
  buffer.width = Math.floor(viewport.width);
  buffer.height = Math.floor(viewport.height);
  task = page.render({ canvasContext: buffer.getContext('2d'), viewport });
  try {
    await task.promise;
  } catch (error) {
    if (error.name === 'RenderingCancelledException') return;
    throw error;
  }
  if (current !== number) return;
  canvas.width = buffer.width;
  canvas.height = buffer.height;
  canvas.getContext('2d').drawImage(buffer, 0, 0);
  canvas.setAttribute('aria-label', `Slide ${number} of ${doc.numPages}`);
  frame.style.aspectRatio = `${size.width} / ${size.height}`;
  status.hidden = true;
  if (number < doc.numPages) doc.getPage(number + 1);
}

function go(number) {
  if (doc && number >= 1 && number <= doc.numPages) draw(number);
}

prev.addEventListener('click', () => go(current - 1));
next.addEventListener('click', () => go(current + 1));
addEventListener('keydown', (event) => {
  if (event.key === 'ArrowLeft') go(current - 1);
  if (event.key === 'ArrowRight') go(current + 1);
});
let startX = null;
frame.addEventListener('pointerdown', (event) => { startX = event.clientX; });
frame.addEventListener('pointerup', (event) => {
  if (startX === null) return;
  const moved = event.clientX - startX;
  startX = null;
  if (Math.abs(moved) > 40) go(current + (moved < 0 ? 1 : -1));
});

try {
  doc = await pdfjs.getDocument({
    url: root.dataset.pdf,
    cMapUrl: '/assets/pdfjs/cmaps/',
    cMapPacked: true,
    standardFontDataUrl: '/assets/pdfjs/standard_fonts/',
  }).promise;
  await draw(1);
} catch (error) {
  console.error(error);
  status.hidden = false;
  status.textContent = "Couldn't show the slides here. Download the PDF instead.";
}

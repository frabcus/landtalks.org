#!/usr/bin/env node
// Crop each picture in assets/emoji/ to its artwork's real width, so narrow
// emoji don't have blank space either side. The height stays as it is, so they
// all stay in proportion. Safe to re-run. Needs Playwright:
//   npx playwright install firefox && NODE_PATH=$(npm root -g) node trim_emoji.js
const fs = require('fs');
const path = require('path');
const http = require('http');
const { firefox } = require('playwright');

const folder = path.join(__dirname, 'assets/emoji');

(async () => {
  const server = http.createServer((request, response) => {
    if (request.url === '/') return response.end('<!DOCTYPE html>');
    const file = path.join(folder, path.basename(request.url));
    if (!fs.existsSync(file)) { response.statusCode = 404; return response.end(); }
    response.setHeader('Content-Type', 'image/svg+xml');
    response.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/`;
  const browser = await firefox.launch();
  const page = await browser.newPage();
  await page.goto(base);
  for (const name of fs.readdirSync(folder).filter((file) => file.endsWith('.svg'))) {
    const file = path.join(folder, name);
    const svg = fs.readFileSync(file, 'utf8');
    const match = svg.match(/viewBox="([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)[ ,]+([-\d.]+)"/);
    if (!match) { console.log(`${name}: no viewBox, left alone`); continue; }
    const [x, y, width, height] = match.slice(1).map(Number);
    const range = await page.evaluate(async ({ url, ratio }) => {
      const image = new Image();
      image.src = url;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.height = 768;
      canvas.width = Math.round(768 * ratio);
      const context = canvas.getContext('2d');
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
      let left = canvas.width;
      let right = 0;
      for (let row = 0; row < canvas.height; row++) {
        for (let column = 0; column < canvas.width; column++) {
          if (data[(row * canvas.width + column) * 4 + 3] > 16) {
            left = Math.min(left, column);
            right = Math.max(right, column + 1);
          }
        }
      }
      return [left / canvas.width, right / canvas.width];
    }, { url: base + name, ratio: width / height });
    if (range[1] <= range[0]) { console.log(`${name}: looks empty, left alone`); continue; }
    const newX = +(x + range[0] * width).toFixed(2);
    const newWidth = +((range[1] - range[0]) * width).toFixed(2);
    fs.writeFileSync(file, svg.replace(match[0], `viewBox="${newX} ${y} ${newWidth} ${height}"`));
    console.log(`${name}: width ${width} -> ${newWidth}`);
  }
  await browser.close();
  server.close();
})().catch((error) => { console.error(error); process.exit(1); });

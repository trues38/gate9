const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const sizes = [72, 96, 128, 144, 152, 192, 384, 512];

// G9 Logo SVG with neon cyan accent
const createSvg = (size) => `
<svg width="${size}" height="${size}" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0f1a"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00f5ff"/>
      <stop offset="100%" style="stop-color:#a855f7"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="512" height="512" rx="100" fill="url(#bg)"/>

  <!-- Outer ring glow -->
  <circle cx="256" cy="256" r="180" fill="none" stroke="url(#accent)" stroke-width="6" opacity="0.3" filter="url(#glow)"/>

  <!-- G9 Text -->
  <text x="256" y="290" font-family="Arial Black, sans-serif" font-size="200" font-weight="900" text-anchor="middle" fill="url(#accent)" filter="url(#glow)">G9</text>

  <!-- Decorative dots -->
  <circle cx="130" cy="130" r="8" fill="#00f5ff" opacity="0.6"/>
  <circle cx="382" cy="130" r="8" fill="#a855f7" opacity="0.6"/>
  <circle cx="130" cy="382" r="8" fill="#a855f7" opacity="0.6"/>
  <circle cx="382" cy="382" r="8" fill="#00f5ff" opacity="0.6"/>
</svg>
`;

async function generateIcons() {
  const iconsDir = path.join(__dirname, 'public', 'icons');

  for (const size of sizes) {
    const svg = Buffer.from(createSvg(size));
    const outputPath = path.join(iconsDir, `icon-${size}x${size}.png`);

    await sharp(svg)
      .resize(size, size)
      .png()
      .toFile(outputPath);

    console.log(`Generated: icon-${size}x${size}.png`);
  }

  // Generate favicon.ico (use 32x32)
  const faviconSvg = Buffer.from(createSvg(32));
  await sharp(faviconSvg)
    .resize(32, 32)
    .png()
    .toFile(path.join(__dirname, 'public', 'favicon.png'));

  console.log('Generated: favicon.png');

  // Generate Apple touch icon
  const appleSvg = Buffer.from(createSvg(180));
  await sharp(appleSvg)
    .resize(180, 180)
    .png()
    .toFile(path.join(__dirname, 'public', 'apple-touch-icon.png'));

  console.log('Generated: apple-touch-icon.png');
}

generateIcons().catch(console.error);

import { defineConfig } from 'astro/config';

// three's DRACOLoader declares its default decoder URLs at module level with `new URL(…, import.meta.url)`,
// so Vite emits ~1.2 MB of decoders into dist/_astro that the site never fetches: it sets its own
// decoder path (public/draco). Blank those defaults so nothing unused ships.
const noDefaultDracoUrls = {
  name: 'no-default-draco-urls',
  enforce: 'pre',
  transform(code, id) {
    if (!id.includes('DRACOLoader.js')) return null;
    return code.replace(/new URL\(\s*'\.\.\/libs\/draco\/[^']+',\s*import\.meta\.url\s*\)\.toString\(\)/g, "''");
  },
};

// GitHub Pages serves the project at /blender-kiln/; nothing is deployed without the owner's go-ahead.
export default defineConfig({
  site: 'https://elithril.github.io',
  base: '/blender-kiln',
  trailingSlash: 'ignore',
  vite: { plugins: [noDefaultDracoUrls] },
});

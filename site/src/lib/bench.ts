import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Marked } from 'marked';
import GithubSlugger from 'github-slugger';

const REPO = 'https://github.com/elithril/blender-kiln';

/** docs/benchmarks.md, rendered at build time: the repository document stays the single source, so a
 *  release that updates it updates this page with no redesign. Only two things change on the way:
 *  links relative to docs/ point at GitHub, and em/en dashes become hyphens (the site carries none). */
export function benchmarks() {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const raw = readFileSync(resolve(process.cwd(), '../docs/benchmarks.md'), 'utf8');
  const lines = raw.split('\n');
  const title = (lines.find((l) => l.startsWith('# ')) ?? '# Benchmarks').slice(2);
  // drop the H1 and the document's own link list (the page draws its contents from the headings)
  let body = lines.filter((l) => !l.startsWith('# ')).join('\n');
  body = body.replace(/\n- \[How it is measured\][\s\S]*?\n(?=\n## )/, '\n');
  // no dash used as punctuation on the site: in a table cell "v1 \u2014 before the loop" becomes a label
  // ("v1: before the loop"); in prose, an aside between dashes becomes an aside between commas
  body = body.split('\n').map((l) => l.startsWith('|')
    ? l.replace(/\s+\u2014\s+/g, ': ')
    : l.replace(/\s+\u2014\s+/g, ', ')).join('\n').replace(/\u2014/g, '-').replace(/\u2013/g, '-');

  const slugger = new GithubSlugger();
  const toc: { id: string; text: string }[] = [];
  const marked = new Marked({
    gfm: true,
    renderer: {
      heading({ tokens, depth, text }) {
        const id = slugger.slug(text);
        if (depth === 2) toc.push({ id, text: text.replace(/[*_`]/g, '') });
        return `<h${depth} id="${id}">${this.parser.parseInline(tokens)}</h${depth}>\n`;
      },
      link({ href, title: t, tokens }) {
        let url = href;
        if (url.startsWith('../')) url = `${REPO}/blob/main/${url.slice(3)}`;
        const inner = this.parser.parseInline(tokens);
        const ext = /^https?:/.test(url);
        return `<a href="${url}"${t ? ` title="${t}"` : ''}${ext ? ' rel="noopener"' : ''}>${inner}</a>`;
      },
    },
  });
  // bench sheets are served from the site (public/assets/img/bench), three with their empty grid cells
  // painted in the page grey (assets-src/bench/fill_empty_cells.py); one without a local copy stays on GitHub
  body = body.replace(/https:\/\/raw\.githubusercontent\.com\/elithril\/blender-kiln\/bench-results\/[^"')\s]+?\/([\w.-]+\.webp)/g,
    (url, file) => (existsSync(resolve(process.cwd(), 'public/assets/img/bench', file)) ? `${base}/assets/img/bench/${file}` : url));
  let html = marked.parse(body) as string;
  // bench sheets open at full resolution: on a phone they are too small to read in the column
  html = html.replace(/<img([^>]*?)src="([^"]+)"([^>]*)>/g, (m, a, src, b) => `<a class="sheet" href="${src}" target="_blank" rel="noopener"><img${a}src="${src}"${b}></a>`);
  // numbers never split from their unit
  html = html.replace(/(\d) %/g, '$1&nbsp;%').replace(/(\d) (MB|KB|kB|cm|mm|min)\b/g, '$1&nbsp;$2');
  return { title: title.replace(/\s+\u2014\s+/g, ': '), html, toc, source: `${REPO}/blob/main/docs/benchmarks.md` };
}

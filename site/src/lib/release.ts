import site from '../content/site.json';

export interface Release { version: string; title: string; url: string; date: string; source: 'github' | 'content' }

/** The latest GitHub release, read at build time: the release notes are the source of truth for
 *  "what's new". Falls back to site.json when offline or rate-limited, and says which it used. */
export async function latestRelease(): Promise<Release> {
  const fallback: Release = { ...site.release, source: 'content' };
  try {
    const headers: Record<string, string> = { Accept: 'application/vnd.github+json', 'User-Agent': 'blender-kiln-site' };
    if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
    const res = await fetch('https://api.github.com/repos/elithril/blender-kiln/releases/latest', { headers, signal: AbortSignal.timeout(8000) });
    if (!res.ok) return fallback;
    const r = await res.json();
    // "blender-kiln 2.2 — /kiln animate" -> "/kiln animate"; the page carries no em dash
    const title = String(r.name ?? '').split(/\s+[—–-]\s+/).pop()?.trim() || fallback.title;
    return { version: String(r.tag_name).replace(/^v/, ''), title, url: r.html_url, date: String(r.published_at).slice(0, 10), source: 'github' };
  } catch {
    return fallback;
  }
}

/** Stars on the repository, read at build time. null when GitHub does not answer: the page then shows
 *  no count rather than a stale or invented one. The site workflow rebuilds daily to keep it fresh. */
export async function repoStars(): Promise<number | null> {
  try {
    const headers: Record<string, string> = { Accept: 'application/vnd.github+json', 'User-Agent': 'blender-kiln-site' };
    if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
    const res = await fetch('https://api.github.com/repos/elithril/blender-kiln', { headers, signal: AbortSignal.timeout(8000) });
    if (!res.ok) return null;
    const n = (await res.json()).stargazers_count;
    return typeof n === 'number' ? n : null;
  } catch {
    return null;
  }
}

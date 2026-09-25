"""Stack detection (P1.3): hosting, framework and backend from one homepage response, in code. The fix plan uses it to
pick the recipe for the file the owner actually has (vercel.json, netlify.toml, next.config.js, public/_headers...).

Signals are public response headers and HTML markers only. Each answer carries the evidence that decided it, and an
unknown part stays None rather than a guess.
"""

import re
from urllib.parse import urlsplit

HOSTING = ("vercel", "netlify", "cloudflare", "render", "github_pages")
FRAMEWORKS = ("nextjs", "astro", "lovable", "bolt", "vite", "nuxt", "sveltekit", "wordpress")
BACKENDS = ("supabase", "firebase")
LABEL = {
    "vercel": "Vercel", "netlify": "Netlify", "cloudflare": "Cloudflare Pages", "render": "Render", "github_pages": "GitHub Pages",
    "nextjs": "Next.js", "astro": "Astro", "lovable": "Lovable (Vite and React)", "bolt": "Bolt (Vite and React)", "vite": "Vite",
    "nuxt": "Nuxt", "sveltekit": "SvelteKit", "wordpress": "WordPress", "supabase": "Supabase", "firebase": "Firebase",
}


def _host(headers: dict, url: str) -> tuple[str | None, str]:
    h = {k.lower(): str(v).lower() for k, v in headers.items()}
    host = (urlsplit(url).hostname or "").lower()
    server = h.get("server", "")
    if "x-vercel-id" in h or "x-vercel-cache" in h or server == "vercel" or host.endswith(".vercel.app"):
        return "vercel", "x-vercel-id header" if "x-vercel-id" in h else "server: Vercel" if server == "vercel" else "vercel.app address"
    if "x-nf-request-id" in h or server == "netlify" or host.endswith(".netlify.app"):
        return "netlify", "x-nf-request-id header" if "x-nf-request-id" in h else "server: Netlify" if server == "netlify" else "netlify.app address"
    if "x-render-origin-server" in h or "rndr-id" in h or host.endswith(".onrender.com"):
        return "render", "Render response header" if "rndr-id" in h or "x-render-origin-server" in h else "onrender.com address"
    if host.endswith(".github.io") or server == "github.com":
        return "github_pages", "GitHub Pages"
    if host.endswith(".pages.dev") or ("cf-ray" in h and server == "cloudflare" and "x-powered-by" not in h):
        return "cloudflare", "pages.dev address" if host.endswith(".pages.dev") else "Cloudflare serves the site (cf-ray)"
    return None, ""


def _framework(headers: dict, html: str) -> tuple[str | None, str]:
    h = {k.lower(): str(v).lower() for k, v in headers.items()}
    low = html.lower()
    if "next.js" in h.get("x-powered-by", "") or "x-nextjs-cache" in h or "__next_data__" in low or "/_next/static" in low:
        return "nextjs", "Next.js markers (/_next/static or x-powered-by)"
    if 'content="astro' in low or "/_astro/" in low or "astro-island" in low:
        return "astro", "Astro markers (/_astro/ or generator)"
    if "__nuxt" in low or "/_nuxt/" in low:
        return "nuxt", "Nuxt markers (/_nuxt/)"
    if "__sveltekit" in low or "/_app/immutable/" in low:
        return "sveltekit", "SvelteKit markers (/_app/immutable/)"
    if "wp-content/" in low or 'content="wordpress' in low:
        return "wordpress", "WordPress markers (wp-content)"
    if "gptengineer" in low or "lovable" in low or "cdn.gpteng.co" in low:
        return "lovable", "Lovable markers (gptengineer or lovable in the HTML)"
    if "bolt.new" in low or "stackblitz" in low:
        return "bolt", "Bolt markers (bolt.new in the HTML)"
    if re.search(r'src="/assets/index-[\w-]+\.js"', low) or "/@vite/client" in low:
        return "vite", "Vite build (/assets/index-*.js)"
    return None, ""


def _backend(html: str, rules: set[str]) -> tuple[str | None, str]:
    low = html.lower()
    if ".supabase.co" in low or any(r.startswith("sec.supabase") for r in rules):
        return "supabase", "a *.supabase.co address in the page or a Supabase finding"
    if "firebaseapp.com" in low or "firebaseio.com" in low or any(r.startswith("sec.firebase") for r in rules):
        return "firebase", "a Firebase address in the page or a Firebase finding"
    return None, ""


def detect(headers: dict, html: str, url: str, rules: set[str] | frozenset = frozenset()) -> dict:
    """{"hosting", "framework", "backend", "evidence": {part: why}}; unknown parts are None."""
    hosting, why_host = _host(headers, url)
    framework, why_framework = _framework(headers, html[:400_000])
    backend, why_backend = _backend(html[:400_000], set(rules))
    evidence = {k: v for k, v in (("hosting", why_host), ("framework", why_framework), ("backend", why_backend)) if v}
    return {"hosting": hosting, "framework": framework, "backend": backend, "evidence": evidence}


def label(stack: dict | None) -> str:
    """"Next.js on Vercel with Supabase", or "an unknown stack"."""
    if not stack:
        return "an unknown stack"
    parts = [LABEL[stack["framework"]] if stack.get("framework") else "", f"on {LABEL[stack['hosting']]}" if stack.get("hosting") else "",
             f"with {LABEL[stack['backend']]}" if stack.get("backend") else ""]
    text = " ".join(p for p in parts if p)
    return text or "an unknown stack"

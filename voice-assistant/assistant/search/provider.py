from __future__ import annotations
import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


class SearchProvider:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg.get('search', {})
        self.timeout = int(self.cfg.get('timeout', 10))
        self.max_results = int(self.cfg.get('max_results', 5))

    def search(self, query: str) -> List[SearchResult]:
        if not query:
            return []
        # 1) configured SearXNG (self-hosted, no subscription)
        searx = (self.cfg.get('searxng_url') or '').strip()
        if searx and self.cfg.get('allow_online', True):
            res = self._search_searxng(searx, query)
            if res:
                return res
        # 2) DuckDuckGo HTML (no key, best-effort, works when online)
        if self.cfg.get('allow_online', True):
            res = self._search_ddg(query)
            if res:
                return res
        return []

    def _http_get(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        h = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) FreeVoice/0.1'}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            raw = r.read()
            # try decode
            try:
                return raw.decode('utf-8', errors='replace')
            except Exception:
                return raw.decode('latin-1', errors='replace')

    def _search_searxng(self, base: str, query: str) -> List[SearchResult]:
        try:
            url = base.rstrip('/') + '/search?' + urllib.parse.urlencode({'q': query, 'format': 'json'})
            data = json.loads(self._http_get(url, {'Accept': 'application/json'}))
            out = []
            for item in data.get('results', [])[:self.max_results]:
                out.append(SearchResult(title=item.get('title',''), url=item.get('url',''),
                                        snippet=item.get('content','') or ''))
            return out
        except Exception:
            return []

    def _search_ddg(self, query: str) -> List[SearchResult]:
        try:
            url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query, 'kl': 'ru-ru'})
            page = self._http_get(url)
            return self._parse_ddg_html(page)
        except Exception:
            return []

    def _parse_ddg_html(self, page: str) -> List[SearchResult]:
        results: List[SearchResult] = []
        # try bs4 if available
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(page, 'lxml')
            for r in soup.select('.result')[:self.max_results]:
                a = r.select_one('.result__a')
                sn = r.select_one('.result__snippet')
                if not a:
                    continue
                href = a.get('href', '')
                # ddg redirect unwrap
                m = re.search(r'uddg=([^&]+)', href)
                if m:
                    href = urllib.parse.unquote(m.group(1))
                results.append(SearchResult(
                    title=a.get_text(' ', strip=True),
                    url=href,
                    snippet=sn.get_text(' ', strip=True) if sn else ''
                ))
            if results:
                return results
        except Exception:
            pass
        # regex fallback
        for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
            href = m.group(1)
            m2 = re.search(r'uddg=([^&]+)', href)
            if m2:
                href = urllib.parse.unquote(m2.group(1))
            title = re.sub('<[^>]+>', '', m.group(2))
            title = html.unescape(title).strip()
            results.append(SearchResult(title=title, url=href))
            if len(results) >= self.max_results:
                break
        return results

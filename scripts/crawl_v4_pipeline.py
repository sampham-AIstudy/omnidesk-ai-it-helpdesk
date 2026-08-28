# Hardened Product-Aligned RAG V4 Crawling Pipeline
import hashlib
import json
import logging
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.rag_service import scan_indirect_injection

logger = logging.getLogger('crawl_v4_pipeline')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

APPROVED_HOSTS = {
    'learn.microsoft.com',
    'support.microsoft.com',
    'docs.github.com',
    'git-scm.com',
    'docs.docker.com',
    'developer.mozilla.org',
    'support.apple.com',
    'help.ubuntu.com',
    'ubuntu.com',
    'docs.redhat.com',
    'www.postgresql.org',
    'docs.oracle.com',
    'pip.pypa.io',
    'docs.npmjs.com',
    'developer.chrome.com',
}

SECRET_PATTERNS = [
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', re.I),
    re.compile(r'\bghp_[a-zA-Z0-9]{36}\b'),
]

def canonicalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parsed.query) if not k.startswith('utm_') and k != 'view'))
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), query, ''))

def clean_text(value: str) -> str:
    value = value.replace('\u200b', ' ').replace('\xa0', ' ').replace('\x00', '')
    return re.sub(r'\s+', ' ', value).strip()

from html.parser import HTMLParser

class CleanHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.cur_text = []
        self.skip_tags = {'script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'form', 'aside'}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self.skip_depth += 1
            return
        if self.skip_depth > 0:
            return
        if tag.lower() in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'pre', 'code', 'tr', 'blockquote'}:
            self._flush()

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth > 0:
            return
        if tag.lower() in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'pre', 'code', 'tr', 'blockquote', 'div', 'section', 'article'}:
            self._flush()

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        self.cur_text.append(data)

    def _flush(self):
        txt = clean_text(' '.join(self.cur_text))
        self.cur_text = []
        if len(txt) >= 30 and not any(skip in txt.lower() for skip in ('cookie', 'privacy statement', 'all rights reserved', 'terms of use', 'feedback')):
            self.blocks.append(txt)

def extract_clean_blocks(html: str) -> list[str]:
    parser = CleanHTMLParser()
    try:
        parser.feed(html)
        parser._flush()
    except Exception:
        # Fallback regex with fixed backreference
        no_scripts = re.sub(r'<(script|style|nav|footer|header|noscript|svg|form|aside)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
        clean_tags = re.sub(r'<[^>]+>', ' ', no_scripts)
        raw_blocks = clean_tags.split('\n\n')
        return [clean_text(b) for b in raw_blocks if len(clean_text(b)) >= 30]
    
    blocks = []
    seen = set()
    for b in parser.blocks:
        h = hashlib.sha256(b.casefold().encode('utf-8')).hexdigest()
        if h not in seen:
            seen.add(h)
            blocks.append(b)
    return blocks

def chunk_blocks(blocks, max_chars=1800, overlap_blocks=1):
    chunks = []
    current = []
    current_len = 0
    for block in blocks:
        pieces = [block[i : i + max_chars] for i in range(0, len(block), max_chars)]
        for piece in pieces:
            added_len = len(piece) + (2 if current else 0)
            if current and current_len + added_len > max_chars:
                chunks.append('\n\n'.join(current))
                current = current[-overlap_blocks:] if overlap_blocks else []
                current_len = sum(len(item) for item in current) + 2 * max(0, len(current) - 1)
                if current and current_len + len(piece) + 2 > max_chars:
                    current = []
                    current_len = 0
            current.append(piece)
            current_len += len(piece) + (2 if len(current) > 1 else 0)
    if current:
        chunks.append('\n\n'.join(current))
    return [c for c in chunks if len(c.strip()) >= 80]

def check_robots(client, url):
    parsed = urlparse(url)
    robots_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
    try:
        resp = client.get(robots_url, timeout=10.0)
        if resp.status_code == 200:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(resp.text.splitlines())
            return parser.can_fetch('*', url) or parser.can_fetch(USER_AGENT, url)
        if resp.status_code in {401, 403}:
            return False
        return True
    except Exception:
        return True

def run_crawl_pipeline(manifest_path, staging_dir):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    staging = Path(staging_dir)
    raw_dir = staging / 'raw'
    accepted_dir = staging / 'accepted'
    rejected_dir = staging / 'rejected'
    norm_dir = staging / 'normalized'
    reports_dir = staging / 'reports'
    for d in (raw_dir, accepted_dir, rejected_dir, norm_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    results = []
    rejections = []
    stats = {
        'planned': len(manifest),
        'attempted': 0,
        'accepted_docs': 0,
        'accepted_chunks': 0,
        'rejected_sources': 0,
        'rejection_reasons': {},
    }

    retrieved_at = datetime.now(UTC).isoformat()
    seen_content_hashes = set()

    with httpx.Client(headers={'User-Agent': USER_AGENT}, follow_redirects=True, timeout=25.0) as client:
        for idx, item in enumerate(manifest, 1):
            stats['attempted'] += 1
            key = item['key']
            url = item['canonical_url']
            logger.info('[%d/%d] Fetching %s (%s)', idx, len(manifest), key, url)

            parsed = urlparse(url)
            if parsed.hostname not in APPROVED_HOSTS:
                err = f'Hostname {parsed.hostname} not in approved list'
                rejections.append({'key': key, 'url': url, 'reason': err})
                stats['rejected_sources'] += 1
                stats['rejection_reasons']['host_not_approved'] = stats['rejection_reasons'].get('host_not_approved', 0) + 1
                continue

            if not check_robots(client, url):
                err = 'Robots.txt Disallow'
                rejections.append({'key': key, 'url': url, 'reason': err})
                stats['rejected_sources'] += 1
                stats['rejection_reasons']['robots_denied'] = stats['rejection_reasons'].get('robots_denied', 0) + 1
                continue

            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    err = f'HTTP status {resp.status_code}'
                    rejections.append({'key': key, 'url': url, 'reason': err})
                    stats['rejected_sources'] += 1
                    stats['rejection_reasons']['http_failed'] = stats['rejection_reasons'].get('http_failed', 0) + 1
                    continue

                final_host = urlparse(str(resp.url)).hostname or ''
                if final_host.lower() not in APPROVED_HOSTS:
                    err = f'Redirected to unapproved host: {final_host}'
                    rejections.append({'key': key, 'url': url, 'reason': err})
                    stats['rejected_sources'] += 1
                    stats['rejection_reasons']['redirect_unapproved'] = stats['rejection_reasons'].get('redirect_unapproved', 0) + 1
                    continue

                html = resp.text
                (raw_dir / f'{key}.html').write_text(html, encoding='utf-8')

                blocks = extract_clean_blocks(html)
                if not blocks:
                    err = 'No technical content extracted'
                    rejections.append({'key': key, 'url': url, 'reason': err})
                    stats['rejected_sources'] += 1
                    stats['rejection_reasons']['no_content'] = stats['rejection_reasons'].get('no_content', 0) + 1
                    continue

                # Max 6-8 chunks per source
                chunks = chunk_blocks(blocks, max_chars=1800, overlap_blocks=1)[:6]
                if not chunks:
                    err = 'Zero valid chunks after chunking'
                    rejections.append({'key': key, 'url': url, 'reason': err})
                    stats['rejected_sources'] += 1
                    stats['rejection_reasons']['zero_chunks'] = stats['rejection_reasons'].get('zero_chunks', 0) + 1
                    continue

                title_match = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.IGNORECASE | re.DOTALL)
                page_title = clean_text(title_match.group(1)) if title_match else item.get('title', key)

                doc_chunks = []
                for c_idx, chunk in enumerate(chunks, 1):
                    if scan_indirect_injection(chunk):
                        logger.warning('Prompt injection marker in %s chunk %d', key, c_idx)
                        continue
                    if any(p.search(chunk) for p in SECRET_PATTERNS):
                        logger.warning('Secret pattern in %s chunk %d', key, c_idx)
                        continue

                    c_hash = hashlib.sha256(chunk.encode('utf-8')).hexdigest()
                    if c_hash in seen_content_hashes:
                        continue
                    seen_content_hashes.add(c_hash)

                    doc_record = {
                        'doc_id': f'web-{key}-{c_idx:03d}',
                        'title': item.get('title') or page_title,
                        'content': chunk,
                        'category': item['category'],
                        'issue_family': item['issue_family'],
                        'product_domain': item.get('product_domain', 'general'),
                        'topic': item.get('topic', 'general'),
                        'tags': item.get('tags', ''),
                        'priority': item.get('priority', 'P1'),
                        'source': 'official_web_documentation',
                        'source_type': item.get('source_type', 'official_vendor_documentation'),
                        'source_id': key,
                        'canonical_source_id': key,
                        'source_title': page_title,
                        'source_url': str(resp.url),
                        'vendor': item.get('vendor', 'Unknown'),
                        'product': item.get('product', 'Unknown'),
                        'retrieved_at': retrieved_at,
                        'content_sha256': c_hash,
                        'applicable_to_all': True,
                        'company_unit': 'all',
                        'department': '',
                    }
                    doc_chunks.append(doc_record)

                if doc_chunks:
                    stats['accepted_docs'] += 1
                    stats['accepted_chunks'] += len(doc_chunks)
                    results.extend(doc_chunks)
                    (accepted_dir / f'{key}.json').write_text(json.dumps(doc_chunks, indent=2, ensure_ascii=False), encoding='utf-8')
                else:
                    err = 'All chunks failed security or dedup filter'
                    rejections.append({'key': key, 'url': url, 'reason': err})
                    stats['rejected_sources'] += 1
                    stats['rejection_reasons']['filtered_out'] = stats['rejection_reasons'].get('filtered_out', 0) + 1

            except Exception as exc:
                err = f'Fetch/parse exception: {exc}'
                logger.error('%s failed: %s', key, exc)
                rejections.append({'key': key, 'url': url, 'reason': err})
                stats['rejected_sources'] += 1
                stats['rejection_reasons']['exception'] = stats['rejection_reasons'].get('exception', 0) + 1

            time.sleep(0.3)

    (norm_dir / 'crawled_v4_documents.json').write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    (reports_dir / 'crawl_v4_report.json').write_text(
        json.dumps({'stats': stats, 'rejections': rejections}, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    logger.info('=== CRAWL COMPLETE: %d docs accepted (%d chunks), %d rejected ===', stats['accepted_docs'], stats['accepted_chunks'], stats['rejected_sources'])
    return stats

if __name__ == '__main__':
    manifest_file = sys.argv[1] if len(sys.argv) > 1 else 'data/staging/crawl_v4/manifest_v4.json'
    staging_path = sys.argv[2] if len(sys.argv) > 2 else 'data/staging/crawl_v4'
    run_crawl_pipeline(manifest_file, staging_path)

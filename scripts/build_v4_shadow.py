import hashlib, json, logging, sys
from datetime import UTC, datetime
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings

ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))
from src.config import get_settings
from src.services.rag_service import embed_texts

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('build_v4_shadow')

VALID_CATEGORIES = {
    'hardware', 'software', 'network', 'access_permission',
    'infrastructure', 'security', 'email', 'service_request',
    'inquiry', 'other'
}

VALID_SOURCES = {
    'internal_curated_kb',
    'approved_internal_source',
    'official_web_documentation',
    'historical_resolved_ticket',
}

def normalize_meta(doc_id, content, meta):
    norm = dict(meta or {})
    if not norm.get('source'):
        if doc_id.startswith('kb-') or doc_id.startswith('sr-') or doc_id.startswith('auto-kb-'):
            norm['source'] = 'internal_curated_kb'
        elif doc_id.startswith('web-') or doc_id.startswith('p0-'):
            norm['source'] = 'official_web_documentation'
        elif doc_id.startswith('mem-'):
            norm['source'] = 'historical_resolved_ticket'
        else:
            norm['source'] = 'official_web_documentation'

    cat = str(norm.get('category', '')).strip().lower()
    if cat not in VALID_CATEGORIES:
        if cat == 'performance':
            norm['category'] = 'software'
        elif 'account' in cat or 'permission' in cat or 'access' in cat:
            norm['category'] = 'access_permission'
        elif 'printer' in cat or 'monitor' in cat or 'device' in cat:
            norm['category'] = 'hardware'
        elif 'network' in cat or 'wifi' in cat or 'vpn' in cat:
            norm['category'] = 'network'
        else:
            norm['category'] = 'other'

    if 'applicable_to_all' not in norm:
        norm['applicable_to_all'] = True
    if not norm.get('company_unit'):
        norm['company_unit'] = 'all'
    if 'department' not in norm:
        norm['department'] = ''
    if not norm.get('content_sha256'):
        norm['content_sha256'] = hashlib.sha256(content.encode('utf-8')).hexdigest()
    if not norm.get('canonical_source_id'):
        norm['canonical_source_id'] = norm.get('source_id') or doc_id
    if not norm.get('title'):
        norm['title'] = doc_id
    return norm

settings = get_settings()
client = chromadb.PersistentClient(path=settings.chroma_persist_dir, settings=ChromaSettings(anonymized_telemetry=False))

source_col_name = 'helpdesk_kb_multilingual_v3_sentence_transformer'
target_col_name = 'helpdesk_kb_multilingual_v4_shadow'

existing_cols = {c.name for c in client.list_collections()}
if target_col_name in existing_cols:
    logger.info('Deleting existing %s', target_col_name)
    client.delete_collection(target_col_name)

source_col = client.get_collection(source_col_name)
v3_count = source_col.count()
logger.info('Loading %d records from %s', v3_count, source_col_name)
v3_batch = source_col.get(limit=v3_count, include=['documents', 'metadatas', 'embeddings'])

records = []
seen_hashes = set()

for item_id, doc, meta, emb in zip(v3_batch['ids'], v3_batch['documents'], v3_batch['metadatas'], v3_batch['embeddings']):
    norm = normalize_meta(item_id, doc, meta)
    h = norm['content_sha256']
    seen_hashes.add(h)
    clean_emb = [float(x) for x in emb]
    records.append({'id': item_id, 'document': doc, 'metadata': norm, 'embedding': clean_emb})

logger.info('Processed %d V3 base records', len(records))

crawled_file = Path('data/staging/crawl_v4/normalized/crawled_v4_documents.json')
crawled_docs = json.loads(crawled_file.read_text(encoding='utf-8'))
logger.info('Loaded %d crawled V4 documents', len(crawled_docs))

new_to_embed = []
for d in crawled_docs:
    doc_id = d['doc_id']
    doc_text = f"{d['title']}. Từ khóa: {d['tags']}. {d['content']}"
    norm = normalize_meta(doc_id, doc_text, d)
    h = norm['content_sha256']
    if h in seen_hashes:
        continue
    seen_hashes.add(h)
    new_to_embed.append({'id': doc_id, 'document': doc_text, 'metadata': norm})

logger.info('Embedding %d new V4 chunks', len(new_to_embed))
if new_to_embed:
    texts = [item['document'] for item in new_to_embed]
    embeddings = embed_texts(texts)
    for item, emb in zip(new_to_embed, embeddings):
        clean_emb = [float(x) for x in emb]
        records.append({'id': item['id'], 'document': item['document'], 'metadata': item['metadata'], 'embedding': clean_emb})

invalid = []
cat_dist = {}
src_dist = {}
top_dist = {}
for r in records:
    doc_id = r['id']
    m = r['metadata']
    errs = []
    if not m.get('source') or m['source'] not in VALID_SOURCES:
        errs.append(f"Invalid source: {m.get('source')}")
    if not m.get('category') or m['category'] not in VALID_CATEGORIES:
        errs.append(f"Invalid category: {m.get('category')}")
    if not m.get('content_sha256'):
        errs.append('Missing content_sha256')
    if not r.get('document'):
        errs.append('Empty document')
    if errs:
        invalid.append({'doc_id': doc_id, 'errors': errs})
    c = m.get('category', 'unknown')
    s = m.get('source', 'unknown')
    t = m.get('topic', 'none')
    cat_dist[c] = cat_dist.get(c, 0) + 1
    src_dist[s] = src_dist.get(s, 0) + 1
    top_dist[t] = top_dist.get(t, 0) + 1

val_summary = {
    'total_records': len(records),
    'valid_records': len(records) - len(invalid),
    'invalid_records': len(invalid),
    'category_distribution': cat_dist,
    'source_distribution': src_dist,
    'unique_topics': len(top_dist),
    'generated_at': datetime.now(UTC).isoformat(),
}

val_path = Path('data/staging/crawl_v4/metadata_schema_validation.json')
val_path.write_text(json.dumps({'summary': val_summary, 'invalid_records': invalid}, indent=2, ensure_ascii=False), encoding='utf-8')
logger.info('Validation report written to %s (invalid: %d)', val_path, len(invalid))
assert len(invalid) == 0, 'Metadata validation failed!'

target_col = client.create_collection(
    name=target_col_name,
    metadata={
        'hnsw:space': 'cosine',
        'shadow_version': 'v4',
        'shadow_only': True,
        'source_collection': source_col_name,
        'total_chunks': len(records),
        'v3_base_chunks': len(v3_batch['ids']),
        'new_v4_chunks': len(new_to_embed),
        'created_at': datetime.now(UTC).isoformat(),
    }
)

batch_size = 64
for start in range(0, len(records), batch_size):
    batch = records[start : start + batch_size]
    target_col.add(
        ids=[r['id'] for r in batch],
        documents=[r['document'] for r in batch],
        metadatas=[r['metadata'] for r in batch],
        embeddings=[r['embedding'] for r in batch],
    )

logger.info('=== V4 SHADOW CREATED SUCCESSFULLY ===')
logger.info('Collection: %s, Count: %d', target_col_name, target_col.count())
logger.info('V3 Base: %d, New V4: %d, Total: %d', len(v3_batch['ids']), len(new_to_embed), target_col.count())

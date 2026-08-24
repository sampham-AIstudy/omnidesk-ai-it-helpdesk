# P0 Canonical V3 Rollback

Rollback is configuration-only; neither collection is rebuilt, modified, or deleted.

1. Set `CHROMA_COLLECTION_NAME=helpdesk_kb_multilingual_v2_sentence_transformer` in the runtime environment.
2. Restart or reload the application process so settings and the in-memory Chroma collection cache are recreated.
3. Verify the runtime collection name and count are `helpdesk_kb_multilingual_v2_sentence_transformer` and `433`.

To return to v3, set `CHROMA_COLLECTION_NAME=helpdesk_kb_multilingual_v3_sentence_transformer` and restart/reload.

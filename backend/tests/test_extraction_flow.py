from app.services.enhanced_world_extractor import EnhancedWorldExtractor


def test_medium_setting_text_uses_single_pass_threshold(monkeypatch):
    text = "设定项A：这是一个需要整体理解的世界观设定。\n" * 900
    assert len(text) > EnhancedWorldExtractor.LONG_TEXT_THRESHOLD

    profile = {
        "profile": "short",
        "chunk_size": 60000,
        "chunk_overlap": 500,
        "chapter_chunk_char_budget": 60000,
        "chapters_per_chunk": 9999,
        "outer_workers": 4,
        "text_length": len(text),
        "context_window": 128000,
        "target_chunk_chars": 60000,
        "parser_model": "test-parser",
        "chunk_profile_version": 999,
    }
    calls = []

    monkeypatch.setattr(
        EnhancedWorldExtractor,
        "get_text_volume_profile",
        classmethod(lambda cls, text_len: {**profile, "text_length": text_len}),
    )

    def fake_short_extract(self, source_text, progress_callback=None):
        calls.append(("short", len(source_text)))
        return {
            "world_info": {},
            "entities": [],
            "events": [],
            "settings": {},
            "extraction_diagnostics": {},
        }

    def fake_chapter_extract(self, *args, **kwargs):
        calls.append(("chapters", len(args[0]) if args else 0))
        return {}

    monkeypatch.setattr(EnhancedWorldExtractor, "_extract_short_text", fake_short_extract)
    monkeypatch.setattr(EnhancedWorldExtractor, "_extract_chapters", fake_chapter_extract)

    extractor = EnhancedWorldExtractor()
    cleaned_len = len(extractor._preclean_extraction_text(text))

    result = extractor.extract_from_text(text, extraction_mode="fast")

    assert calls == [("short", cleaned_len)]
    assert result["cache_status"] == "skipped_short_text"
    assert result["extraction_diagnostics"]["single_pass_threshold"] == 60000


def test_text_above_dynamic_single_pass_threshold_uses_chapter_flow(monkeypatch):
    text = "超长设定项：需要分块。\n" * 3000

    profile = {
        "profile": "novel",
        "chunk_size": 20000,
        "chunk_overlap": 500,
        "chapter_chunk_char_budget": 20000,
        "chapters_per_chunk": 9999,
        "outer_workers": 4,
        "text_length": len(text),
        "context_window": 64000,
        "target_chunk_chars": 20000,
        "parser_model": "test-parser",
        "chunk_profile_version": 999,
    }
    calls = []

    monkeypatch.setattr(
        EnhancedWorldExtractor,
        "get_text_volume_profile",
        classmethod(lambda cls, text_len: {**profile, "text_length": text_len}),
    )

    def fake_short_extract(self, source_text, progress_callback=None):
        calls.append(("short", len(source_text)))
        return {}

    def fake_chapter_extract(self, source_text, *args, **kwargs):
        calls.append(("chapters", len(source_text)))
        return {"cache_status": "running"}

    monkeypatch.setattr(EnhancedWorldExtractor, "_extract_short_text", fake_short_extract)
    monkeypatch.setattr(EnhancedWorldExtractor, "_extract_chapters", fake_chapter_extract)

    extractor = EnhancedWorldExtractor()
    cleaned_len = len(extractor._preclean_extraction_text(text))

    result = extractor.extract_from_text(text, extraction_mode="fast")

    assert calls == [("chapters", cleaned_len)]
    assert result["cache_status"] == "running"

import threading
import time

from app.services.enhanced_world_extractor import EnhancedWorldExtractor


def make_result(chunk_index: int, intro: str):
    return {
        "world_info": {},
        "entities": [{
            "name": f"角色{chunk_index}",
            "type": "人物",
            "attributes": {"简介": intro},
            "aliases": [],
            "stages": [],
            "relationships": [],
        }],
        "events": [],
        "settings": {"items": [], "mapData": {}, "calendars": []},
    }


def main():
    text = "\n\n".join([f"第{i}章 标题\n" + ("内容" * 5000) for i in range(1, 4)])
    extractor = EnhancedWorldExtractor()
    volume_profile = extractor.get_text_volume_profile(len(text))
    cache_key = extractor.build_cache_key(text, "deep", volume_profile)
    pause_flag = threading.Event()
    result_box = {}

    original = extractor._extract_from_chunk

    def slow_chunk(chunk, chunk_index=0, context_prefix=""):
        time.sleep(3)
        return make_result(chunk_index, "slow")

    extractor._extract_from_chunk = slow_chunk

    worker = threading.Thread(
        target=lambda: result_box.setdefault(
            "paused_result",
            extractor.extract_from_text(
                text,
                extraction_mode="deep",
                should_pause=lambda: pause_flag.is_set(),
            ),
        )
    )

    started = time.time()
    worker.start()
    time.sleep(0.6)
    pause_flag.set()
    worker.join(timeout=2.0)
    assert not worker.is_alive(), "pause did not return immediately"

    paused_result = result_box["paused_result"]
    cache = extractor._load_cache(cache_key)
    assert paused_result.get("paused") is True
    assert cache.get("status") == "paused"
    pending_indexes = [record.get("index") for record in (cache.get("chunks") or []) if record.get("status") == "pending"]
    assert pending_indexes, "interrupted chunk was not re-queued"
    interrupted_index = pending_indexes[0]

    def fast_chunk(chunk, chunk_index=0, context_prefix=""):
        return make_result(chunk_index, "fast")

    extractor._extract_from_chunk = fast_chunk
    resumed_result = extractor.resume_from_cache(cache_key)
    resumed_entity_names = [item.get("name") for item in resumed_result.get("entities") or []]

    assert resumed_result.get("paused") is not True
    assert resumed_result.get("cache_status") in {"completed", "partial"}
    assert f"角色{interrupted_index}" in resumed_entity_names

    extractor._extract_from_chunk = original
    print("immediate-pause-ok", round(time.time() - started, 2), interrupted_index)
    print("resume-from-interrupted-chunk-ok", resumed_result.get("cache_status"), len(resumed_entity_names))


if __name__ == "__main__":
    main()

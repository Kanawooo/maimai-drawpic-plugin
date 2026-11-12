"""Persistent character references and admission checks; no real LLM, provider or chat sends."""

import asyncio
import base64
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from PIL import Image
import pytest

from test_workspace import DrawpicConfig, image_bytes, make_plugin
from test_lifecycle_settlement import configured_plugin, remaining, module

PersonaReferenceStore = module("infrastructure.storage.persona").PersonaReferenceStore
PersonaReferenceService = module("application.persona").PersonaReferenceService
TaskRequestError = module("domain.task_errors").TaskRequestError


def plan_response(subject="SELF", shot="侧身坐在桌边，手扶杯子，视线自然移向窗外，侧前方拍摄"):
    return {"success": True, "response": json.dumps({"subject": subject, "shot": shot if subject == "SELF" else ""}, ensure_ascii=False)}


def picture(color):
    output = BytesIO()
    Image.new("RGB", (80, 100), color).save(output, "PNG")
    return output.getvalue()


def service(tmp_path, verdict="SELF", enabled=True, name="林悦 Yue"):
    config = DrawpicConfig()
    config.general.persona_reference_enabled = enabled
    config.general.persona_reference_name = name
    ctx = SimpleNamespace(
        llm=SimpleNamespace(generate=AsyncMock(return_value=plan_response(verdict if isinstance(verdict, str) else "SELF"))),
        api=SimpleNamespace(call=AsyncMock(return_value={})),
        config=SimpleNamespace(get=AsyncMock(return_value="Yue")), logger=Mock(),
    )
    store = PersonaReferenceStore(tmp_path)
    return PersonaReferenceService(ctx, store, lambda: config)


def test_store_persists_valid_images_and_rejects_stale_or_duplicate_writes(tmp_path):
    store = PersonaReferenceStore(tmp_path)
    raw = image_bytes()
    saved = store.add(raw, 0)
    restarted = PersonaReferenceStore(tmp_path)
    assert restarted.images() == [raw]
    with pytest.raises(ValueError, match="变化"):
        restarted.add(picture("blue"), 0)
    with pytest.raises(ValueError, match="已经存在"):
        restarted.add(raw, 1)
    with pytest.raises(ValueError):
        restarted.add(b"not an image", 1)
    assert restarted.snapshot() == saved
    assert restarted.remove(saved["images"][0]["id"], 1)["images"] == []
    assert not list(store.root.glob("*.image"))


def test_store_limits_and_corrupt_bytes_are_not_silently_ignored(tmp_path):
    store = PersonaReferenceStore(tmp_path)
    for revision, color in enumerate(["red", "green", "blue"]):
        store.add(picture(color), revision)
    with pytest.raises(ValueError, match="最多"):
        store.add(picture("black"), 3)
    with pytest.raises(ValueError, match="6 MiB"):
        store.add(b"x" * (store.MAX_IMAGE_BYTES + 1), 3)
    snapshot = store.snapshot()
    path = store.root / (snapshot["images"][0]["id"] + ".image")
    path.write_bytes(picture("white"))
    with pytest.raises(ValueError, match="校验失败"):
        store.images()
    assert store.snapshot() == snapshot


def test_corrupt_index_is_preserved(tmp_path):
    store = PersonaReferenceStore(tmp_path)
    store.add(image_bytes(), 0)
    invalid = {"revision": 1, "images": [{"id": "../outside"}]}
    store.path.write_text(json.dumps(invalid), encoding="utf-8")
    before = store.path.read_bytes()
    with pytest.raises(ValueError, match="无效图片 ID"):
        store.add(picture("blue"), 1)
    assert store.path.read_bytes() == before


def test_self_binds_real_images_deduplicates_and_preserves_other_source_urls(tmp_path):
    async def run():
        persona = service(tmp_path)
        reference, original = image_bytes(), picture("blue")
        persona.store.add(reference, 0)
        prompt, images, urls = await persona.prepare(
            "Yue 和朋友合照", [reference, original], ["https://example.com/ref", "https://example.com/original"],
        )
        assert images == [reference, original]
        assert urls == ["https://example.com/ref", "https://example.com/original"]
        assert "前 1 张" in prompt and "不让其他人" in prompt
        assert (await persona.snapshot())["images"][0]["preview"].startswith("data:image/webp;base64,")
    asyncio.run(run())


@pytest.mark.parametrize("verdict", ["NONE", "OTHER"])
def test_no_character_and_other_people_are_unchanged_even_without_references(tmp_path, verdict):
    async def run():
        persona = service(tmp_path, verdict)
        raw = picture("blue")
        original = ("a landscape", [raw], ["https://example.com/original"])
        assert await persona.prepare(*original) == original
    asyncio.run(run())


def test_detection_uses_subject_instead_of_style_and_resolves_bot_name(tmp_path):
    async def run():
        persona = service(tmp_path, "NONE", name="")
        await persona.prepare("style says selfie and same identity; lake", [], [], subject_prompt="a lake")
        message = persona.ctx.llm.generate.call_args.args[0][1]["content"]
        assert json.loads(message) == {"character": "Yue", "drawing_request": "a lake", "life_context": {}, "recent_shots": []}
        persona.ctx.config.get.assert_awaited_once_with("bot.nickname", "")
    asyncio.run(run())


def test_disabled_feature_has_no_llm_or_reference_io(tmp_path):
    async def run():
        persona = service(tmp_path, enabled=False)
        persona.store.images = Mock(side_effect=AssertionError("no reference reads"))
        assert await persona.prepare("selfie", [], []) == ("selfie", [], [])
        persona.ctx.llm.generate.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize("failure,code", [
    ("UNCERTAIN", "PERSONA_UNCERTAIN"), ("garbage", "PERSONA_UNCERTAIN"),
    ("SELF", "PERSONA_REFERENCE_MISSING"), (RuntimeError("unavailable"), "PERSONA_CHECK_FAILED"),
])
def test_detection_failures_and_missing_refs_stop_submission(tmp_path, failure, code):
    async def run():
        persona = service(tmp_path, failure)
        if isinstance(failure, Exception):
            persona.ctx.llm.generate.side_effect = failure
        with pytest.raises(TaskRequestError) as error:
            await persona.prepare("selfie", [], [])
        assert error.value.code == code
    asyncio.run(run())


def test_combined_limit_is_enforced(tmp_path):
    async def run():
        persona = service(tmp_path)
        persona.store.add(image_bytes(), 0)
        with pytest.raises(ValueError, match="合计超过"):
            await persona.prepare("selfie", [picture("blue")] * 8, [""] * 8)
    asyncio.run(run())


def test_api_auto_edit_and_idempotency_skip_reclassification(make_plugin, monkeypatch):
    async def run():
        plugin = make_plugin()
        await plugin.on_load()
        try:
            config = plugin.config.general
            config.persona_reference_enabled = True
            config.persona_reference_name = "Yue"
            persona = plugin._persona_reference_service
            persona.store.add(image_bytes(), 0)
            detect = AsyncMock(return_value=plan_response())
            monkeypatch.setattr(plugin.ctx.llm, "generate", detect)
            draw = plugin._require_draw_service()
            generated = []

            async def generate(**kwargs):
                generated.append(kwargs)
                return [image_bytes()]

            monkeypatch.setattr(draw, "_run_image_request_attempt", generate)
            first = await plugin.drawpic_submit("Yue selfie", request_id="persona-test-1")
            await asyncio.gather(*draw.background_tasks)
            second = await plugin.drawpic_submit("Yue selfie", request_id="persona-test-1")
            assert second["reused"] and second["task_id"] == first["task_id"]
            detect.assert_awaited_once()
            assert len(generated) == 1 and generated[0]["source_image_bytes_list"] == [image_bytes()]
            task = plugin._task_store.get_task(first["task_id"])
            assert task.task_type == "edit_image"
            assert task.submission["prompt"] == "Yue selfie"
        finally:
            await plugin.on_unload()
    asyncio.run(run())


@pytest.mark.parametrize("condition", ["missing", "unsupported", "forced_text"])
def test_chat_rejections_precede_task_creation_and_quota(make_plugin, monkeypatch, condition):
    async def run():
        plugin = await configured_plugin(make_plugin, monkeypatch)
        try:
            plugin.config.general.persona_reference_enabled = True
            plugin.config.general.persona_reference_name = "Yue"
            monkeypatch.setattr(plugin.ctx.llm, "generate", AsyncMock(return_value=plan_response()))
            if condition != "missing":
                plugin._persona_reference_service.store.add(image_bytes(), 0)
            if condition == "unsupported":
                plugin.config.general.image_edit_unsupported_models = plugin._require_router().get_all_models()
            with pytest.raises(ValueError):
                await plugin._start_background_image_request(
                    prompt="Yue selfie", stream_id="mock-stream", forced_text_only=condition == "forced_text",
                )
            assert remaining(plugin) == 1
            assert not plugin._task_store.snapshot()
        finally:
            await plugin.on_unload()
    asyncio.run(run())


def test_reference_management_api_uses_owned_sources_and_survives_reload(make_plugin):
    async def run():
        plugin = make_plugin()
        await plugin.on_load()
        try:
            inputs = plugin.ctx.paths.data_dir / "inputs"
            inputs.mkdir(exist_ok=True)
            source_id = "a" * 32
            (inputs / (source_id + ".image")).write_bytes(image_bytes())
            saved = await plugin.workspace_persona_add(source_id, 0)
            assert len(saved["images"]) == 1
            conflict = await plugin.workspace_persona_add(source_id, 0)
            assert "__workspace_error__" in conflict
            invalid = await plugin.workspace_persona_add("../outside", 1)
            assert "__workspace_error__" in invalid
        finally:
            await plugin.on_unload()
        reloaded = make_plugin(configured=False)
        await reloaded.on_load()
        try:
            data = await reloaded.workspace_bootstrap()
            assert data["persona_references"]["images"][0]["id"] == saved["images"][0]["id"]
            removed = await reloaded.workspace_persona_remove(saved["images"][0]["id"], 1)
            assert removed["images"] == []
        finally:
            await reloaded.on_unload()
    asyncio.run(run())


def test_live_scene_and_specific_shot_follow_raw_request_not_style(tmp_path):
    async def run():
        persona = service(tmp_path)
        persona.store.add(image_bytes(), 0)
        scene = {"activity": "改预算", "location": "办公室", "weather": "多云，19℃", "mood": "有些闷"}
        persona.ctx.api.call.return_value = scene
        persona.ctx.llm.generate.return_value = plan_response(shot="坐在海边看向海面，轻抬下巴，侧面近景")
        prompt, images, _ = await persona.prepare("style says keep pose; Yue 在海边侧脸", [], [], subject_prompt="Yue 在海边侧脸")
        persona.ctx.api.call.assert_awaited_once_with("maibot-community.mai-life.get_photo_context", version="1")
        data = json.loads(persona.ctx.llm.generate.call_args.args[0][1]["content"])
        assert data["drawing_request"] == "Yue 在海边侧脸" and data["life_context"] == scene
        assert "用户已指定" in persona.ctx.llm.generate.call_args.args[0][0]["content"]
        assert "海面" in prompt and "不是待编辑的底图" in prompt and len(images) == 1
        assert all(value in prompt for value in scene.values())
    asyncio.run(run())


def test_life_direct_request_has_no_callback_and_uses_one_authoritative_reference_set(tmp_path):
    async def run():
        persona = service(tmp_path)
        own, upstream = image_bytes(), picture("blue")
        persona.store.add(own, 0)
        persona.ctx.api.call.side_effect = AssertionError("must not call back into MaiLife")
        scene = {"activity": "喝水", "location": "家里", "weather": "晴", "mood": "平静", "source_role": "identity"}
        prompt, images, _ = await persona.prepare("Yue 此刻的生活照片", [upstream], [""], photo_context=scene)
        assert images == [own] and "喝水" in prompt
        assert "编辑源图，保留" not in prompt
        persona.ctx.api.call.assert_not_awaited()
        persona.ctx.llm.generate.assert_awaited_once()
    asyncio.run(run())


def test_life_snapshot_cannot_relabel_an_actual_user_edit_source(tmp_path):
    async def run():
        persona = service(tmp_path)
        own, edit = image_bytes(), picture("blue")
        persona.store.add(own, 0)
        persona.ctx.api.call.return_value = {"activity": "休息", "source_role": "identity"}
        prompt, images, urls = await persona.prepare("换掉 Yue 照片的背景", [edit], ["https://example.com/edit"])
        assert images == [own, edit] and urls[-1] == "https://example.com/edit"
        assert "其余输入图才是本次编辑源图" in prompt
    asyncio.run(run())


def test_disabled_auto_reference_still_preserves_explicit_caller_scene(tmp_path):
    async def run():
        persona = service(tmp_path, enabled=False)
        source = picture("blue")
        prompt, images, _ = await persona.prepare("Yue", [source], [""], photo_context={"weather": "雨", "source_role": "identity"})
        assert "雨" in prompt and "不是待编辑的底图" in prompt and images == [source]
        persona.ctx.api.call.assert_not_awaited()
        persona.ctx.llm.generate.assert_not_awaited()
    asyncio.run(run())


def test_missing_life_plugin_does_not_fabricate_background_or_block_images(tmp_path):
    async def run():
        persona = service(tmp_path)
        persona.store.add(image_bytes(), 0)
        persona.ctx.api.call.side_effect = RuntimeError("API unavailable")
        prompt, _, _ = await persona.prepare("Yue 在海边", [], [])
        assert "当前生活背景" not in prompt
        assert json.loads(persona.ctx.llm.generate.call_args.args[0][1]["content"])["life_context"] == {}
        persona.ctx.logger.warning.assert_called_once()
    asyncio.run(run())


def test_recent_plans_are_bounded_and_isolated_by_conversation(tmp_path):
    async def run():
        persona = service(tmp_path)
        persona.store.add(image_bytes(), 0)
        for index in range(3):
            persona.ctx.llm.generate.return_value = plan_response(shot=f"方案 {index}，侧前方拍摄")
            await persona.prepare("Yue 自拍", [], [], scope_key="chat-a", photo_context={})
        assert len(persona.recent_shots["chat-a"]) == 2
        await persona.prepare("Yue 自拍", [], [], scope_key="chat-b", photo_context={})
        assert json.loads(persona.ctx.llm.generate.call_args.args[0][1]["content"])["recent_shots"] == []
    asyncio.run(run())


@pytest.mark.parametrize("context", [{"diary": "private"}, {"weather": 10}, {"source_role": []}, {"activity": "x" * 601}])
def test_supplied_scene_schema_rejects_invalid_or_private_fields(tmp_path, context):
    async def run():
        persona = service(tmp_path)
        with pytest.raises(ValueError):
            await persona.prepare("Yue 自拍", [], [], photo_context=context)
        persona.ctx.llm.generate.assert_not_awaited()
    asyncio.run(run())


def test_scene_request_id_recovery_does_not_replan_or_submit_twice(make_plugin, monkeypatch):
    async def run():
        plugin = make_plugin()
        await plugin.on_load()
        try:
            plugin.config.general.persona_reference_enabled = True
            plugin.config.general.persona_reference_name = "Yue"
            plugin._persona_reference_service.store.add(image_bytes(), 0)
            detect = AsyncMock(return_value=plan_response())
            monkeypatch.setattr(plugin.ctx.llm, "generate", detect)
            monkeypatch.setattr(plugin.ctx.api, "call", AsyncMock(side_effect=AssertionError("no callback")))
            draw = plugin._require_draw_service()
            generate = AsyncMock(return_value=[image_bytes()])
            monkeypatch.setattr(draw, "_run_image_request_attempt", generate)
            scene = {"activity": "喝茶", "location": "公司", "weather": "晴", "mood": "平静", "source_role": "identity"}
            source = base64.b64encode(picture("blue")).decode()
            args = dict(prompt="Yue 的生活照", task_type="edit_image", source_images=[source], request_id="scene-request-1", persona_scene_context=scene)
            first = await plugin.drawpic_submit_v2(**args)
            await asyncio.gather(*draw.background_tasks)
            again = await plugin.drawpic_submit_v2(**args)
            assert first["accepted"] and again["reused"] and again["task_id"] == first["task_id"]
            detect.assert_awaited_once()
            generate.assert_awaited_once()
            assert generate.call_args.kwargs["source_image_bytes_list"] == [image_bytes()]
            changed = await plugin.drawpic_submit_v2(**{**args, "persona_scene_context": {**scene, "activity": "下班"}})
            assert not changed["accepted"] and changed["error"]["code"] == "REQUEST_ID_CONFLICT"
        finally:
            await plugin.on_unload()
    asyncio.run(run())

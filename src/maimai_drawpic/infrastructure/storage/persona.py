"""持久人物参考图；与会过期的普通图生图输入分开保存。"""

from hashlib import sha256
from pathlib import Path
from threading import RLock
from uuid import uuid4
import json

from .atomic import write_json_atomically
from ..media.images import validate_image_bytes


class PersonaReferenceStore:
    MAX_IMAGES = 3
    MAX_IMAGE_BYTES = 6 * 1024 * 1024

    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "persona_references"
        self.path = self.root / "index.json"
        self.lock = RLock()

    def _read(self) -> dict:
        if self.root.is_symlink() or self.path.is_symlink():
            raise ValueError("人物参考图目录或索引不能是符号链接")
        if not self.path.exists():
            return {"revision": 0, "images": []}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or type(data.get("revision")) is not int or data["revision"] < 0
                or not isinstance(data.get("images"), list) or len(data["images"]) > self.MAX_IMAGES):
            raise ValueError("人物参考图索引损坏，请检查原文件")
        for item in data["images"]:
            identifier = item.get("id", "") if isinstance(item, dict) else ""
            if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
                raise ValueError("人物参考图索引包含无效图片 ID")
            digest = item.get("sha256", "")
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)
                    or type(item.get("bytes")) is not int or not 0 < item["bytes"] <= self.MAX_IMAGE_BYTES):
                raise ValueError("人物参考图索引损坏，请检查原文件")
        if len({item["id"] for item in data["images"]}) != len(data["images"]):
            raise ValueError("人物参考图索引包含重复图片 ID")
        return data

    def _file(self, identifier: str) -> Path:
        path = self.root / f"{identifier}.image"
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("人物参考图路径无效")
        return path

    def snapshot(self) -> dict:
        with self.lock:
            return self._read()

    def add(self, raw: bytes, revision: int) -> dict:
        if len(raw) > self.MAX_IMAGE_BYTES:
            raise ValueError("人物参考图单张不能超过 6 MiB")
        try:
            validate_image_bytes(raw)
        except (OSError, ValueError) as exc:
            raise ValueError("人物参考图必须是可读取的真实图片") from exc
        with self.lock:
            data = self._read()
            if type(revision) is not int or revision != data["revision"]:
                raise ValueError("人物参考图已发生变化，请刷新后重试")
            if len(data["images"]) >= self.MAX_IMAGES:
                raise ValueError("最多保存 3 张人物参考图，请先移除旧图")
            digest = sha256(raw).hexdigest()
            if any(item["sha256"] == digest for item in data["images"]):
                raise ValueError("这张人物参考图已经存在")
            self.root.mkdir(parents=True, exist_ok=True)
            identifier = uuid4().hex
            path = self._file(identifier)
            path.write_bytes(raw)
            data["images"].append({"id": identifier, "sha256": digest, "bytes": len(raw)})
            data["revision"] += 1
            try:
                write_json_atomically(self.path, data)
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            return data

    def remove(self, identifier: str, revision: int) -> dict:
        with self.lock:
            data = self._read()
            if type(revision) is not int or revision != data["revision"]:
                raise ValueError("人物参考图已发生变化，请刷新后重试")
            if not any(item["id"] == identifier for item in data["images"]):
                raise ValueError("人物参考图不存在")
            data["images"] = [item for item in data["images"] if item["id"] != identifier]
            data["revision"] += 1
            write_json_atomically(self.path, data)
            self._file(identifier).unlink(missing_ok=True)
            return data

    def images(self) -> list[bytes]:
        return self.load()[1]

    def load(self) -> tuple[dict, list[bytes]]:
        with self.lock:
            data = self._read()
            result = []
            for item in data["images"]:
                try:
                    with self._file(item["id"]).open("rb") as handle:
                        raw = handle.read(self.MAX_IMAGE_BYTES + 1)
                except OSError as exc:
                    raise ValueError("人物参考图不可读取，请重新上传") from exc
                if len(raw) != item["bytes"] or sha256(raw).hexdigest() != item["sha256"]:
                    raise ValueError("人物参考图校验失败，请检查原文件")
                validate_image_bytes(raw)
                result.append(raw)
            return data, result

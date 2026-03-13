from __future__ import annotations

import json
import random
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from vendor.ai_goofish_monitor.account_strategy_service import resolve_account_runtime_plan
from vendor.ai_goofish_monitor.rotation import load_state_files

SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class StateFileSummary:
    name: str
    path: str
    is_root: bool


class LoginStateService:
    def __init__(self, state_dir: Path, root_state_file: Path):
        self.state_dir = state_dir
        self.root_state_file = root_state_file

    def list_state_files(self) -> List[StateFileSummary]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        files = [Path(path) for path in load_state_files(str(self.state_dir))]
        if self.root_state_file.exists() and self.root_state_file.parent == self.state_dir:
            root_in_dir = any(path == self.root_state_file for path in files)
            if not root_in_dir:
                files.append(self.root_state_file)
        elif self.root_state_file.exists():
            files.append(self.root_state_file)

        unique = sorted({path.resolve(): path for path in files}.values(), key=lambda item: item.name)
        return [
            StateFileSummary(name=path.name, path=str(path), is_root=path.resolve() == self.root_state_file.resolve())
            for path in unique
        ]

    def save_state(self, content: str, file_name: Optional[str] = None) -> StateFileSummary:
        self._validate_json(content)
        target = self._resolve_target(file_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return StateFileSummary(name=target.name, path=str(target), is_root=target.resolve() == self.root_state_file.resolve())

    def delete_state(self, file_name: str) -> bool:
        target = self._resolve_target(file_name)
        if not target.exists():
            return False
        target.unlink()
        return True

    def promote_to_root(self, file_name: str) -> StateFileSummary:
        source = self._resolve_target(file_name)
        if not source.exists():
            raise ValueError("state file does not exist")
        self.root_state_file.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != self.root_state_file.resolve():
            shutil.copyfile(source, self.root_state_file)
        return StateFileSummary(
            name=self.root_state_file.name,
            path=str(self.root_state_file),
            is_root=True,
        )

    def resolve_runtime_plan(self, strategy: Optional[str], account_state_file: Optional[str]) -> dict:
        summaries = self.list_state_files()
        pool_files = [item.path for item in summaries if not item.is_root]
        return resolve_account_runtime_plan(
            strategy=strategy,
            account_state_file=account_state_file,
            has_root_state_file=self.root_state_file.exists(),
            available_account_files=pool_files,
        )

    def resolve_state_file(self, strategy: Optional[str], account_state_file: Optional[str]) -> Path:
        plan = self.resolve_runtime_plan(strategy, account_state_file)
        forced_account = plan.get("forced_account")
        if forced_account:
            target = Path(forced_account)
            if not target.is_absolute():
                target = self.state_dir / forced_account
            if not target.exists():
                raise ValueError("requested state file does not exist")
            return target
        if plan.get("prefer_root_state") and self.root_state_file.exists():
            return self.root_state_file
        if plan.get("use_account_pool"):
            pool = [Path(item.path) for item in self.list_state_files() if not item.is_root]
            if pool:
                return random.choice(pool)
        raise ValueError("no available login state file")

    def _resolve_target(self, file_name: Optional[str]) -> Path:
        if file_name is None or not file_name.strip():
            return self.root_state_file
        safe_name = file_name.strip()
        if not SAFE_NAME_RE.match(safe_name):
            raise ValueError("invalid state file name")
        return self.state_dir / safe_name

    @staticmethod
    def _validate_json(content: str) -> None:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("state content must be valid JSON") from exc
        if not isinstance(payload, (dict, list)):
            raise ValueError("state content must be a JSON object or array")

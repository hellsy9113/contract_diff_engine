from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

V3DiffTokenType = Literal["equal", "insert", "delete"]
V3ClauseStatus = Literal["unchanged", "modified", "added", "deleted"]


class V3DiffToken(BaseModel):
    """Frontend-ready word diff token for one v3 clause."""

    model_config = ConfigDict(frozen=True)

    type: V3DiffTokenType
    text: str

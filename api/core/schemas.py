from typing import Any, Optional
from pydantic import BaseModel, model_validator


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel):
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None

    @model_validator(mode="after")
    def check_exclusive(self) -> "APIResponse":
        if self.data is not None and self.error is not None:
            raise ValueError("APIResponse cannot have both data and error set")
        return self

from pydantic import BaseModel, Field


class ApprovalPayload(BaseModel):
    reviewer: str | None = Field(default=None, max_length=255)
    comment: str | None = None
    draft_id: str | None = None


class ApprovalResult(BaseModel):
    task_id: str
    status: str
    decision: str
    reviewer: str | None

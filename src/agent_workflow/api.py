from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .agent import AgentError
from .service import AgentService

app = FastAPI(title="AI Agent Workflow Automation")


class AgentRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


def get_service() -> AgentService:
    return AgentService()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/run")
def agent_run(payload: AgentRequest, service: AgentService = Depends(get_service)):
    try:
        return service.run(payload.message)
    except AgentError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
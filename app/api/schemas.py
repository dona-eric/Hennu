from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=2000,
        description="Question sur la réglementation douanière",
    )


class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict] = []

class DocumentBase(BaseModel):
    id: str


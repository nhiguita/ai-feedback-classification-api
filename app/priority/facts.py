"""Facts the LLM extracts from feedback; priority is derived from them in code (see rules.py)."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import Category, Intent, Sentiment


class PriorityFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_down: bool = Field(description="The whole service, or an integration for all users, is unavailable now.")
    data_loss: bool = Field(description="Data was actually lost, deleted, overwritten or corrupted.")
    security_exposure: bool = Field(
        description="People can see or change data they should not (permission bypass, leaked credentials)."
    )
    blocked: bool = Field(
        description="The user or team cannot complete an essential task right now and no workaround is mentioned."
    )
    functional_problem: bool = Field(
        description="Something currently malfunctions, is slow or shows wrong data (not cosmetic issues or taste)."
    )
    price_or_support_complaint: bool = Field(description="Dissatisfaction with price, billing or support service.")
    business_need: bool = Field(
        description="A feature request that explains a concrete business need or cost, not a nice-to-have."
    )


class FeedbackAnalysis(BaseModel):
    """LLM output: labels except priority, plus the facts used to compute it."""

    model_config = ConfigDict(extra="forbid")

    sentiment: Sentiment
    intent: Intent
    category: Category
    facts: PriorityFacts

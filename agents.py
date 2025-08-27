from __future__ import annotations
from crewai import Agent

ANALYST_SYSTEM = (
    "You are a precise financial analyst. Use only the text provided in the task. "
    "Do NOT hallucinate; if something is uncertain, state that you cannot confirm. "
    "Your final output must be STRICT JSON only (no extra prose)."
)

financial_analyst = Agent(
    role="Financial Analyst",
    goal="Produce a structured JSON analysis (recommendation, risks, insights) from supplied financial text.",
    backstory=(
        "You analyze quarterly earnings, identify risk factors, and provide investment recommendations "
        "while adhering to compliance and avoiding unsupported claims."
    ),
    verbose=True,
    allow_delegation=False,
    max_iter=1,
    system_prompt=ANALYST_SYSTEM,
)
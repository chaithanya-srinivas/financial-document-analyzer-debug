from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ValidationError, conint
from openai import OpenAI

from tools import extract_text_from_pdf_bytes

# ---------- Pydantic schema ----------
class Recommendation(BaseModel):
    action: Literal["buy", "hold", "sell"]
    rationale: str
    confidence: conint(ge=0, le=100)

class RiskItem(BaseModel):
    name: str
    severity: Literal["low", "medium", "high", "critical"]
    impact: str
    likelihood: Literal["low", "medium", "high"]
    mitigation: str

class MarketInsight(BaseModel):
    topic: str
    insight: str
    evidence: str

class Metrics(BaseModel):
    revenue_yoy: Optional[float] = None
    gross_margin: Optional[float] = None
    ebitda_margin: Optional[float] = None
    guidance_change: Optional[str] = None

class DocumentMetadata(BaseModel):
    company: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    pages: Optional[int] = None

class AnalysisResult(BaseModel):
    metadata: DocumentMetadata
    recommendation: Recommendation
    risks: List[RiskItem]
    insights: List[MarketInsight]
    key_metrics: Optional[Metrics] = None
    quotes: List[str]
    limitations: str

# --------- helpers ---------
def _extract_json_str(s: str) -> str:
    """Extract first balanced-JSON object from a string."""
    s = (s or "").strip()
    if s.startswith("```"):
        s = s.strip("`").strip()
    start = s.find("{")
    if start == -1:
        return s
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1].strip().strip("`").strip()
    return s

def _build_schema_for_prompt() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "metadata": {
                "type": "object",
                "properties": {
                    "company": {"type": ["string", "null"]},
                    "quarter": {"type": ["string", "null"]},
                    "year": {"type": ["integer", "null"]},
                    "source": {"type": ["string", "null"]},
                    "pages": {"type": ["integer", "null"]},
                },
                "required": ["company", "quarter", "year", "source", "pages"],
            },
            "recommendation": {
                "type": "object",
                "properties": {
                    "action": {"enum": ["buy", "hold", "sell"]},
                    "rationale": {"type": "string"},
                    "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["action", "rationale", "confidence"],
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "severity": {"enum": ["low", "medium", "high", "critical"]},
                        "impact": {"type": "string"},
                        "likelihood": {"enum": ["low", "medium", "high"]},
                        "mitigation": {"type": "string"},
                    },
                    "required": ["name", "severity", "impact", "likelihood", "mitigation"],
                },
            },
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "insight": {"type": "string"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["topic", "insight", "evidence"],
                },
            },
            "key_metrics": {
                "type": ["object", "null"],
                "properties": {
                    "revenue_yoy": {"type": ["number", "null"]},
                    "gross_margin": {"type": ["number", "null"]},
                    "ebitda_margin": {"type": ["number", "null"]},
                    "guidance_change": {"type": ["string", "null"]},
                },
            },
            "quotes": {"type": "array", "items": {"type": "string"}},
            "limitations": {"type": "string"},
        },
        "required": ["metadata", "recommendation", "risks", "insights", "quotes", "limitations"],
        "additionalProperties": False,
    }

# Few-shot to keep the model (or mock) disciplined
_FEW_USER = (
    "TEXT (excerpt): Revenue grew 12% YoY to $10.1B; gross margin down 120bps; "
    "guidance: Q3 revenue flat to +2%.\n"
    'META: {"company":"SampleCo","quarter":"Q2","year":2025,"source":"mock.pdf","pages":2}'
)
_FEW_ASSISTANT = json.dumps({
    "metadata": {"company": "SampleCo", "quarter": "Q2", "year": 2025, "source": "mock.pdf", "pages": 2},
    "recommendation": {"action": "hold", "rationale": "Growth but margin compression; flat guide.", "confidence": 72},
    "risks": [{"name": "Margin pressure", "severity": "medium", "impact": "Profitability", "likelihood": "medium", "mitigation": "Pricing & mix"}],
    "insights": [
        {"topic": "Growth", "insight": "Double-digit YoY", "evidence": "12% YoY to $10.1B"},
        {"topic": "Guide", "insight": "Flat to +2%", "evidence": "Q3 guidance"},
    ],
    "key_metrics": {"revenue_yoy": 12.0, "gross_margin": None, "ebitda_margin": None, "guidance_change": "Flat to +2%"},
    "quotes": ['"Revenue grew 12% YoY to $10.1B"'],
    "limitations": "Excerpt only.",
}, ensure_ascii=False)

# --------- Mock + real model paths ---------
def _mock_result(text: str, meta: Dict[str, Any]) -> AnalysisResult:
    t = (text or "").lower()
    growth = any(k in t for k in ["increase", "grew", "up ", "growth", "higher"])
    margin = "margin" in t or "bps" in t
    rec = "buy" if growth and margin else ("hold" if growth else "sell")
    return AnalysisResult(
        metadata=DocumentMetadata(
            company=meta.get("company") or "UnknownCo",
            quarter=meta.get("quarter") or "Q?",
            year=meta.get("year"),
            source=meta.get("source") or "uploaded.pdf",
            pages=meta.get("pages"),
        ),
        recommendation=Recommendation(
            action=rec,
            rationale="Mock analysis using keywords (growth/margin).",
            confidence=65,
        ),
        risks=[
            RiskItem(
                name="Data completeness",
                severity="medium",
                impact="Heuristic mock may miss context.",
                likelihood="medium",
                mitigation="Use real model when quota is available.",
            )
        ],
        insights=[
            MarketInsight(
                topic="Growth",
                insight="Growth keywords detected." if growth else "No clear growth signals detected.",
                evidence="increase/grew/up/higher" if growth else "—",
            )
        ],
        key_metrics=Metrics(revenue_yoy=None, gross_margin=None, ebitda_margin=None, guidance_change=None),
        quotes=[],
        limitations="This is a mock result generated without calling the model.",
    )

def _llm_analyze_financials(text: str, meta: Dict[str, Any]) -> AnalysisResult:
    # Mock mode
    if os.getenv("MOCK_LLM", "0") == "1":
        return _mock_result(text, meta)

    client = OpenAI()
    schema = _build_schema_for_prompt()
    snippet = text if len(text) < 180_000 else text[:180_000]
    SYSTEM_PROMPT = (
        "You analyze official company financial PDFs. "
        "Rules: 1) NEVER hallucinate; if unsure, say you cannot confirm. "
        "2) Use ONLY the provided PDF text. 3) Output STRICT JSON ONLY—no extra text."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}"},
        {"role": "user", "content": _FEW_USER},
        {"role": "assistant", "content": _FEW_ASSISTANT},
        {"role": "user", "content": f"Analyze the document and output STRICT JSON only.\n"
                                     f"META: {json.dumps(meta, ensure_ascii=False)}\n"
                                     f"TEXT:\n{snippet}"},
    ]
    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.2,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or ""
        json_text = _extract_json_str(raw)
        return AnalysisResult.model_validate_json(json_text)
    except Exception as e:
        # Fallback to mock if allowed
        if os.getenv("MOCK_LLM", "0") == "1":
            return _mock_result(text, meta)
        raise RuntimeError(f"Model call failed: {e}")

def run_analysis(query: str, file_path: str) -> Dict[str, Any]:
    """Public entry used by FastAPI. CrewAI is optional, controlled by CREWAI_ENABLED."""
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    ext = extract_text_from_pdf_bytes(pdf_bytes)
    meta = {"company": None, "quarter": None, "year": None, "source": file_path, "pages": ext.get("pages")}

    # Optional CrewAI step (keeps assignment flavor) — disabled by default
    if os.getenv("CREWAI_ENABLED", "0") == "1":
        from crewai import Task as CrewTask, Crew, Process  # lazy import
        from agents import financial_analyst                 # lazy import

        analyze_task = CrewTask(
            description=(
                "Analyze the supplied financial text and produce STRICT JSON matching the schema. "
                "Avoid hallucinations; use only the provided text.\n"
                f"QUERY: {query}\nTEXT:\n{ext['text'][:180_000]}"
            ),
            expected_output=(
                "A single JSON object with keys: metadata, recommendation, risks, "
                "insights, key_metrics (optional), quotes, limitations."
            ),
            agent=financial_analyst,
        )
        crew = Crew(agents=[financial_analyst], tasks=[analyze_task], verbose=True, process=Process.sequential)
        _ = crew.kickoff({"query": query})  # we don't rely on this return

    result = _llm_analyze_financials(ext["text"], meta)
    return json.loads(result.model_dump_json())
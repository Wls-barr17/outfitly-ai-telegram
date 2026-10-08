from itertools import product
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class RecommendationWeights(BaseModel):
    weather: float = 0.30
    color: float = 0.20
    style: float = 0.15
    preference: float = 0.10
    novelty: float = 0.10
    availability: float = 0.05
    completeness: float = 0.10


class OutfitCandidate(BaseModel):
    items: list[dict[str, Any]]
    score: float = Field(ge=0, le=100)
    explanation: str


class ColorCompatibilityEngine:
    neutrals: ClassVar[set[str]] = {
        "WHITE",
        "BLACK",
        "GRAY",
        "GREY",
        "BEIGE",
        "NAVY",
        "BROWN",
    }

    def pair_score(self, left: str, right: str) -> float:
        a, b = left.upper(), right.upper()
        if a == b:
            return 0.78
        if a in self.neutrals and b in self.neutrals:
            return 0.96
        if a in self.neutrals or b in self.neutrals:
            return 0.93
        pairs = {
            frozenset(p)
            for p in (
                ("BLUE", "BEIGE"),
                ("NAVY", "WHITE"),
                ("BROWN", "BEIGE"),
                ("GREEN", "BROWN"),
                ("BLUE", "ORANGE"),
            )
        }
        return 0.9 if frozenset((a, b)) in pairs else 0.66

    def score(self, items: list[dict[str, Any]]) -> float:
        colors = [str(i.get("color", "")).upper() for i in items if i.get("color")]
        pairs = [
            self.pair_score(colors[a], colors[b])
            for a in range(len(colors))
            for b in range(a + 1, len(colors))
        ]
        return sum(pairs) / len(pairs) if pairs else 0.75


class WeatherRuleEngine:
    def score(
        self, items: list[dict[str, Any]], temperature: float, rain_probability: int
    ) -> float:
        score = 1.0
        types = " ".join(
            str(i.get("subcategory") or i.get("garment_type", "")).upper()
            for i in items
        )
        if temperature < 10:
            score += (
                0.1
                if any(x in types for x in ("JACKET", "COAT", "SWEATER", "HOODIE"))
                else -0.15
            )
            score -= 0.25 if any(x in types for x in ("SHORT", "SANDAL", "TANK")) else 0
        elif temperature < 15:
            score += (
                0.08 if any(x in types for x in ("JACKET", "SWEATER", "HOODIE")) else 0
            )
        elif temperature > 28:
            score += 0.1 if any(x in types for x in ("SHORT", "T_SHIRT", "TANK")) else 0
            score -= 0.15 if any(x in types for x in ("COAT", "SWEATER")) else 0
        if rain_probability > 60:
            score += 0.15 if any(x in types for x in ("RAIN", "WATERPROOF")) else 0
            score -= 0.15 if any(x in types for x in ("SANDAL", "SUEDE")) else 0
        return max(0.0, min(1.0, score))


class RecommendationEngine:
    def __init__(self, weights: RecommendationWeights | None = None) -> None:
        self.weights = weights or RecommendationWeights()
        self.colors = ColorCompatibilityEngine()
        self.weather = WeatherRuleEngine()

    def generate(
        self,
        items: list[dict[str, Any]],
        temperature: float,
        rain_probability: int = 0,
        preferred_style: str | None = None,
        history: list[list[str]] | None = None,
        preferences: dict[str, float] | None = None,
        limit: int = 3,
    ) -> list[OutfitCandidate]:
        available = [i for i in items if i.get("is_available", True)]
        groups = {
            key: [i for i in available if str(i.get("category", "")).upper() == key]
            for key in ("TOP", "BOTTOM", "FOOTWEAR", "OUTERWEAR", "ACCESSORY")
        }
        if not groups["TOP"] or not groups["BOTTOM"] or not groups["FOOTWEAR"]:
            return []
        prior = {tuple(sorted(ids)) for ids in (history or [])}
        results: list[OutfitCandidate] = []
        for base in product(groups["TOP"], groups["BOTTOM"], groups["FOOTWEAR"]):
            optional = groups["OUTERWEAR"] if temperature < 17 else [None]
            for layer in optional or [None]:
                selected = [*base, *([layer] if layer else [])]
                ids = [str(i.get("id", i.get("name", ""))) for i in selected]
                novelty = 0.15 if tuple(sorted(ids)) in prior else 1.0
                weather = self.weather.score(selected, temperature, rain_probability)
                color = self.colors.score(selected)
                styles = [str(i.get("style", "")).upper() for i in selected]
                desired_style = (preferred_style or "CASUAL").upper()
                style = sum(1 for s in styles if s and s == desired_style) / max(
                    1, sum(bool(s) for s in styles)
                )
                pref_values = preferences or {}
                preference = sum(
                    float(pref_values.get(str(i.get("subcategory", "")), 0))
                    for i in selected
                )
                preference = max(
                    0, min(1, 0.5 + preference / max(1, len(selected)) * 0.1)
                )
                components = (
                    weather * self.weights.weather
                    + color * self.weights.color
                    + style * self.weights.style
                    + preference * self.weights.preference
                    + novelty * self.weights.novelty
                    + self.weights.availability
                    + self.weights.completeness
                )
                score = round(
                    components / sum(self.weights.model_dump().values()) * 100, 1
                )
                reason = "El clima y la combinación de colores funcionan bien juntos."
                if temperature < 15:
                    reason = "Las capas ayudan a adaptarte al clima fresco."
                elif rain_probability > 60:
                    reason = (
                        "La selección prioriza comodidad ante la probabilidad "
                        "de lluvia."
                    )
                results.append(
                    OutfitCandidate(items=selected, score=score, explanation=reason)
                )
        results.sort(key=lambda candidate: candidate.score, reverse=True)
        return results[:limit]

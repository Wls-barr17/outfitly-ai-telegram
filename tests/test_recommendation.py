from app.recommendation.engine import (
    ColorCompatibilityEngine,
    RecommendationEngine,
    WeatherRuleEngine,
)


def test_neutral_colors_score_higher_than_conflicting_colors() -> None:
    engine = ColorCompatibilityEngine()
    neutral = engine.score([{"color": "WHITE"}, {"color": "BLACK"}])
    mixed = engine.score([{"color": "PURPLE"}, {"color": "ORANGE"}])
    assert neutral > mixed


def test_cold_weather_rewards_outerwear() -> None:
    engine = WeatherRuleEngine()
    jacket_score = engine.score(
        [{"subcategory": "JACKET"}, {"subcategory": "JEANS"}], 8, 0
    )
    light_score = engine.score(
        [{"subcategory": "T_SHIRT"}, {"subcategory": "JEANS"}], 8, 0
    )
    assert jacket_score > light_score


def test_hot_weather_penalizes_heavy_layers() -> None:
    engine = WeatherRuleEngine()
    shorts_score = engine.score(
        [{"subcategory": "T_SHIRT"}, {"subcategory": "SHORTS"}], 30, 0
    )
    coat_score = engine.score(
        [{"subcategory": "SWEATER"}, {"subcategory": "COAT"}], 30, 0
    )
    assert shorts_score > coat_score


def test_rain_prioritizes_rain_jacket_and_penalizes_sandals() -> None:
    engine = WeatherRuleEngine()
    protected = engine.score(
        [{"subcategory": "RAIN_JACKET"}, {"subcategory": "BOOTS"}], 18, 80
    )
    exposed = engine.score(
        [{"subcategory": "T_SHIRT"}, {"subcategory": "SANDALS"}], 18, 80
    )
    assert protected > exposed


def test_generator_uses_owned_available_items_and_history_penalty() -> None:
    items = [
        {
            "id": "t",
            "category": "TOP",
            "subcategory": "T_SHIRT",
            "color": "WHITE",
            "style": "CASUAL",
        },
        {
            "id": "b",
            "category": "BOTTOM",
            "subcategory": "JEANS",
            "color": "BLUE",
            "style": "CASUAL",
        },
        {
            "id": "s",
            "category": "FOOTWEAR",
            "subcategory": "SNEAKERS",
            "color": "WHITE",
            "style": "CASUAL",
        },
        {
            "id": "hidden",
            "category": "BOTTOM",
            "subcategory": "SHORTS",
            "is_available": False,
        },
    ]
    engine = RecommendationEngine()
    fresh = engine.generate(items, temperature=20, limit=1)[0]
    worn = engine.generate(items, temperature=20, history=[["t", "b", "s"]], limit=1)[0]
    assert [item["id"] for item in fresh.items] == ["t", "b", "s"]
    assert worn.score < fresh.score
    assert all(item["id"] != "hidden" for item in fresh.items)

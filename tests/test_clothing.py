import pytest
from pydantic import ValidationError

from app.domain.clothing import ClothingAnalysis, ClothingCategory


def test_valid_clothing_analysis() -> None:
    analysis = ClothingAnalysis(
        category="FOOTWEAR",
        garment_type="sneakers",
        color="white",
        style="casual",
        warmth=1,
    )

    assert analysis.category is ClothingCategory.FOOTWEAR
    assert analysis.warmth == 1


@pytest.mark.parametrize("warmth", [0, 6])
def test_warmth_must_be_in_supported_range(warmth: int) -> None:
    with pytest.raises(ValidationError):
        ClothingAnalysis(
            category="TOP",
            garment_type="shirt",
            color="blue",
            style="casual",
            warmth=warmth,
        )


def test_unknown_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ClothingAnalysis(
            category="UNKNOWN",
            garment_type="item",
            color="blue",
            style="casual",
            warmth=2,
        )

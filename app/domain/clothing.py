from enum import StrEnum

from pydantic import BaseModel, Field


class ClothingCategory(StrEnum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    OUTERWEAR = "OUTERWEAR"
    FOOTWEAR = "FOOTWEAR"
    ACCESSORY = "ACCESSORY"
    DRESS = "DRESS"


class GarmentSubcategory(StrEnum):
    T_SHIRT = "T_SHIRT"
    SHIRT = "SHIRT"
    POLO = "POLO"
    SWEATER = "SWEATER"
    HOODIE = "HOODIE"
    SWEATSHIRT = "SWEATSHIRT"
    TANK_TOP = "TANK_TOP"
    JEANS = "JEANS"
    PANTS = "PANTS"
    CHINOS = "CHINOS"
    SHORTS = "SHORTS"
    JOGGERS = "JOGGERS"
    SWEATPANTS = "SWEATPANTS"
    JACKET = "JACKET"
    COAT = "COAT"
    BOMBER = "BOMBER"
    WINDBREAKER = "WINDBREAKER"
    RAIN_JACKET = "RAIN_JACKET"
    SNEAKERS = "SNEAKERS"
    RUNNING_SHOES = "RUNNING_SHOES"
    CASUAL_SHOES = "CASUAL_SHOES"
    BOOTS = "BOOTS"
    SANDALS = "SANDALS"
    CAP = "CAP"
    HAT = "HAT"
    SUNGLASSES = "SUNGLASSES"
    WATCH = "WATCH"
    BELT = "BELT"
    SCARF = "SCARF"
    BAG = "BAG"
    OTHER = "OTHER"


class ClothingAnalysis(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    category: ClothingCategory
    subcategory: GarmentSubcategory | None = None
    garment_type: str = Field(min_length=1, max_length=80)
    color: str = Field(min_length=1, max_length=60)
    secondary_color: str | None = Field(default=None, max_length=60)
    pattern: str | None = Field(default=None, max_length=40)
    material: str | None = Field(default=None, max_length=60)
    style: str = Field(min_length=1, max_length=60)
    fit: str | None = Field(default=None, max_length=40)
    season: str | None = Field(default=None, max_length=40)
    formality: int = Field(default=2, ge=1, le=5)
    warmth: int = Field(ge=1, le=5)
    water_resistance: int = Field(default=0, ge=0, le=5)
    description: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0.7, ge=0, le=1)

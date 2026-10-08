# Image analysis

GeminiClient sends image bytes with an internal garment-classification prompt and requests JSON schema output. ClothingAnalysis validates categories, string lengths and numeric ranges. No brand is inferred and uncertain optional attributes may be null.

The bot displays the validated result and asks for confirmation before storage and database writes. Gemini does not choose outfits; the deterministic recommendation engine controls availability, weather, combinations and ranking. GEMINI_MODEL changes the selected model without code edits.

from pydantic import BaseModel


class WeatherResponse(BaseModel):
    temperature: float
    feels_like: float
    min_temperature: float
    max_temperature: float
    humidity: int
    rain_probability: int
    precipitation: float
    wind_speed: float
    uv_index: float
    weather_code: int


CITIES: dict[str, tuple[float, float, str]] = {
    "Bogotá": (4.7110, -74.0721, "America/Bogota"),
    "Medellín": (6.2442, -75.5812, "America/Bogota"),
    "Cali": (3.4516, -76.5320, "America/Bogota"),
    "Barranquilla": (10.9639, -74.7964, "America/Bogota"),
    "Cartagena": (10.3910, -75.4794, "America/Bogota"),
    "Bucaramanga": (7.1193, -73.1227, "America/Bogota"),
    "Pereira": (4.8143, -75.6946, "America/Bogota"),
    "Manizales": (5.0703, -75.5138, "America/Bogota"),
    "Armenia": (4.5339, -75.6811, "America/Bogota"),
    "Santa Marta": (11.2408, -74.1990, "America/Bogota"),
    "Cúcuta": (7.8891, -72.4967, "America/Bogota"),
    "Ibagué": (4.4389, -75.2322, "America/Bogota"),
    "Villavicencio": (4.1420, -73.6266, "America/Bogota"),
    "Neiva": (2.9273, -75.2819, "America/Bogota"),
    "Pasto": (1.2136, -77.2811, "America/Bogota"),
    "Popayán": (2.4448, -76.6147, "America/Bogota"),
    "Montería": (8.7479, -75.8814, "America/Bogota"),
    "Sincelejo": (9.3047, -75.3978, "America/Bogota"),
    "Valledupar": (10.4631, -73.2532, "America/Bogota"),
    "Tunja": (5.5353, -73.3678, "America/Bogota"),
}

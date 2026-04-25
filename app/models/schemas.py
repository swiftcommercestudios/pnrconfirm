from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class BookingStatus(str, Enum):
    WL = "WL"
    CNF = "CNF"
    RAC = "RAC"
    PQWL = "PQWL"
    GNWL = "GNWL"
    TQWL = "TQWL"
    CAN = "CAN"

class PassengerInfo(BaseModel):
    name: str
    age: int
    gender: str
    booking_status: str
    current_status: str

class TrainInfo(BaseModel):
    pnr: str
    train_number: str
    train_name: str
    from_station: str
    from_station_name: str
    to_station: str
    to_station_name: str
    departure_time: str
    arrival_time: str
    journey_date: str
    duration: str
    class_code: str
    quota: str
    booked_on: str
    chart_prepared: bool = False
    passengers: List[PassengerInfo]

class PredictionFactors(BaseModel):
    historical_confirmation_rate: float
    days_to_travel: int
    wl_movement_7d: int
    avg_daily_cancellations: float
    current_wl_number: int
    tatkal_seats_expected: int
    route_popularity_score: float
    season_factor: float

class WLMovementPoint(BaseModel):
    day: str
    wl_number: int

class PredictionResult(BaseModel):
    confirmation_probability: float
    prediction_label: str  # "High", "Medium", "Low"
    confidence_score: float
    factors: PredictionFactors
    wl_movement_history: List[WLMovementPoint]
    estimated_confirmation_by: Optional[str]
    recommendation: str

class PNRResponse(BaseModel):
    success: bool
    train_info: Optional[TrainInfo] = None
    prediction: Optional[PredictionResult] = None
    error: Optional[str] = None

class PNRRequest(BaseModel):
    pnr: str = Field(..., min_length=10, max_length=10, pattern=r'^\d{10}$')
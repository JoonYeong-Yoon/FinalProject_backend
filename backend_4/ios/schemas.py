from pydantic import BaseModel
from typing import Optional

class HealthData(BaseModel):
    steps: Optional[float] = 0
    distance: Optional[float] = 0
    flights: Optional[float] = 0

    activeEnergy: Optional[float] = 0
    exerciseTime: Optional[float] = 0

    heartRate: Optional[float] = 0
    restingHeartRate: Optional[float] = 0
    walkingHeartRate: Optional[float] = 0
    hrv: Optional[float] = 0

    sleepHours: Optional[float] = 0

    weight: Optional[float] = 0
    height: Optional[float] = 0
    bmi: Optional[float] = 0
    bodyFat: Optional[float] = 0
    leanBody: Optional[float] = 0

    systolic: Optional[float] = 0
    diastolic: Optional[float] = 0
    glucose: Optional[float] = 0
    oxygen: Optional[float] = 0

    calories: Optional[float] = 0
    water: Optional[float] = 0

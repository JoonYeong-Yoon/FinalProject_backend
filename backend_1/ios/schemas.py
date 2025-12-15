from pydantic import BaseModel

class HealthData(BaseModel):
    steps: float
    distance: float
    flights: float

    activeEnergy: float
    exerciseTime: float

    heartRate: float
    restingHeartRate: float
    walkingHeartRate: float
    hrv: float

    sleepHours: float

    weight: float
    height: float
    bmi: float
    bodyFat: float
    leanBody: float

    systolic: float
    diastolic: float
    glucose: float
    oxygen: float

    calories: float
    water: float

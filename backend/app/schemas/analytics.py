from datetime import date

from pydantic import BaseModel


class DailyQueueMetrics(BaseModel):
    date: date
    tokens_issued: int
    completed: int
    cancelled: int
    no_show: int
    average_wait_minutes: float | None
    average_service_minutes: float | None


class ServiceMetrics(BaseModel):
    service_id: int
    service_name: str
    tokens_issued: int
    completed: int
    average_wait_minutes: float | None
    average_service_minutes: float | None


class AppointmentMetrics(BaseModel):
    total: int
    completed: int
    cancelled: int
    no_show: int
    upcoming: int


class BusinessAnalytics(BaseModel):
    business_id: int
    start_date: date
    end_date: date
    days: list[DailyQueueMetrics]
    services: list[ServiceMetrics]
    appointments: AppointmentMetrics
    total_tokens: int
    completion_rate: float | None
    no_show_rate: float | None

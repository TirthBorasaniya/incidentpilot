"""Pydantic models for Alertmanager webhook payloads."""

from datetime import datetime

from pydantic import BaseModel


class AlertModel(BaseModel):
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: datetime
    endsAt: datetime
    generatorURL: str
    fingerprint: str


class AlertmanagerWebhookPayload(BaseModel):
    version: str
    groupKey: str
    truncatedAlerts: int
    status: str
    receiver: str
    groupLabels: dict[str, str]
    commonLabels: dict[str, str]
    commonAnnotations: dict[str, str]
    externalURL: str
    alerts: list[AlertModel]

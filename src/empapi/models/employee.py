"""Employee response models (what this API returns)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EmployeeDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")  # tolerate fields MCP adds later

    e_id: int
    name: str
    email: str
    phone: str | None = None
    job_title: str
    join_date: date
    salary: float | None = Field(
        None, description="null unless your role includes salary access"
    )
    department_id: int | None = None
    department_name: str | None = None
    manager_id: int | None = None
    manager_name: str | None = None


class EmployeeSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    e_id: int
    name: str
    job_title: str
    department_id: int | None = None
    department_name: str | None = None


class EmployeeSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[EmployeeSummary]
    total: int = Field(description="Total matches, ignoring limit and offset")
    limit: int
    offset: int

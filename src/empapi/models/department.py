"""Department response models."""



from datetime import date

from pydantic import BaseModel, Field

_SALARY_NOTE = "null unless your role includes salary access"


class DepartmentStatistics(BaseModel):
    dept_id: int
    name: str
    location: str | None = None
    is_active: bool
    created_date: date
    manager_id: int | None = None
    manager_name: str | None = None
    headcount: int
    budget: float | None = Field(None, description="null when no budget is set")
    total_salary: float | None = Field(None, description=_SALARY_NOTE)
    avg_salary: float | None = Field(None, description=_SALARY_NOTE)
    min_salary: float | None = Field(None, description=_SALARY_NOTE)
    max_salary: float | None = Field(None, description=_SALARY_NOTE)
    budget_utilization_pct: float | None = Field(
        None, description="total salary / budget * 100; " + _SALARY_NOTE
    )


class DepartmentStatisticsResult(BaseModel):
    departments: list[DepartmentStatistics]
    count: int

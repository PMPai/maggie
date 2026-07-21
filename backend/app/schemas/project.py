import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    code: str
    name: str
    company_type: str
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    contact_person: str | None = None


class CompanyResponse(BaseModel):
    id: str
    code: str
    name: str
    company_type: str
    tax_id: str | None
    status: str


class ProjectCreate(BaseModel):
    internal_project_code: str
    project_name: str
    description: str | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    currency: str = "TWD"
    default_tax_rate: Decimal = Decimal("0.05")


class ProjectResponse(BaseModel):
    id: str
    internal_project_code: str
    project_name: str
    description: str | None
    status: str
    currency: str
    default_tax_rate: Decimal


class ProjectMemberAdd(BaseModel):
    user_id: str
    project_role: str


class ProjectMemberResponse(BaseModel):
    id: str
    user_id: str
    project_role: str
    status: str

from pydantic import BaseModel, Field
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)
class RegisterRequest(LoginRequest):
    role: str = "Citizen/General User"
class VerifyFields(BaseModel):
    deed_number: str = ""
    registration_year: int | None = None
    seller_name: str = ""
    buyer_name: str = ""
    mouza: str = ""
    jl_number: str = ""
    khatian_number: str = ""
    dag_number: str = ""
    area_decimal: float | None = None
    deed_type: str = "Sale"

"""Shared data models for the Home Finder multi-agent system."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class HomeType(str, Enum):
    NEW_BUILD = "new_build"
    EXISTING = "existing"
    EITHER = "either"


class UserProfile(BaseModel):
    # Personal & Financial
    annual_income: float = Field(description="Combined annual household income in USD")
    savings: float = Field(description="Available savings for down payment and closing costs")
    credit_score: Optional[int] = Field(None, description="Credit score (300-850)")
    monthly_debts: float = Field(0, description="Monthly debt payments (car, student loans, etc.)")

    # Current Home
    has_current_home: bool = Field(False)
    current_home_value: Optional[float] = Field(None, description="Estimated value of current home")
    current_home_equity: Optional[float] = Field(None, description="Equity in current home")
    current_home_location: Optional[str] = Field(None, description="Current city/state")

    # Move Preferences
    target_move_date: str = Field(description="Target move date e.g. 'June 2025' or '2025-06-01'")
    destination_cities: List[str] = Field(
        description="List of cities/states to consider e.g. ['Austin, TX', 'Denver, CO']"
    )
    home_type_preference: HomeType = Field(HomeType.EITHER)

    # Lifestyle Priorities (1-5 scale)
    school_priority: int = Field(3, ge=1, le=5, description="Importance of school quality")
    commute_priority: int = Field(3, ge=1, le=5, description="Importance of commute/transport")
    safety_priority: int = Field(3, ge=1, le=5, description="Importance of low crime rate")
    walkability_priority: int = Field(3, ge=1, le=5, description="Importance of walkability")
    restaurants_priority: int = Field(3, ge=1, le=5, description="Importance of food/dining scene")
    job_market_priority: int = Field(3, ge=1, le=5, description="Importance of job opportunities")
    airport_priority: int = Field(3, ge=1, le=5, description="Importance of airport proximity")
    growth_priority: int = Field(3, ge=1, le=5, description="Importance of city growth/appreciation")

    # Family
    num_adults: int = Field(1, ge=1)
    num_children: int = Field(0, ge=0)
    industry: Optional[str] = Field(None, description="Industry you work in for job market analysis")

    # Home Requirements
    min_bedrooms: int = Field(2, ge=1)
    max_budget: Optional[float] = Field(None, description="Max home purchase price (calculated if not set)")


class AgentUpdate(BaseModel):
    agent: str
    status: str  # "starting" | "working" | "complete" | "error"
    message: str
    data: Optional[dict] = None


class CityAnalysis(BaseModel):
    city: str
    state: str
    overall_score: float
    school_score: float
    crime_score: float
    walkability_score: float
    transport_score: float
    job_market_score: float
    restaurant_score: float
    airport_score: float
    growth_score: float
    median_home_price: float
    affordability_score: float
    summary: str
    pros: List[str]
    cons: List[str]
    neighborhoods: List[str]


class HomeListing(BaseModel):
    address: str
    city: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: int
    home_type: str
    year_built: Optional[int] = None
    description: str
    zillow_url: Optional[str] = None
    match_score: float


class FinancialAnalysis(BaseModel):
    max_affordable_price: float
    recommended_price_range_min: float
    recommended_price_range_max: float
    estimated_down_payment: float
    estimated_monthly_payment: float
    estimated_closing_costs: float
    dti_ratio: float
    affordability_rating: str  # "comfortable" | "stretched" | "aggressive"
    notes: List[str]


class SaleTimeline(BaseModel):
    recommended_list_date: str
    estimated_sale_date: str
    estimated_net_proceeds: float
    pricing_strategy: str
    preparation_tasks: List[str]
    timeline_steps: List[dict]
    key_risks: List[str]


class HomefinderResult(BaseModel):
    user_profile: UserProfile
    city_analyses: List[CityAnalysis]
    recommended_city: str
    home_listings: List[HomeListing]
    financial_analysis: FinancialAnalysis
    sale_timeline: Optional[SaleTimeline] = None
    executive_summary: str
    next_steps: List[str]

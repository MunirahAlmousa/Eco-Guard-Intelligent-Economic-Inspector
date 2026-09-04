import os
from fastapi import FastAPI
from pydantic import BaseModel
from agents import run_demographic_agent, run_financial_agent, run_manager_agent

app = FastAPI(title="Eco-Guard API", description="Household Survey Data Verification System")

class SurveyRecord(BaseModel):
    age: int
    marital_status: str
    education: str
    occupation: str
    family_size: int
    region: str
    income: float
    actual_expenses: float
    housing_type: str
    electricity_bill: float

@app.get("/health")
def health():
    return {"status": "running", "system": "Eco-Guard"}

@app.post("/agent/demographic")
def demographic(record: SurveyRecord):
    return run_demographic_agent(record.dict())

@app.post("/agent/financial")
def financial(record: SurveyRecord):
    return run_financial_agent(record.dict())

@app.post("/agent/manager")
def manager(record: SurveyRecord):
    demo = run_demographic_agent(record.dict())
    fin = run_financial_agent(record.dict())
    return run_manager_agent(demo, fin, record.dict())

@app.post("/analyze")
def analyze(record: SurveyRecord):
    demo = run_demographic_agent(record.dict())
    fin = run_financial_agent(record.dict())
    mgr = run_manager_agent(demo, fin, record.dict())
    return {"demographic": demo, "financial": fin, "manager": mgr}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)


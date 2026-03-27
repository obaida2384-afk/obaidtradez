from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================== MODELS =====================

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class StockRequest(BaseModel):
    symbol: str

class StockResponse(BaseModel):
    symbol: str
    price: Optional[str] = None
    change: Optional[str] = None
    change_percent: Optional[str] = None
    volume: Optional[str] = None
    last_trading_day: Optional[str] = None
    error: Optional[str] = None

# ===================== CHAT SERVICE =====================

async def get_obaid_response(message: str, session_id: str) -> str:
    """Get response from Obaid AI using OpenAI GPT-5.2 via Emergent"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    system_message = """You are Obaid, an expert AI financial assistant. You specialize in:
    
1. **Financial Formulas**: Explain and calculate financial metrics like ROI, NPV, IRR, WACC, P/E ratio, EPS, etc.
2. **Stock Analysis**: Provide insights on stock performance, market trends, and company fundamentals.
3. **Revenue Predictions**: Analyze growth patterns and provide revenue forecasting insights.
4. **Financial Education**: Explain complex financial concepts in simple terms.

Guidelines:
- Always be precise with numbers and formulas
- When providing formulas, show the mathematical notation clearly
- If asked about specific stock prices, recommend using the stock lookup feature
- Be professional but approachable
- Use markdown formatting for better readability
- For calculations, show step-by-step work

You ONLY answer questions related to finance, investing, stocks, economics, and business. 
If asked about unrelated topics, politely redirect to financial topics."""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=message)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# ===================== STOCK SERVICE =====================

async def get_stock_quote(symbol: str) -> dict:
    """Fetch real-time stock quote from Alpha Vantage"""
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                return {
                    "symbol": quote.get("01. symbol", symbol),
                    "price": quote.get("05. price"),
                    "change": quote.get("09. change"),
                    "change_percent": quote.get("10. change percent"),
                    "volume": quote.get("06. volume"),
                    "last_trading_day": quote.get("07. latest trading day"),
                    "error": None
                }
            elif "Note" in data:
                return {"symbol": symbol, "error": "API rate limit reached. Please try again later."}
            else:
                return {"symbol": symbol, "error": f"No data found for symbol: {symbol}"}
    except Exception as e:
        logger.error(f"Stock API error: {e}")
        return {"symbol": symbol, "error": str(e)}

# ===================== ROUTES =====================

@api_router.get("/")
async def root():
    return {"message": "Obaid Finance AI API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_obaid(request: ChatRequest):
    """Chat with Obaid AI assistant"""
    session_id = request.session_id or str(uuid.uuid4())
    
    # Store user message
    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Get AI response
    response = await get_obaid_response(request.message, session_id)
    
    # Store AI response
    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return ChatResponse(response=response, session_id=session_id)

@api_router.get("/chat/history/{session_id}", response_model=List[ChatMessage])
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    messages = await db.chat_history.find(
        {"session_id": session_id}, 
        {"_id": 0, "session_id": 0}
    ).sort("timestamp", 1).to_list(100)
    return messages

@api_router.post("/stock", response_model=StockResponse)
async def get_stock_price(request: StockRequest):
    """Get real-time stock quote"""
    result = await get_stock_quote(request.symbol.upper())
    return StockResponse(**result)

@api_router.get("/stock/{symbol}", response_model=StockResponse)
async def get_stock_by_symbol(symbol: str):
    """Get real-time stock quote by symbol"""
    result = await get_stock_quote(symbol.upper())
    return StockResponse(**result)

# ===================== INFOGRAPHIC DATA =====================

@api_router.get("/infographic/data")
async def get_infographic_data():
    """Get data for the AI in Finance infographic report"""
    return {
        "page1": {
            "title": "AI Agents in Financial Services: The Landscape",
            "year": "2024-2025",
            "key_stats": [
                {"label": "Firms Using AI", "value": "73%", "description": "of financial services firms"},
                {"label": "AI Investment", "value": "$35B", "description": "annual spending globally"},
                {"label": "Cost Reduction", "value": "25%", "description": "average operational savings"},
                {"label": "ROI Timeline", "value": "18mo", "description": "average time to positive ROI"}
            ],
            "adoption_by_sector": [
                {"name": "Investment Banking", "value": 82},
                {"name": "Asset Management", "value": 78},
                {"name": "Retail Banking", "value": 71},
                {"name": "Insurance", "value": 65},
                {"name": "Wealth Management", "value": 58}
            ],
            "use_cases": [
                {"name": "Fraud Detection", "percentage": 89, "description": "Real-time transaction monitoring"},
                {"name": "Customer Service", "percentage": 76, "description": "AI chatbots and virtual assistants"},
                {"name": "Risk Assessment", "percentage": 72, "description": "Credit scoring and loan approval"},
                {"name": "Trading Algorithms", "percentage": 68, "description": "Automated trading strategies"},
                {"name": "Compliance", "percentage": 61, "description": "Regulatory reporting automation"}
            ]
        },
        "page2": {
            "title": "Adoption Velocity & Implementation",
            "adoption_timeline": [
                {"year": "2020", "adoption": 32},
                {"year": "2021", "adoption": 45},
                {"year": "2022", "adoption": 58},
                {"year": "2023", "adoption": 67},
                {"year": "2024", "adoption": 73},
                {"year": "2025", "adoption": 81}
            ],
            "investment_breakdown": [
                {"category": "Infrastructure", "amount": 12.5, "color": "#044738"},
                {"category": "AI/ML Platforms", "amount": 9.8, "color": "#D4AF37"},
                {"category": "Data Management", "amount": 7.2, "color": "#10B981"},
                {"category": "Talent & Training", "amount": 5.5, "color": "#F97316"}
            ],
            "implementation_challenges": [
                {"challenge": "Data Quality", "severity": 85},
                {"challenge": "Legacy Systems", "severity": 78},
                {"challenge": "Regulatory Compliance", "severity": 72},
                {"challenge": "Talent Shortage", "severity": 68},
                {"challenge": "Integration Complexity", "severity": 65}
            ],
            "regional_adoption": [
                {"region": "North America", "percentage": 79},
                {"region": "Europe", "percentage": 71},
                {"region": "Asia Pacific", "percentage": 68},
                {"region": "Middle East", "percentage": 52},
                {"region": "Latin America", "percentage": 41}
            ]
        },
        "page3": {
            "title": "Future Projections & Strategic Outlook",
            "market_forecast": [
                {"year": "2024", "value": 35},
                {"year": "2025", "value": 48},
                {"year": "2026", "value": 65},
                {"year": "2027", "value": 89},
                {"year": "2028", "value": 120}
            ],
            "emerging_trends": [
                {"trend": "Generative AI for Document Processing", "impact": "High", "timeline": "2024-2025"},
                {"trend": "Autonomous Trading Agents", "impact": "Very High", "timeline": "2025-2026"},
                {"trend": "Real-time Risk Prediction", "impact": "High", "timeline": "2024-2025"},
                {"trend": "Personalized Financial Planning", "impact": "Medium", "timeline": "2025-2027"},
                {"trend": "Blockchain + AI Integration", "impact": "Medium", "timeline": "2026-2028"}
            ],
            "job_impact": {
                "created": 1200000,
                "transformed": 3500000,
                "automated": 800000
            },
            "recommendations": [
                "Invest in data infrastructure before AI deployment",
                "Prioritize explainable AI for regulatory compliance",
                "Build hybrid human-AI workflows",
                "Focus on customer experience use cases first",
                "Establish AI governance frameworks early"
            ],
            "benefits": [
                "24/7 automated customer support and query resolution",
                "Real-time fraud detection with 99.5% accuracy",
                "50% faster loan processing and approval",
                "Personalized investment recommendations",
                "Automated compliance reporting"
            ],
            "cautions": [
                "Ensure robust data privacy and security measures",
                "Maintain human oversight for critical decisions",
                "Address algorithmic bias in credit decisions",
                "Plan for regulatory changes and audits",
                "Invest in employee upskilling programs"
            ]
        }
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

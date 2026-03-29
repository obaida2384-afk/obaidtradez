"""
ObaidTradez - Enhanced Investment Signal Engine
With dynamic thresholds, proper scoring, and comprehensive explanations
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)

# ===================== ENHANCED MODELS =====================

class ScoreDrivers(BaseModel):
    """What's driving the score up or down"""
    boosters: List[str] = []  # What increased the score
    detractors: List[str] = []  # What reduced the score
    biggest_weakness: Optional[str] = None
    data_impact: Optional[str] = None  # Impact of missing data

class ValuationSummary(BaseModel):
    pe_ratio: Optional[float] = None
    pe_vs_sector: Optional[str] = None  # "Below", "In-line", "Premium"
    ev_ebitda: Optional[float] = None
    ev_ebitda_vs_sector: Optional[str] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    intrinsic_value: Optional[float] = None
    classification: str = "N/A"  # "Undervalued", "Fair", "Overvalued"
    upside_potential: Optional[str] = None

class BusinessQuality(BaseModel):
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roic: Optional[float] = None
    earnings_consistency: str = "N/A"
    quality_rating: str = "N/A"  # "Excellent", "Good", "Average", "Poor"

class GrowthProfile(BaseModel):
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    growth_trend: str = "N/A"  # "Accelerating", "Stable", "Decelerating", "Declining"
    growth_rating: str = "N/A"

class EnhancedInvestmentSignal(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    signal: str
    confidence: float
    
    # Scores
    overall_score: float
    valuation_score: float
    quality_score: float
    growth_score: float
    financial_strength: float
    risk_score: float
    
    # Detailed summaries
    valuation_summary: ValuationSummary
    business_quality: BusinessQuality
    growth_profile: GrowthProfile
    score_drivers: ScoreDrivers
    
    # Cases
    bull_case: List[str] = []
    bear_case: List[str] = []
    risks: List[str] = []
    
    # Reasoning
    reasoning: str
    category: str
    
    # Metadata
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    market_cap: Optional[float] = None
    market_cap_label: Optional[str] = None
    data_completeness: float = 100.0
    last_updated: Optional[str] = None
    
    # Percentile ranking (for dynamic thresholds)
    percentile_rank: Optional[float] = None


class EnhancedInvestmentEngine:
    """
    Enhanced investment analysis engine with:
    - Correct FMP field names
    - Dynamic percentile-based thresholds
    - Comprehensive explanations
    - Balanced factor weights
    """
    
    # Sector benchmarks (realistic current market values)
    SECTOR_BENCHMARKS = {
        "Technology": {"pe": 30, "ev_ebitda": 20, "roe": 18, "growth": 12, "margin": 20},
        "Healthcare": {"pe": 25, "ev_ebitda": 15, "roe": 15, "growth": 8, "margin": 15},
        "Financial Services": {"pe": 14, "ev_ebitda": 10, "roe": 12, "growth": 5, "margin": 25},
        "Consumer Cyclical": {"pe": 22, "ev_ebitda": 14, "roe": 15, "growth": 8, "margin": 10},
        "Consumer Defensive": {"pe": 24, "ev_ebitda": 15, "roe": 20, "growth": 4, "margin": 12},
        "Industrials": {"pe": 22, "ev_ebitda": 13, "roe": 15, "growth": 6, "margin": 10},
        "Energy": {"pe": 12, "ev_ebitda": 6, "roe": 15, "growth": 3, "margin": 12},
        "Basic Materials": {"pe": 15, "ev_ebitda": 8, "roe": 12, "growth": 4, "margin": 10},
        "Real Estate": {"pe": 35, "ev_ebitda": 18, "roe": 8, "growth": 4, "margin": 30},
        "Utilities": {"pe": 18, "ev_ebitda": 10, "roe": 10, "growth": 3, "margin": 12},
        "Communication Services": {"pe": 22, "ev_ebitda": 12, "roe": 15, "growth": 8, "margin": 18},
        "default": {"pe": 22, "ev_ebitda": 14, "roe": 15, "growth": 7, "margin": 15}
    }
    
    # Factor weights (balanced - quality and growth matter as much as valuation)
    FACTOR_WEIGHTS = {
        "valuation": 0.20,
        "quality": 0.25,
        "growth": 0.20,
        "financial_strength": 0.20,
        "risk": 0.15
    }
    
    def __init__(self, api_client, db):
        self.api_client = api_client
        self.db = db
    
    def _get_market_cap_label(self, market_cap: float) -> str:
        if not market_cap:
            return "Unknown"
        if market_cap >= 200e9:
            return "Mega Cap"
        elif market_cap >= 10e9:
            return "Large Cap"
        elif market_cap >= 2e9:
            return "Mid Cap"
        elif market_cap >= 300e6:
            return "Small Cap"
        return "Micro Cap"
    
    async def analyze_stock(self, symbol: str) -> Optional[EnhancedInvestmentSignal]:
        """Comprehensive stock analysis with proper field mapping and explanations"""
        try:
            # Fetch all data sources
            quote, profile, ratios, metrics, growth = await asyncio.gather(
                self.api_client.fmp_quote(symbol),
                self.api_client.fmp_profile(symbol),
                self.api_client.fmp_ratios(symbol),
                self.api_client.fmp_metrics(symbol),
                self.api_client.fmp_growth(symbol),
                return_exceptions=True
            )
            
            # Handle exceptions
            quote = None if isinstance(quote, Exception) else quote
            profile = None if isinstance(profile, Exception) else profile
            ratios = None if isinstance(ratios, Exception) else ratios
            metrics = None if isinstance(metrics, Exception) else metrics
            growth = None if isinstance(growth, Exception) else growth
            
            # Calculate data completeness
            data_sources = [quote, profile, ratios, metrics, growth]
            available_sources = sum(1 for d in data_sources if d)
            data_completeness = (available_sources / len(data_sources)) * 100
            
            # Require at least quote or profile
            if not quote and not profile:
                return None
            
            # Merge all data
            data = {}
            for d in [ratios, metrics, growth, quote, profile]:
                if d:
                    data.update(d)
            
            # Basic info
            sector = data.get('sector', 'default')
            benchmark = self.SECTOR_BENCHMARKS.get(sector, self.SECTOR_BENCHMARKS['default'])
            price = data.get('price', 0)
            market_cap = data.get('marketCap') or data.get('mktCap', 0)
            
            # Initialize tracking
            bull_case = []
            bear_case = []
            risks = []
            score_boosters = []
            score_detractors = []
            
            # ==================== VALUATION SCORE ====================
            valuation_score = 55  # Start slightly positive (most stocks aren't deeply undervalued)
            
            # P/E Ratio - CORRECT FIELD NAME
            pe = data.get('priceToEarningsRatioTTM') or data.get('peRatioTTM') or data.get('pe')
            pe_vs_sector = "N/A"
            if pe and pe > 0:
                sector_pe = benchmark['pe']
                if pe < sector_pe * 0.7:
                    valuation_score += 20
                    pe_vs_sector = "Discount"
                    bull_case.append(f"Trading at discount P/E of {pe:.1f}x vs sector {sector_pe}x")
                    score_boosters.append(f"P/E discount to sector (+20)")
                elif pe < sector_pe * 0.9:
                    valuation_score += 10
                    pe_vs_sector = "Below"
                    score_boosters.append(f"P/E below sector average (+10)")
                elif pe <= sector_pe * 1.2:
                    valuation_score += 3
                    pe_vs_sector = "In-line"
                elif pe <= sector_pe * 1.5:
                    valuation_score -= 5
                    pe_vs_sector = "Premium"
                    score_detractors.append(f"P/E premium to sector (-5)")
                else:
                    valuation_score -= 12
                    pe_vs_sector = "Expensive"
                    bear_case.append(f"Expensive P/E of {pe:.1f}x vs sector {sector_pe}x")
                    score_detractors.append(f"High P/E valuation (-12)")
            
            # EV/EBITDA - CORRECT FIELD NAME
            ev_ebitda = data.get('evToEBITDATTM') or data.get('enterpriseValueMultipleTTM') or data.get('enterpriseValueOverEBITDATTM')
            ev_vs_sector = "N/A"
            if ev_ebitda and 0 < ev_ebitda < 100:
                sector_ev = benchmark['ev_ebitda']
                if ev_ebitda < sector_ev * 0.7:
                    valuation_score += 15
                    ev_vs_sector = "Low"
                    bull_case.append(f"Attractive EV/EBITDA of {ev_ebitda:.1f}x")
                    score_boosters.append(f"Low EV/EBITDA (+15)")
                elif ev_ebitda < sector_ev:
                    valuation_score += 7
                    ev_vs_sector = "Below Average"
                    score_boosters.append(f"Below average EV/EBITDA (+7)")
                elif ev_ebitda > sector_ev * 1.5:
                    valuation_score -= 8
                    ev_vs_sector = "High"
                    score_detractors.append(f"High EV/EBITDA (-8)")
            
            # Price to Book - CORRECT FIELD NAME
            ptb = data.get('priceToBookRatioTTM') or data.get('pbRatioTTM')
            if ptb and ptb > 0:
                if ptb < 1.5:
                    valuation_score += 8
                    bull_case.append(f"Low price-to-book of {ptb:.1f}x")
                    score_boosters.append(f"Low P/B ratio (+8)")
                elif ptb < 3:
                    valuation_score += 3
                elif ptb > 10:
                    valuation_score -= 5
            
            # Price to Sales
            pts = data.get('priceToSalesRatioTTM')
            
            # Cap valuation score
            valuation_score = max(20, min(95, valuation_score))
            
            # ==================== QUALITY SCORE ====================
            quality_score = 50  # Neutral start
            
            # ROE - CORRECT FIELD NAME (comes as decimal)
            roe = data.get('returnOnEquityTTM') or data.get('roeTTM')
            roe_pct = None
            quality_rating = "Average"
            if roe is not None:
                roe_pct = roe * 100 if abs(roe) < 1 else roe
                sector_roe = benchmark['roe']
                if roe_pct > 25:
                    quality_score += 25
                    bull_case.append(f"Exceptional ROE of {roe_pct:.1f}%")
                    score_boosters.append(f"High ROE (+25)")
                    quality_rating = "Excellent"
                elif roe_pct > 18:
                    quality_score += 18
                    score_boosters.append(f"Strong ROE (+18)")
                    quality_rating = "Good"
                elif roe_pct > 12:
                    quality_score += 10
                    score_boosters.append(f"Decent ROE (+10)")
                elif roe_pct > 5:
                    quality_score += 0
                elif roe_pct > 0:
                    quality_score -= 10
                    score_detractors.append(f"Low ROE (-10)")
                    quality_rating = "Below Average"
                else:
                    quality_score -= 20
                    bear_case.append(f"Negative ROE of {roe_pct:.1f}%")
                    score_detractors.append(f"Negative ROE (-20)")
                    quality_rating = "Poor"
            
            # Net Margin - CORRECT FIELD NAME
            net_margin = data.get('netProfitMarginTTM') or data.get('netIncomeMarginTTM')
            net_margin_pct = None
            if net_margin is not None:
                net_margin_pct = net_margin * 100 if abs(net_margin) < 1 else net_margin
                sector_margin = benchmark['margin']
                if net_margin_pct > sector_margin * 1.5:
                    quality_score += 15
                    bull_case.append(f"Excellent profit margin of {net_margin_pct:.1f}%")
                    score_boosters.append(f"High margins (+15)")
                elif net_margin_pct > sector_margin:
                    quality_score += 8
                    score_boosters.append(f"Above-average margins (+8)")
                elif net_margin_pct > sector_margin * 0.5:
                    quality_score += 2
                elif net_margin_pct > 0:
                    quality_score -= 5
                    score_detractors.append(f"Thin margins (-5)")
                else:
                    quality_score -= 15
                    bear_case.append(f"Negative margins")
                    score_detractors.append(f"Unprofitable (-15)")
                    risks.append("Profitability concerns")
            
            # Gross Margin
            gross_margin = data.get('grossProfitMarginTTM')
            gross_margin_pct = None
            if gross_margin:
                gross_margin_pct = gross_margin * 100 if abs(gross_margin) < 1 else gross_margin
                if gross_margin_pct > 50:
                    quality_score += 8
                    score_boosters.append(f"High gross margin (+8)")
                elif gross_margin_pct > 30:
                    quality_score += 3
            
            # Cap quality score
            quality_score = max(20, min(95, quality_score))
            
            # ==================== GROWTH SCORE ====================
            growth_score = 50  # Neutral start
            
            # Revenue Growth
            rev_growth = data.get('revenueGrowth')
            rev_growth_pct = None
            growth_trend = "Stable"
            growth_rating = "Average"
            if rev_growth is not None:
                rev_growth_pct = rev_growth * 100 if abs(rev_growth) < 1 else rev_growth
                sector_growth = benchmark['growth']
                if rev_growth_pct > 25:
                    growth_score += 25
                    bull_case.append(f"Strong revenue growth of {rev_growth_pct:.1f}%")
                    score_boosters.append(f"High growth (+25)")
                    growth_trend = "Accelerating"
                    growth_rating = "Excellent"
                elif rev_growth_pct > 15:
                    growth_score += 18
                    score_boosters.append(f"Solid growth (+18)")
                    growth_trend = "Accelerating"
                    growth_rating = "Good"
                elif rev_growth_pct > 8:
                    growth_score += 10
                    score_boosters.append(f"Decent growth (+10)")
                    growth_rating = "Good"
                elif rev_growth_pct > 3:
                    growth_score += 3
                    growth_trend = "Stable"
                elif rev_growth_pct > 0:
                    growth_score += 0
                    growth_trend = "Slow"
                elif rev_growth_pct > -5:
                    growth_score -= 8
                    score_detractors.append(f"Declining revenue (-8)")
                    growth_trend = "Decelerating"
                    growth_rating = "Below Average"
                else:
                    growth_score -= 18
                    bear_case.append(f"Revenue declining {rev_growth_pct:.1f}%")
                    score_detractors.append(f"Revenue contraction (-18)")
                    growth_trend = "Declining"
                    growth_rating = "Poor"
                    risks.append("Revenue declining")
            
            # Earnings Growth
            eps_growth = data.get('epsgrowth') or data.get('netIncomeGrowth')
            eps_growth_pct = None
            if eps_growth is not None:
                eps_growth_pct = eps_growth * 100 if abs(eps_growth) < 1 else eps_growth
                if eps_growth_pct > 20:
                    growth_score += 12
                    score_boosters.append(f"Strong EPS growth (+12)")
                elif eps_growth_pct > 10:
                    growth_score += 6
                elif eps_growth_pct < -10:
                    growth_score -= 10
                    score_detractors.append(f"EPS declining (-10)")
            
            # Cap growth score
            growth_score = max(20, min(95, growth_score))
            
            # ==================== FINANCIAL STRENGTH ====================
            strength_score = 55  # Start slightly positive
            
            # Debt to Equity - CORRECT FIELD NAME
            de = data.get('debtToEquityRatioTTM') or data.get('debtEquityRatioTTM')
            if de is not None:
                if de < 0.3:
                    strength_score += 18
                    bull_case.append(f"Very low debt (D/E: {de:.2f})")
                    score_boosters.append(f"Strong balance sheet (+18)")
                elif de < 0.7:
                    strength_score += 10
                    score_boosters.append(f"Low leverage (+10)")
                elif de < 1.2:
                    strength_score += 3
                elif de < 2:
                    strength_score -= 8
                    score_detractors.append(f"High leverage (-8)")
                else:
                    strength_score -= 18
                    bear_case.append(f"Very high debt (D/E: {de:.2f})")
                    score_detractors.append(f"Excessive debt (-18)")
                    risks.append(f"High leverage (D/E: {de:.1f})")
            
            # Current Ratio - CORRECT FIELD NAME
            current = data.get('currentRatioTTM')
            if current:
                if current > 2.5:
                    strength_score += 10
                    score_boosters.append(f"Strong liquidity (+10)")
                elif current > 1.5:
                    strength_score += 5
                elif current < 1:
                    strength_score -= 12
                    bear_case.append(f"Weak liquidity (Current ratio: {current:.2f})")
                    score_detractors.append(f"Low liquidity (-12)")
                    risks.append("Liquidity concerns")
            
            # Free Cash Flow
            fcf_per_share = data.get('freeCashFlowPerShareTTM')
            if fcf_per_share and fcf_per_share > 0:
                if price > 0:
                    fcf_yield = (fcf_per_share / price) * 100
                    if fcf_yield > 8:
                        strength_score += 12
                        bull_case.append(f"Strong FCF yield of {fcf_yield:.1f}%")
                        score_boosters.append(f"High FCF yield (+12)")
                    elif fcf_yield > 5:
                        strength_score += 6
                    elif fcf_yield > 3:
                        strength_score += 2
            elif fcf_per_share and fcf_per_share < 0:
                strength_score -= 10
                bear_case.append("Negative free cash flow")
                score_detractors.append(f"Negative FCF (-10)")
                risks.append("Cash flow concerns")
            
            # Cap strength score
            strength_score = max(20, min(95, strength_score))
            
            # ==================== RISK SCORE ====================
            risk_score = 65  # Start positive (most stocks are investable)
            
            # Beta (volatility)
            beta = data.get('beta')
            if beta:
                if beta < 0.8:
                    risk_score += 12
                    score_boosters.append(f"Low volatility (+12)")
                elif beta < 1.2:
                    risk_score += 5
                elif beta > 1.8:
                    risk_score -= 15
                    score_detractors.append(f"High volatility (-15)")
                    risks.append(f"High volatility (beta: {beta:.2f})")
                elif beta > 1.4:
                    risk_score -= 7
            
            # Market cap risk
            if market_cap:
                if market_cap > 100e9:
                    risk_score += 10  # Large cap = lower risk
                    score_boosters.append(f"Large cap stability (+10)")
                elif market_cap > 10e9:
                    risk_score += 5
                elif market_cap < 2e9:
                    risk_score -= 10
                    risks.append("Small cap volatility")
                    score_detractors.append(f"Small cap risk (-10)")
            
            # Cap risk score
            risk_score = max(20, min(95, risk_score))
            
            # ==================== OVERALL SCORE ====================
            # Apply data completeness penalty (mild)
            completeness_factor = 1.0
            data_impact = None
            if data_completeness < 60:
                completeness_factor = 0.95
                data_impact = "Score reduced 5% due to limited data"
                score_detractors.append(f"Limited data (-5%)")
            elif data_completeness < 80:
                completeness_factor = 0.98
                data_impact = "Score reduced 2% due to some missing data"
            
            overall_score = (
                valuation_score * self.FACTOR_WEIGHTS["valuation"] +
                quality_score * self.FACTOR_WEIGHTS["quality"] +
                growth_score * self.FACTOR_WEIGHTS["growth"] +
                strength_score * self.FACTOR_WEIGHTS["financial_strength"] +
                risk_score * self.FACTOR_WEIGHTS["risk"]
            ) * completeness_factor
            
            # Find biggest weakness
            scores = {
                "Valuation": valuation_score,
                "Quality": quality_score,
                "Growth": growth_score,
                "Financial Strength": strength_score,
                "Risk": risk_score
            }
            biggest_weakness = min(scores, key=scores.get)
            
            # ==================== INTRINSIC VALUE ====================
            intrinsic_value = None
            upside_potential = None
            valuation_class = "N/A"
            
            if fcf_per_share and fcf_per_share > 0 and price > 0:
                # Simple DCF-like estimate
                growth_rate = min(0.15, max(0.02, (rev_growth_pct or 5) / 100))
                discount_rate = 0.10
                terminal_multiple = 12
                intrinsic_value = fcf_per_share * terminal_multiple * (1 + growth_rate)
                
                upside = ((intrinsic_value / price) - 1) * 100
                upside_potential = f"{upside:+.1f}%"
                
                if upside > 30:
                    valuation_class = "Undervalued"
                elif upside > 10:
                    valuation_class = "Slightly Undervalued"
                elif upside > -10:
                    valuation_class = "Fair Value"
                elif upside > -25:
                    valuation_class = "Slightly Overvalued"
                else:
                    valuation_class = "Overvalued"
            
            # ==================== BUILD SUMMARIES ====================
            valuation_summary = ValuationSummary(
                pe_ratio=pe,
                pe_vs_sector=pe_vs_sector,
                ev_ebitda=ev_ebitda,
                ev_ebitda_vs_sector=ev_vs_sector,
                price_to_book=ptb,
                price_to_sales=pts,
                intrinsic_value=round(intrinsic_value, 2) if intrinsic_value else None,
                classification=valuation_class,
                upside_potential=upside_potential
            )
            
            business_quality = BusinessQuality(
                gross_margin=gross_margin_pct,
                net_margin=net_margin_pct,
                roe=roe_pct,
                roic=None,  # Not available in current data
                earnings_consistency="N/A",
                quality_rating=quality_rating
            )
            
            growth_profile = GrowthProfile(
                revenue_growth=rev_growth_pct,
                earnings_growth=eps_growth_pct,
                growth_trend=growth_trend,
                growth_rating=growth_rating
            )
            
            score_drivers = ScoreDrivers(
                boosters=score_boosters[:6],
                detractors=score_detractors[:6],
                biggest_weakness=f"{biggest_weakness} ({scores[biggest_weakness]:.0f})",
                data_impact=data_impact
            )
            
            # ==================== GENERATE REASONING ====================
            reasoning_parts = []
            if bull_case:
                reasoning_parts.append(f"Strengths: {'; '.join(bull_case[:3])}")
            if bear_case:
                reasoning_parts.append(f"Concerns: {'; '.join(bear_case[:2])}")
            reasoning_parts.append(f"Overall score {overall_score:.1f}/100")
            reasoning = ". ".join(reasoning_parts)
            
            return EnhancedInvestmentSignal(
                symbol=symbol,
                name=data.get('companyName', symbol),
                price=price,
                signal="Pending",  # Will be set by categorization
                confidence=min(overall_score / 100, 0.95),
                overall_score=round(overall_score, 1),
                valuation_score=round(valuation_score, 1),
                quality_score=round(quality_score, 1),
                growth_score=round(growth_score, 1),
                financial_strength=round(strength_score, 1),
                risk_score=round(risk_score, 1),
                valuation_summary=valuation_summary,
                business_quality=business_quality,
                growth_profile=growth_profile,
                score_drivers=score_drivers,
                bull_case=bull_case[:5],
                bear_case=bear_case[:5],
                risks=risks[:5],
                reasoning=reasoning,
                category="Pending",
                sector=sector,
                industry=data.get('industry'),
                country=data.get('country', 'US'),
                market_cap=market_cap,
                market_cap_label=self._get_market_cap_label(market_cap),
                data_completeness=round(data_completeness, 1),
                last_updated=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Analysis error for {symbol}: {e}")
            return None
    
    def apply_dynamic_thresholds(self, signals: List[EnhancedInvestmentSignal]) -> List[EnhancedInvestmentSignal]:
        """Apply percentile-based categorization to ensure top categories are populated"""
        if not signals:
            return signals
        
        # Sort by overall score
        signals = sorted(signals, key=lambda x: x.overall_score, reverse=True)
        total = len(signals)
        
        # Calculate percentiles
        for i, signal in enumerate(signals):
            signal.percentile_rank = ((total - i) / total) * 100
        
        # Get score distribution
        scores = [s.overall_score for s in signals]
        p90_score = scores[int(total * 0.10)] if total > 10 else scores[0]
        p75_score = scores[int(total * 0.25)] if total > 4 else scores[0]
        p50_score = scores[int(total * 0.50)] if total > 2 else scores[0]
        p25_score = scores[int(total * 0.75)] if total > 4 else scores[-1]
        
        # Dynamic thresholds based on distribution
        hot_threshold = max(p90_score, 65)  # Top 10% or at least 65
        bullish_threshold = max(p75_score, 58)  # Top 25% or at least 58
        watch_threshold = max(p50_score, 48)  # Top 50% or at least 48
        
        for signal in signals:
            score = signal.overall_score
            percentile = signal.percentile_rank
            
            # Categorize based on both absolute score AND percentile
            if percentile >= 90 and score >= 60:
                signal.category = "Hot"
                signal.signal = "Buy"
            elif percentile >= 75 and score >= 55:
                signal.category = "Bullish"
                signal.signal = "Buy"
            elif signal.valuation_summary.classification == "Undervalued" and score >= 50:
                signal.category = "Undervalued"
                signal.signal = "Watchlist"
            elif score >= watch_threshold:
                signal.category = "Watch"
                signal.signal = "Watchlist"
            elif signal.valuation_summary.classification == "Overvalued" and score < 45:
                signal.category = "Overpriced"
                signal.signal = "Sell"
            elif score < 40:
                signal.category = "Bearish"
                signal.signal = "Sell"
            else:
                # Check if overvalued despite decent score
                if signal.valuation_score < 45:
                    signal.category = "Overpriced"
                    signal.signal = "Hold"
                else:
                    signal.category = "Watch"
                    signal.signal = "Watchlist"
        
        return signals
    
    async def batch_analyze(self, symbols: List[str], batch_size: int = 10) -> List[EnhancedInvestmentSignal]:
        """Analyze multiple symbols in batches"""
        all_signals = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            signals = await asyncio.gather(*[self.analyze_stock(s) for s in batch])
            valid_signals = [s for s in signals if s]
            all_signals.extend(valid_signals)
            
            # Delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        # Apply dynamic thresholds
        return self.apply_dynamic_thresholds(all_signals)


def convert_to_legacy_format(signal: EnhancedInvestmentSignal) -> dict:
    """Convert enhanced signal to legacy format for backward compatibility"""
    return {
        "symbol": signal.symbol,
        "name": signal.name,
        "price": signal.price,
        "signal": signal.signal,
        "confidence": signal.confidence,
        "overall_score": signal.overall_score,
        "valuation_score": signal.valuation_score,
        "quality_score": signal.quality_score,
        "growth_score": signal.growth_score,
        "financial_strength": signal.financial_strength,
        "risk_score": signal.risk_score,
        "intrinsic_value": signal.valuation_summary.intrinsic_value,
        "upside_potential": signal.valuation_summary.upside_potential,
        "bull_case": signal.bull_case,
        "bear_case": signal.bear_case,
        "risks": signal.risks,
        "reasoning": signal.reasoning,
        "category": signal.category,
        "sector": signal.sector,
        "industry": signal.industry,
        "country": signal.country,
        "market_cap": signal.market_cap,
        "market_cap_label": signal.market_cap_label,
        "data_completeness": signal.data_completeness,
        "last_updated": signal.last_updated,
        "percentile_rank": signal.percentile_rank,
        # Enhanced fields
        "valuation_summary": signal.valuation_summary.dict(),
        "business_quality": signal.business_quality.dict(),
        "growth_profile": signal.growth_profile.dict(),
        "score_drivers": signal.score_drivers.dict()
    }

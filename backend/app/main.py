import logging
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from app.config.config import settings
from app.database.session import SessionLocal, engine, Base
from app.database.seeder import seed_database
from app.api import auth, policies, dataset, dashboard, reports, evaluation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Prometheus Monitoring Setup
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "http_status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"]
)

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Policy Conflict & Staleness Detector API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics sub-app
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Request duration middleware for Prometheus logging
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    # Process request
    response = await call_next(request)
    
    # Calculate performance metrics
    duration = time.time() - start_time
    status_code = str(response.status_code)
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response

# Startup database initialization
@app.on_event("startup")
def startup_populate():
    logger.info("Application starting up. Initializing database and pre-seeding sample dataset...")
    db = SessionLocal()
    try:
        # Create all tables (especially useful for local SQLite prototyping)
        Base.metadata.create_all(bind=engine)
        
        # Load JSON files and seed database
        seed_database(db)
    except Exception as e:
        logger.exception(f"Critical error during startup database seeding: {str(e)}")
    finally:
        db.close()

# Root redirect and health check
@app.get("/", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "timestamp": time.time()
    }

# Register APIs
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(policies.router, prefix=settings.API_V1_STR)
app.include_router(dataset.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(evaluation.router, prefix=settings.API_V1_STR)

# Direct analysis endpoint for policy_nexus / dashboard
from pydantic import BaseModel
from typing import List, Dict, Any

class DocumentInput(BaseModel):
    name: str
    text: str

class AnalyseRequest(BaseModel):
    documents: List[DocumentInput]

@app.post("/api/analyse")
async def analyse_policies_endpoint(req: AnalyseRequest):
    """
    POST /api/analyse - Live automated parsing, obligation extraction,
    conflict detection, and GRC health reporting.
    """
    from datetime import datetime
    import re
    from app.llm.llm_client import LLMClient
    
    docs = req.documents
    all_obligations = []
    findings = []
    policy_health = []
    timeline = []
    
    topic_counts = {}
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    # 1. Process documents
    for doc in docs:
        doc_name = doc.name
        doc_text = doc.text
        
        # 1a. Extract obligations
        extracted = LLMClient.extract_obligations(doc_text)
        for i, entry in enumerate(extracted):
            ob_id = f"O{len(all_obligations) + 1}"
            topic = entry.get("topic", "general").replace("_", " ")
            ob_data = {
                "id": ob_id,
                "policy": doc_name,
                "section": entry.get("section", f"1.{i+1}"),
                "topic": topic,
                "strength": entry.get("strength", "must"),
                "scope": entry.get("scope", "all"),
                "sentence": entry.get("obligation_text", entry.get("sentence", doc_text[:100]))
            }
            all_obligations.append(ob_data)
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
        # 1b. Check staleness
        last_reviewed_str = "2024-01-01"
        review_date_match = re.search(r"last\s+reviewed:\s*([\d\-]+)", doc_text, re.IGNORECASE)
        is_missing_date = True
        status = "missing"
        
        if review_date_match:
            last_reviewed_str = review_date_match.group(1).strip()
            is_missing_date = False
            try:
                rev_date = datetime.strptime(last_reviewed_str, "%Y-%m-%d")
                days_diff = (datetime.now() - rev_date).days
                months_diff = days_diff / 30.0
                if months_diff > 18:
                    findings.append({
                        "title": f"Stale Policy: {doc_name}",
                        "kind": "STALENESS",
                        "severity": "medium",
                        "policies": [doc_name],
                        "evidence": f"Policy last reviewed on {last_reviewed_str}, which is older than 18 months.",
                        "scopeAnalysis": "Enterprise documentation lifecycle compliance standard.",
                        "recommendation": "Perform a complete policy revision and update the last reviewed metadata date."
                    })
                    severity_counts["medium"] += 1
                    status = "overdue"
                else:
                    status = "within-cycle"
            except Exception:
                status = "missing"
                is_missing_date = True
        else:
            status = "missing"
            
        if is_missing_date:
            findings.append({
                "title": f"Missing Review Date: {doc_name}",
                "kind": "MISSING_METADATA",
                "severity": "low",
                "policies": [doc_name],
                "evidence": "No valid 'Last Reviewed: YYYY-MM-DD' metadata was found in the text.",
                "scopeAnalysis": "Enterprise documentation lifecycle compliance.",
                "recommendation": "Add a metadata header to the policy specifying the last review date."
            })
            severity_counts["low"] += 1
            
        timeline.append({
            "policy": doc_name,
            "date": last_reviewed_str if not is_missing_date else "None",
            "status": status
        })
        
        # 1c. Scan legacy references
        legacy_terms = ["DES", "SHA-1", "SSL", "TLS 1.0", "WEP", "Windows Server 2012"]
        found_legacy = []
        for term in legacy_terms:
            if re.search(r"\b" + re.escape(term) + r"\b", doc_text, re.IGNORECASE):
                found_legacy.append(term)
                
        if found_legacy:
            findings.append({
                "title": f"Legacy references in {doc_name}",
                "kind": "STALENESS",
                "severity": "high",
                "policies": [doc_name],
                "evidence": f"Text references deprecated technology standard(s): {', '.join(found_legacy)}.",
                "scopeAnalysis": "Infrastructure security controls alignment.",
                "recommendation": f"Update policy to mandate modern equivalents (e.g. SHA-256, AES, TLS 1.3, WPA3)."
            })
            severity_counts["high"] += 1
            
    # 2. Pairwise cross-document checks (conflicts / redundancies)
    comparisons = []
    for i in range(len(all_obligations)):
        for j in range(i + 1, len(all_obligations)):
            ob_a = all_obligations[i]
            ob_b = all_obligations[j]
            
            if ob_a["policy"] == ob_b["policy"]:
                continue
                
            if ob_a["topic"] == ob_b["topic"] and ob_a["topic"] != "general":
                analysis = LLMClient.analyze_conflict(ob_a["sentence"], ob_b["sentence"], ob_a["topic"])
                ftype = analysis.get("finding_type", "UNRELATED")
                
                if ftype in ["CONFLICT", "REDUNDANCY", "FALSE_POSITIVE_PRONE"]:
                    decision = "CONFLICT_FOUND" if ftype == "CONFLICT" else "NO_CONFLICT_REDUNDANT"
                    sev = analysis.get("severity", "medium").lower()
                    if sev not in severity_counts:
                        sev = "medium"
                    
                    findings.append({
                        "title": analysis.get("description", f"Contradiction in {ob_a['topic']}"),
                        "kind": ftype,
                        "severity": sev,
                        "policies": [ob_a["policy"], ob_b["policy"]],
                        "evidence": f"'{ob_a['sentence']}' vs '{ob_b['sentence']}'",
                        "scopeAnalysis": analysis.get("explanation", "Potential scope mismatch."),
                        "recommendation": analysis.get("recommendation", "Review policy priorities.")
                    })
                    severity_counts[sev] += 1
                    
                    comparisons.append({
                        "policyA": ob_a["policy"],
                        "domainA": [ob_a["topic"]],
                        "policyB": ob_b["policy"],
                        "domainB": [ob_b["topic"]],
                        "decision": decision,
                        "similarity": str(analysis.get("confidence", 0.85)),
                        "reason": analysis.get("explanation", "Overlap detected.")
                    })
                    
    # 3. Calculate Policy Health cards
    for doc in docs:
        doc_name = doc.name
        doc_findings_count = sum(1 for f in findings if doc_name in f["policies"])
        doc_score = max(0, 100 - doc_findings_count * 10)
        last_reviewed_str = next((t["date"] for t in timeline if t["policy"] == doc_name), "2024-01-01")
        
        policy_health.append({
            "policy": doc_name,
            "score": doc_score,
            "findings": doc_findings_count,
            "lastReviewed": last_reviewed_str
        })
        
    # 4. Scorecard grading (critical=25, high=15, medium=7, low=3)
    deductions = (
        severity_counts.get("critical", 0) * 25 +
        severity_counts.get("high", 0) * 15 +
        severity_counts.get("medium", 0) * 7 +
        severity_counts.get("low", 0) * 3
    )
    score = max(0, 100 - deductions)
    
    rec_list = []
    if severity_counts.get("critical", 0) > 0:
        rec_list.append("Resolve direct logical conflicts between policies (e.g. rotation resets vs MFA).")
    if severity_counts.get("high", 0) > 0:
        rec_list.append("Deprecate legacy technology references (SSL/SHA-1) and update to TLS 1.3/SHA-256.")
    if severity_counts.get("medium", 0) > 0 or severity_counts.get("low", 0) > 0:
        rec_list.append("Harmonize overlapping/redundant requirements and update missing review date headers.")
    if not rec_list:
        rec_list.append("All policies align with enterprise standards.")
        
    coverage_bars = [{"topic": t, "count": c} for t, c in topic_counts.items()]
    severity_bars = [{"severity": s.capitalize(), "count": c} for s, c in severity_counts.items() if c > 0]
    
    return {
        "obligations": all_obligations,
        "findings": findings,
        "policyHealth": policy_health,
        "executive": {
          "summary": f"Audit complete. Policies show a calculated risk index of {score}/100. Corrective actions required.",
          "score": score,
          "recommendations": rec_list
        },
        "timeline": timeline,
        "coverage": coverage_bars,
        "severityDistribution": severity_bars,
        "classifier": "HuggingFace BAAI/bge-small-en-v1.5 + FAISS Vector Classifier",
        "comparisons": comparisons
    }


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."}
    )

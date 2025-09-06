"""
FastAPI Application

Main FastAPI application for KiroLinter DevOps orchestration platform.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .routers import workflows, pipelines, deployments, analytics
from .middleware.logging import LoggingMiddleware
from ..devops.orchestration.workflow_engine import WorkflowEngine
from ..devops.orchestration.pipeline_manager import PipelineManager
from ..devops.orchestration.quality_gates import QualityGateSystem

logger = logging.getLogger(__name__)

# Global instances
workflow_engine = None
pipeline_manager = None
quality_gate_system = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting KiroLinter DevOps API")
    
    # Initialize core components
    global workflow_engine, pipeline_manager, quality_gate_system
    workflow_engine = WorkflowEngine()
    pipeline_manager = PipelineManager()
    quality_gate_system = QualityGateSystem()
    
    # Store in app state
    app.state.workflow_engine = workflow_engine
    app.state.pipeline_manager = pipeline_manager
    app.state.quality_gate_system = quality_gate_system
    
    logger.info("KiroLinter DevOps API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down KiroLinter DevOps API")
    
    # Cleanup resources
    if pipeline_manager:
        # Stop any background tasks
        for task in pipeline_manager.sync_tasks.values():
            task.cancel()
    
    logger.info("KiroLinter DevOps API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="KiroLinter DevOps API",
    description="Advanced DevOps orchestration platform with intelligent workflow management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(
    workflows.router,
    prefix="/api/v1/workflows",
    tags=["workflows"]
)

app.include_router(
    pipelines.router,
    prefix="/api/v1/pipelines",
    tags=["pipelines"]
)

app.include_router(
    deployments.router,
    prefix="/api/v1/deployments",
    tags=["deployments"]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["analytics"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "KiroLinter DevOps API",
        "version": "1.0.0",
        "description": "Advanced DevOps orchestration platform",
        "status": "operational",
        "endpoints": {
            "workflows": "/api/v1/workflows",
            "pipelines": "/api/v1/pipelines",
            "deployments": "/api/v1/deployments",
            "analytics": "/api/v1/analytics",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check core components
        components_status = {
            "workflow_engine": "healthy" if workflow_engine else "unavailable",
            "pipeline_manager": "healthy" if pipeline_manager else "unavailable",
            "quality_gate_system": "healthy" if quality_gate_system else "unavailable"
        }
        
        # Overall health
        overall_health = "healthy" if all(
            status == "healthy" for status in components_status.values()
        ) else "degraded"
        
        return {
            "status": overall_health,
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "components": components_status,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    try:
        # Basic metrics - would integrate with actual metrics collection
        return {
            "active_workflows": len(workflow_engine.active_executions) if workflow_engine else 0,
            "pipeline_integrations": len(pipeline_manager.integrations) if pipeline_manager else 0,
            "api_version": "1.0.0",
            "uptime_seconds": 0  # Would calculate actual uptime
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")
"""
Pipeline API Router

REST API endpoints for CI/CD pipeline integration management.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List
import logging

from ...devops.models.pipeline import PipelineIntegrationAPI, PlatformType
from ...devops.orchestration.pipeline_manager import PipelineManager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_pipeline_manager(request: Request) -> PipelineManager:
    """Dependency to get pipeline manager from app state"""
    return request.app.state.pipeline_manager


@router.get("/platforms", response_model=List[str])
async def get_supported_platforms(
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Get list of supported CI/CD platforms"""
    try:
        platforms = manager.get_supported_platforms()
        return [platform.value for platform in platforms]
    except Exception as e:
        logger.error(f"Failed to get supported platforms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations", response_model=dict)
async def create_integration(
    integration: PipelineIntegrationAPI,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Create a new pipeline integration"""
    try:
        # Convert API model to internal model
        from ...devops.models.pipeline import PipelineIntegration
        
        internal_integration = PipelineIntegration(
            id=integration.id,
            name=integration.name,
            platform=integration.platform,
            configuration=integration.configuration,
            status=integration.status,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            metadata=integration.metadata
        )
        
        success = await manager.add_integration(internal_integration)
        
        if success:
            return {
                "id": integration.id,
                "name": integration.name,
                "platform": integration.platform,
                "status": "created",
                "message": "Pipeline integration created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create integration")
            
    except Exception as e:
        logger.error(f"Failed to create pipeline integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations", response_model=List[dict])
async def list_integrations(
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """List all pipeline integrations"""
    try:
        integrations = manager.get_integrations()
        
        return [
            {
                "id": integration.id,
                "name": integration.name,
                "platform": integration.platform,
                "status": integration.status,
                "created_at": integration.created_at.isoformat(),
                "last_sync": integration.last_sync.isoformat() if integration.last_sync else None,
                "error_message": integration.error_message
            }
            for integration in integrations
        ]
    except Exception as e:
        logger.error(f"Failed to list integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/{integration_id}", response_model=dict)
async def get_integration(
    integration_id: str,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Get pipeline integration by ID"""
    try:
        integration = manager.integrations.get(integration_id)
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return {
            "id": integration.id,
            "name": integration.name,
            "platform": integration.platform,
            "status": integration.status,
            "configuration": {
                "repository_url": integration.configuration.repository_url,
                "branch_patterns": integration.configuration.branch_patterns,
                "trigger_events": integration.configuration.trigger_events
            },
            "created_at": integration.created_at.isoformat(),
            "updated_at": integration.updated_at.isoformat(),
            "last_sync": integration.last_sync.isoformat() if integration.last_sync else None,
            "error_message": integration.error_message,
            "metadata": integration.metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/{integration_id}/health", response_model=dict)
async def get_integration_health(
    integration_id: str,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Get health status of a pipeline integration"""
    try:
        health = await manager.get_integration_health(integration_id)
        return health
    except Exception as e:
        logger.error(f"Failed to get health for integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/{integration_id}/pipelines/{pipeline_id}/trigger", response_model=dict)
async def trigger_pipeline(
    integration_id: str,
    pipeline_id: str,
    parameters: dict = None,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Trigger a pipeline execution"""
    try:
        run_id = await manager.trigger_pipeline(integration_id, pipeline_id, parameters)
        
        if run_id:
            return {
                "integration_id": integration_id,
                "pipeline_id": pipeline_id,
                "run_id": run_id,
                "status": "triggered",
                "message": "Pipeline execution triggered successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to trigger pipeline")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/{integration_id}/pipelines/{pipeline_id}/runs/{run_id}", response_model=dict)
async def get_pipeline_run_status(
    integration_id: str,
    pipeline_id: str,
    run_id: str,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Get pipeline run status"""
    try:
        run_status = await manager.get_pipeline_status(integration_id, pipeline_id, run_id)
        
        if run_status:
            return {
                "id": run_status.id,
                "pipeline_id": run_status.pipeline_id,
                "run_number": run_status.run_number,
                "status": run_status.status,
                "branch": run_status.branch,
                "commit_sha": run_status.commit_sha,
                "commit_message": run_status.commit_message,
                "triggered_by": run_status.triggered_by,
                "started_at": run_status.started_at.isoformat(),
                "completed_at": run_status.completed_at.isoformat() if run_status.completed_at else None,
                "duration_minutes": run_status.duration_minutes,
                "is_success": run_status.is_success,
                "is_running": run_status.is_running,
                "error_message": run_status.error_message
            }
        else:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline run status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/{integration_id}/pipelines/{pipeline_id}/optimize", response_model=dict)
async def optimize_pipeline(
    integration_id: str,
    pipeline_id: str,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Get pipeline optimization recommendations"""
    try:
        optimization = await manager.optimize_pipeline(integration_id, pipeline_id)
        return optimization
    except Exception as e:
        logger.error(f"Failed to optimize pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/sync", response_model=dict)
async def sync_all_integrations(
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Sync all pipeline integrations"""
    try:
        sync_results = await manager.sync_all_integrations()
        return sync_results
    except Exception as e:
        logger.error(f"Failed to sync integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/integrations/{integration_id}", response_model=dict)
async def delete_integration(
    integration_id: str,
    manager: PipelineManager = Depends(get_pipeline_manager)
):
    """Delete a pipeline integration"""
    try:
        success = await manager.remove_integration(integration_id)
        
        if success:
            return {
                "id": integration_id,
                "status": "deleted",
                "message": "Pipeline integration deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Integration not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""
Analytics Processing Worker

Background worker for processing analytics data, generating insights,
and creating reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from .celery_app import app

logger = logging.getLogger(__name__)


class AnalyticsProcessor:
    """Processes analytics data and generates insights"""
    
    def __init__(self):
        self.metrics_cache = {}
        self.trend_analyzers = {}
    
    def process_workflow_metrics(self, workflow_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process workflow execution metrics"""
        if not workflow_data:
            return {"error": "No workflow data provided"}
        
        # Calculate basic metrics
        total_workflows = len(workflow_data)
        successful_workflows = sum(1 for w in workflow_data if w.get('status') == 'completed')
        failed_workflows = total_workflows - successful_workflows
        
        # Calculate average duration
        durations = [w.get('duration_seconds', 0) for w in workflow_data if w.get('duration_seconds')]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Calculate success rate
        success_rate = (successful_workflows / total_workflows) * 100 if total_workflows > 0 else 0
        
        # Analyze failure patterns
        failure_types = {}
        for workflow in workflow_data:
            if workflow.get('status') != 'completed' and workflow.get('error_message'):
                error_msg = workflow['error_message'].lower()
                if 'timeout' in error_msg:
                    failure_types['timeout'] = failure_types.get('timeout', 0) + 1
                elif 'resource' in error_msg:
                    failure_types['resource'] = failure_types.get('resource', 0) + 1
                elif 'network' in error_msg:
                    failure_types['network'] = failure_types.get('network', 0) + 1
                else:
                    failure_types['other'] = failure_types.get('other', 0) + 1
        
        return {
            "total_workflows": total_workflows,
            "successful_workflows": successful_workflows,
            "failed_workflows": failed_workflows,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "failure_patterns": failure_types,
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def analyze_trends(self, metrics_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in workflow metrics"""
        if len(metrics_history) < 2:
            return {"error": "Insufficient data for trend analysis"}
        
        # Simple trend analysis
        recent_metrics = metrics_history[-5:]  # Last 5 data points
        older_metrics = metrics_history[-10:-5] if len(metrics_history) >= 10 else metrics_history[:-5]
        
        if not older_metrics:
            return {"error": "Insufficient historical data"}
        
        # Calculate trend indicators
        recent_success_rate = sum(m.get('success_rate', 0) for m in recent_metrics) / len(recent_metrics)
        older_success_rate = sum(m.get('success_rate', 0) for m in older_metrics) / len(older_metrics)
        
        success_rate_trend = recent_success_rate - older_success_rate
        
        recent_avg_duration = sum(m.get('average_duration_seconds', 0) for m in recent_metrics) / len(recent_metrics)
        older_avg_duration = sum(m.get('average_duration_seconds', 0) for m in older_metrics) / len(older_metrics)
        
        duration_trend = recent_avg_duration - older_avg_duration
        
        # Determine overall trend
        trend_direction = "stable"
        if abs(success_rate_trend) > 5:  # 5% threshold
            if success_rate_trend > 0:
                trend_direction = "improving" if duration_trend <= 0 else "mixed"
            else:
                trend_direction = "declining"
        
        return {
            "success_rate_trend": success_rate_trend,
            "duration_trend_seconds": duration_trend,
            "trend_direction": trend_direction,
            "confidence_score": min(len(metrics_history) / 10.0, 1.0),  # More data = higher confidence
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def generate_insights(self, analytics_data: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from analytics data"""
        insights = []
        
        success_rate = analytics_data.get('success_rate', 0)
        avg_duration = analytics_data.get('average_duration_seconds', 0)
        failure_patterns = analytics_data.get('failure_patterns', {})
        
        # Success rate insights
        if success_rate < 80:
            insights.append(f"Success rate is low at {success_rate:.1f}%. Consider reviewing failure patterns.")
        elif success_rate > 95:
            insights.append(f"Excellent success rate of {success_rate:.1f}%. Current processes are working well.")
        
        # Duration insights
        if avg_duration > 300:  # 5 minutes
            insights.append(f"Average workflow duration is high at {avg_duration:.1f}s. Consider optimization.")
        elif avg_duration < 30:
            insights.append(f"Very fast execution time of {avg_duration:.1f}s. Workflows are well optimized.")
        
        # Failure pattern insights
        if failure_patterns:
            most_common_failure = max(failure_patterns.items(), key=lambda x: x[1])
            insights.append(f"Most common failure type is '{most_common_failure[0]}' ({most_common_failure[1]} occurrences).")
        
        return insights


@app.task(bind=True, name='analytics_worker.process_workflow_analytics')
def process_workflow_analytics(self, workflow_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process workflow analytics data
    
    Args:
        workflow_data: List of workflow execution data
        
    Returns:
        Dict containing processed analytics
    """
    try:
        processor = AnalyticsProcessor()
        result = processor.process_workflow_metrics(workflow_data)
        
        # Generate insights
        insights = processor.generate_insights(result)
        result['insights'] = insights
        
        logger.info(f"Processed analytics for {len(workflow_data)} workflows")
        return result
        
    except Exception as e:
        logger.error(f"Analytics processing failed: {e}")
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'timestamp': datetime.utcnow().isoformat()}
        )
        
        return {"error": str(e)}


@app.task(bind=True, name='analytics_worker.process_analytics_batch')
def process_analytics_batch(self) -> Dict[str, Any]:
    """
    Process a batch of analytics data (periodic task)
    
    Returns:
        Dict containing batch processing results
    """
    try:
        logger.info("Processing analytics batch")
        
        # Mock implementation with realistic processing
        batch_size = 100
        processed_count = 0
        
        # Simulate processing batches
        for batch_num in range(3):  # Process 3 batches
            batch_processed = min(batch_size, 25 + batch_num * 10)  # Variable batch sizes
            processed_count += batch_processed
            
            logger.debug(f"Processed batch {batch_num + 1}: {batch_processed} items")
        
        return {
            "success": True,
            "processed_items": processed_count,
            "batches_processed": 3,
            "processing_duration_seconds": 15.5,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch analytics processing failed: {e}")
        
        return {
            "success": False,
            "error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }


@app.task(bind=True, name='analytics_worker.generate_report')
def generate_report(self, report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate analytics report
    
    Args:
        report_type: Type of report to generate
        parameters: Report parameters
        
    Returns:
        Dict containing report data
    """
    try:
        logger.info(f"Generating {report_type} report")
        
        # Mock report generation with detailed data
        if report_type == "workflow_summary":
            return {
                "report_type": report_type,
                "summary": {
                    "total_workflows": 150,
                    "success_rate": 92.5,
                    "average_duration": 45.2,
                    "total_stages": 450,
                    "most_common_stage_type": "analysis"
                },
                "trends": {
                    "success_rate_change": "+2.3%",
                    "duration_change": "-5.1s",
                    "volume_change": "+15%"
                },
                "generated_at": datetime.utcnow().isoformat(),
                "parameters": parameters
            }
        elif report_type == "performance_trends":
            return {
                "report_type": report_type,
                "performance": {
                    "trend_direction": "improving",
                    "performance_score": 87.3,
                    "bottlenecks": ["security_scan", "build"],
                    "optimization_opportunities": 3
                },
                "recommendations": [
                    "Consider parallel execution for independent stages",
                    "Optimize security scan configuration",
                    "Cache build dependencies"
                ],
                "generated_at": datetime.utcnow().isoformat(),
                "parameters": parameters
            }
        else:
            return {
                "error": f"Unknown report type: {report_type}",
                "available_types": ["workflow_summary", "performance_trends"]
            }
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        
        return {
            "error": str(e),
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat()
        }


@app.task(bind=True, name='analytics_worker.cleanup_old_data')
def cleanup_old_data(self, dry_run: bool = False, table_names: list = None):
    """Clean up old data according to retention policies"""
    try:
        logger.info(f"Starting data cleanup task ({'dry run' if dry_run else 'live'})")
        
        # Import and run cleanup
        import asyncio
        from kirolinter.database.migrations.data_retention import cleanup_old_data as run_cleanup
        
        # Run async cleanup in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(run_cleanup(dry_run=dry_run, table_names=table_names))
            
            logger.info(f"Data cleanup completed: {result['total_deleted']} records processed")
            return result
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Data cleanup task failed: {e}")
        raise self.retry(countdown=300, max_retries=2)  # Retry after 5 minutes


@app.task(bind=True, name='analytics_worker.generate_data_statistics')
def generate_data_statistics(self):
    """Generate data statistics report"""
    try:
        logger.info("Generating data statistics report")
        
        import asyncio
        from kirolinter.database.migrations.data_retention import get_data_statistics
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            statistics = loop.run_until_complete(get_data_statistics())
            
            # Store statistics in cache for dashboard access
            from kirolinter.cache.redis_client import cache_set
            loop.run_until_complete(
                cache_set('data_statistics', statistics, ttl_seconds=3600)  # Cache for 1 hour
            )
            
            logger.info("Data statistics report generated successfully")
            return statistics
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Data statistics generation failed: {e}")
        raise self.retry(countdown=300, max_retries=2)


@app.task(bind=True, name='analytics_worker.get_cleanup_recommendations')
def get_cleanup_recommendations(self):
    """Get data cleanup recommendations"""
    try:
        logger.info("Generating cleanup recommendations")
        
        import asyncio
        from kirolinter.database.migrations.data_retention import get_cleanup_recommendations
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recommendations = loop.run_until_complete(get_cleanup_recommendations())
            
            # Cache recommendations
            from kirolinter.cache.redis_client import cache_set
            loop.run_until_complete(
                cache_set('cleanup_recommendations', recommendations, ttl_seconds=1800)  # Cache for 30 minutes
            )
            
            logger.info("Cleanup recommendations generated successfully")
            return recommendations
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Cleanup recommendations generation failed: {e}")
        raise self.retry(countdown=300, max_retries=2)
#!/usr/bin/env python3
"""
FastAPI wrapper for CrewAI projects - FIXED VERSION
This allows n8n and other services to interact with CrewAI via HTTP
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid
import asyncio
import os
import sys
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CrewAI API Service",
    description="Official CrewAI project with REST API wrapper for n8n integration",
    version="1.0.0"
)

# Add CORS middleware - FIXES browser "failed to fetch" errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your n8n domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job tracking storage (use Redis in production)
jobs = {}

# Models for API requests
class CrewInput(BaseModel):
    """Input parameters for CrewAI crew execution"""
    inputs: Dict[str, Any] = {}

class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

def load_crew_module():
    """Dynamically load the CrewAI crew from the project"""
    try:
        # Add the marketing_posts source path to Python path
        sys.path.insert(0, '/app/marketing_strategy/src')
        
        # Import the crew module directly
        from marketing_posts.crew import MarketingPostsCrew
        return MarketingPostsCrew
        
    except Exception as e:
        logger.error(f"Failed to load crew module: {e}")
        raise ImportError(f"Could not load CrewAI crew module: {e}")

def get_crew_class():
    """Get the CrewAI crew class from the loaded module"""
    return load_crew_module()

async def run_crew_job(job_id: str, inputs: Dict[str, Any]):
    """Run CrewAI crew asynchronously"""
    try:
        jobs[job_id]["status"] = "running"
        logger.info(f"Starting job {job_id} with inputs: {inputs}")
        
        # Get the crew class and instantiate it
        crew_class = get_crew_class()
        crew_instance = crew_class()
        
        # Get the crew and run it
        crew = crew_instance.crew()
        result = crew.kickoff(inputs=inputs)
        
        # Store the result - Convert CrewAI result to string
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = str(result)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": "CrewAI API Service is running",
        "version": "1.0.0",
        "description": "Official CrewAI project with REST API wrapper for n8n integration",
        "endpoints": {
            "health": "/health",
            "crew_info": "/crew/info", 
            "run_async": "/crew/run",
            "run_sync": "/crew/run-sync",
            "job_status": "/crew/status/{job_id}",
            "job_result": "/crew/result/{job_id}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try to load the crew to ensure everything is working
        crew_class = get_crew_class()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "crew_loaded": True,
            "crew_class": crew_class.__name__
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "crew_loaded": False
        }

@app.post("/crew/run")
async def run_crew(crew_input: CrewInput, background_tasks: BackgroundTasks):
    """Start a CrewAI job and return job ID for tracking"""
    job_id = str(uuid.uuid4())
    
    # Initialize job tracking
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(run_crew_job, job_id, crew_input.inputs)
    
    logger.info(f"Started job {job_id}")
    return {"job_id": job_id, "status": "started"}

@app.get("/crew/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a CrewAI job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(**jobs[job_id])

@app.get("/crew/result/{job_id}")
async def get_job_result(job_id: str):
    """Get the result of a completed CrewAI job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] == "pending" or job["status"] == "running":
        raise HTTPException(status_code=202, detail="Job still running")
    
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job['error']}")
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job["result"],
        "completed_at": job["completed_at"]
    }

@app.get("/crew/jobs")
async def list_jobs():
    """List all jobs"""
    return {"jobs": list(jobs.values())}

@app.delete("/crew/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from tracking"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del jobs[job_id]
    return {"message": "Job deleted successfully"}

@app.get("/crew/info")
async def crew_info():
    """Get information about the loaded CrewAI crew - FIXED VERSION"""
    try:
        crew_class = get_crew_class()
        crew_instance = crew_class()
        
        # Get crew object
        crew = crew_instance.crew()
        
        # Extract agent and task information safely
        agents_info = []
        if hasattr(crew, 'agents') and crew.agents:
            agents_info = [{"role": agent.role, "goal": agent.goal} for agent in crew.agents]
        
        tasks_count = 0
        if hasattr(crew, 'tasks') and crew.tasks:
            tasks_count = len(crew.tasks)
        
        return {
            "crew_class": crew_class.__name__,
            "agents": agents_info,
            "tasks_count": tasks_count,
            "available": True,
            "process": str(crew.process) if hasattr(crew, 'process') else "unknown"
        }
    except Exception as e:
        logger.error(f"Error getting crew info: {e}")
        return {
            "error": str(e),
            "available": False
        }

# Example endpoint showing how to call the crew directly (synchronous)
@app.post("/crew/run-sync")
async def run_crew_sync(crew_input: CrewInput):
    """Run CrewAI crew synchronously (for testing/small jobs)"""
    try:
        crew_class = get_crew_class()
        crew_instance = crew_class()
        crew = crew_instance.crew()
        
        result = crew.kickoff(inputs=crew_input.inputs)
        
        return {
            "status": "completed",
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Sync crew execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Crew execution failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Check if crew can be loaded on startup
    try:
        crew_class = get_crew_class()
        logger.info(f"Successfully loaded CrewAI crew: {crew_class.__name__}")
    except Exception as e:
        logger.error(f"Failed to load CrewAI crew on startup: {e}")
        sys.exit(1)
    
    # Start the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )

import docker
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Resilience-Alpha Remediation Engine", version="1.0.0")

# Initialize Docker client using the mounted socket
try:
    client = docker.from_env()
except Exception as e:
    print(f"Failed to connect to Docker socket: {e}")
    client = None

class RemediationRequest(BaseModel):
    reason: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "docker_connected": client is not None}

@app.post("/remediate", status_code=status.HTTP_200_OK)
def trigger_remediation(payload: RemediationRequest):
    """
    Autonomous recovery handler: Restarts the payment microservice 
    and clears bottlenecks without human intervention.
    """
    print(f"🚨 Remediation triggered! Reason: {payload.reason}")
    
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not available on remediation service")

    try:
        # Find and restart the target container autonomously
        target_container_name = "resilience_payment"
        container = client.containers.get(target_container_name)
        
        print(f"Restarting container '{target_container_name}' to restore service...")
        container.restart(timeout=5)
        
        return {
            "status": "SUCCESS",
            "action_taken": f"Restarted container {target_container_name}",
            "reason": payload.reason,
            "message": "System successfully recovered autonomously."
        }
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container {target_container_name} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remediation failed: {str(e)}")
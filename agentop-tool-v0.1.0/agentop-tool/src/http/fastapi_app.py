from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import os
import inspect
from typing import Callable, Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=os.environ.get("TOOL_NAME", "Tool API"),
    description="AGENTOP API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API is not available")
    return api_key

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

registered_functions: List[Dict[str, Any]] = []

def api_function():
    def decorator(func: Callable):
        func_name = func.__name__
        sig = inspect.signature(func)
        docstring = inspect.getdoc(func) or ""

        # Lưu metadata
        registered_functions.append({
            "name": func_name,
            "func": func,
            "signature": sig,
            "description": docstring
        })

        async def endpoint(request: Request, f=func, s=sig):
            try:
                data = await request.json()
                logger.info(f"[{f.__name__}] Input: {data}")
                bound = s.bind(**data)
                bound.apply_defaults()
                result = f(*bound.args, **bound.kwargs)
                return {"result": result}
            except Exception as e:
                logger.error(f"Error in function {f.__name__}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        app.add_api_route(
            f"/{func_name}",
            endpoint=endpoint,
            methods=["POST"],
            dependencies=[Depends(verify_api_key)],
            name=func_name
        )

        return func
    return decorator

@app.get("/functions", tags=["Meta"])
async def list_registered_functions():
    results = []
    for item in registered_functions:
        params = {
            k: str(v.annotation) if v.annotation != inspect.Parameter.empty else "Any"
            for k, v in item["signature"].parameters.items()
        }
        results.append({
            "name": item["name"],
            "description": item["description"],
            "parameters": params
        })
    return {"functions": results}


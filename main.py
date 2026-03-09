
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting RepoIR Backend on {host}:{port}")
    uvicorn.run("app_server:app", host=host, port=port, reload=False)

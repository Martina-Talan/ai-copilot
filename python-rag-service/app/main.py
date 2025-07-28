from fastapi import FastAPI
from app.routes.vector import router as vector_router
from app.routes.pdf import router as pdf_router
from app.routes.chat import router as chat_router

app = FastAPI()

app.include_router(vector_router, prefix="/api", tags=["Embeddings"])

app.include_router(pdf_router, prefix="/api", tags=["PDF"])

app.include_router(chat_router, prefix="/api", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
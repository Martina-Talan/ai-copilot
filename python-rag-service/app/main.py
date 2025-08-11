from fastapi import FastAPI
from app.routes.vector import router as vector_router
from app.routes.pdf import router as pdf_router
from app.routes.chat import router as chat_router
from app.services.ws_handler import ws_router
import warnings
from fastapi.middleware.cors import CORSMiddleware  
from transformers.utils.logging import set_verbosity_error

warnings.filterwarnings("ignore", 
    message="`encoder_attention_mask` is deprecated")
set_verbosity_error()

app = FastAPI()

app.include_router(vector_router, prefix="/api", tags=["Embeddings"])

app.include_router(pdf_router, prefix="/api", tags=["PDF"])

app.include_router(chat_router, prefix="/api", tags=["Chat"])

app.include_router(ws_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
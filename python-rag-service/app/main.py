from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from transformers.utils.logging import set_verbosity_error

import os, logging, warnings
from app.routes.vector import router as vector_router
from app.routes.pdf import router as pdf_router
from app.routes.chat import router as chat_router
from app.ws.ws_handler import ws_router

# Load env + logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.info("ENV resolved → PORT=%s, FAISS_STORE_PATH=%s, EMBEDDING_MODEL=%s, OPENAI_CHAT_MODEL=%s",
         os.getenv("PORT"),
         os.getenv("FAISS_STORE_PATH"),
         os.getenv("EMBEDDING_MODEL"),
         os.getenv("OPENAI_CHAT_MODEL"))

# Hide warnings
warnings.filterwarnings("ignore", message="`encoder_attention_mask` is deprecated")
set_verbosity_error()

# FastAPI app
app = FastAPI()

# Routers
for r in [vector_router, pdf_router, chat_router]:
    app.include_router(r, prefix="/api")
app.include_router(ws_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
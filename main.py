from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import users
from api import teams
from auth.oauth2 import router as auth_router

app = FastAPI()

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluye los routers
app.include_router(auth_router, prefix="/auth")
app.include_router(users.router, prefix="/api/users")
app.include_router(teams.router, prefix="/api/teams")

@app.get("/")
def read_root():
    return {"message": "Backend ITSA Avisos"}

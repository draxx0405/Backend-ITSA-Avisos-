from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from backend.services.graph_service import graph_service


router = APIRouter()

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="/auth/login",
    tokenUrl="/auth/token"
)

# ✅ Obtener todos los usuarios del tenant
@router.get("/all")
async def get_all_users(token: str = Depends(oauth2_scheme)):
    try:
        result = await graph_service.get_all_users(token)
        return result
    except Exception as e:
        # Logea el error con más detalles
        print(f"Error al obtener usuarios: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener usuarios")
from msal import ConfidentialClientApplication
import os
import httpx

# Configuración desde variables de entorno
CLIENT_ID = os.getenv("MSAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("MSAL_CLIENT_SECRET")
TENANT_ID = os.getenv("MSAL_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Scopes necesarios
SCOPES = [
"Chat.Create",
"Chat.ReadWrite",
"ChatMessage.Send",
"Files.ReadWrite",
"User.Read",
"User.ReadBasic.All"]

app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY
)


def get_auth_url():
    """Genera URL de login con Microsoft"""
    return app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state="some_random_state"  # IMPORTANTE: Genera un valor único en producción
    )

def get_token_from_code(code: str):
    """Intercambia el código por tokens"""
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    if "error" in result:
        raise Exception(result.get("error_description", "Error al obtener tokens"))
    
    return result

async def get_user_info(access_token: str):
    """
    Obtiene información del usuario desde Microsoft Graph API
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Primero obtiene el perfil básico
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            response.raise_for_status()
            user_data = response.json()
            
            # Si necesitas más información, puedes hacer otras llamadas
            # Por ejemplo, para obtener la foto o detalles adicionales
            return {
                "name": user_data.get("displayName", ""),
                "email": user_data.get("mail") or user_data.get("userPrincipalName", ""),
                # Agrega más campos según necesites
            }
            
    except Exception as e:
        print(f"Error obteniendo info de usuario: {str(e)}")
        return {}
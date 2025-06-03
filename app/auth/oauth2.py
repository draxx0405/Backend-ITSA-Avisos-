from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.auth.msal_auth import get_auth_url, get_token_from_code,get_user_info
from fastapi.responses import HTMLResponse
import httpx
router = APIRouter()

@router.get("/login")
async def login():
    """Inicia el flujo de autenticación redirigiendo a Microsoft"""
    auth_url = get_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback", response_class=HTMLResponse)
async def auth_callback(code: str, state: str = None, session_state: str = None):
    if not code:
        return """
        <html>
          <script>
            window.opener.postMessage({
              type: 'AUTH_ERROR',
              error: 'Código de autorización faltante'
            }, 'https://frontend-itsa-avisos-production.up.railway.app/');
            window.close();
          </script>
        </html>
        """
    
    try:
        # 1. Obtener token usando el código
        token_result = get_token_from_code(code)
        print(token_result)
        
        # 2. Obtener información del usuario
        user_info = await get_user_info(token_result['access_token'])
        print(user_info)
        # 3. Enviar datos al frontend y cerrar ventana
        return f"""
        <html>
          <style>
            body {{ 
              font-family: Arial; 
              text-align: center;
              padding: 20px;
            }}
          </style>
          <body>
            <h2>Autenticación exitosa</h2>
            <p>Puedes cerrar esta ventana</p>
            <script>
              window.opener.postMessage({{
                type: 'MSAL_AUTH',
                token: '{token_result["access_token"]}',
                user: {{
                  name: '{user_info.get("name", "")}',
                  email: '{user_info.get("email", "")}'
                }}
              }}, 'https://frontend-itsa-avisos-production.up.railway.app/');
              window.close();
            </script>
          </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
          <script>
            window.opener.postMessage({{
              type: 'AUTH_ERROR',
              error: '{str(e)}'
            }}, 'https://frontend-itsa-avisos-production.up.railway.app/');
            window.close();
          </script>
        </html>
        """


@router.get("/logout")   
async def revoke_refresh_token(refresh_token: str, client_id: str, client_secret: str):
    async with httpx.AsyncClient() as client:
        data = {
            "token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "token_type_hint": "refresh_token"
        }
        response = await client.post("https://login.microsoftonline.com/common/oauth2/v2.0/logout", data=data)
        if response.status_code == 200:
            return {"message": "Sesión cerrada correctamente"}
        else:
            raise Exception(f"No se pudo cerrar sesión: {response.text}")



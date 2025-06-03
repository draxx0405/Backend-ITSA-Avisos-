from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from backend.services.graph_service import graph_service
from pydantic import BaseModel
import base64
import httpx
from typing import List

router = APIRouter()

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="/auth/login",
    tokenUrl="/auth/token"
)

class MessageRequest(BaseModel):
    id: str
    message: str

@router.post("/send-message")
async def send_message(
    data: MessageRequest,
    token: str = Depends(oauth2_scheme),
):
    try:
        result = await graph_service.send_message_to_user(token, data.id, data.message)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to send message",
                "internal_error": str(e),
                "user_id": data.id,
                "message_content": data.message[:100] + "..." if len(data.message) > 100 else data.message
            }
        )



class MessageWithAttachmentRequest(BaseModel):
    id: List[str]          # Lista de user_ids
    message: str
    file: str              # archivo en base64
    file_name: str         # nombre original del archivo

@router.post("/send-message-with-attachment")
async def send_message_with_attachment(
    data: MessageWithAttachmentRequest,
    token: str = Depends(oauth2_scheme),
):
    try:
        file_bytes = base64.b64decode(data.file)

        results = await graph_service.send_message_with_attachment(
            token=token,
            user_ids=data.id,
            content=data.message,
            file_bytes=file_bytes,
            file_name=data.file_name
        )

        return {
            "status": "success",
            "results": results
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Graph API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
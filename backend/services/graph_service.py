import httpx
import re
import json
import uuid

class GraphService:
    
    async def get_all_users(self, token: str):
        usuarios_filtrados = []
        next_link = "https://graph.microsoft.com/v1.0/users?$select=id,displayName,mail,userPrincipalName"

        def determinar_carrera(matricula: str) -> str:
            letra = matricula[4].upper()
            return {
                "S": "Ingenieria en Sistemas Computacionales",
                "D": "Ingenieria industrial",
                "G": "Ingenieria en Gestion Empresarial",
                "T": "Ingenieria en Electromecanica",
                "K": "Ingenieria en Mecatronica"
            }.get(letra, "No encontrada")
        
        async with httpx.AsyncClient() as client:
            while next_link:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(next_link, headers=headers)
                response.raise_for_status()
                data = response.json()

                for user in data.get("value", []):
                    mail = user.get("mail")
                            
                    if not mail:
                        continue
                    
                    matricula = mail.split("@")[0]
                    if re.match(r"^[0-9]{4}[SDGTK][0-9]{5}$", matricula):                        
                        usuarios_filtrados.append({
                            "idUser": user["id"],
                            "displayName": user["displayName"],
                            "mail": mail,
                            "matricula": matricula,
                            "Carrera": determinar_carrera(matricula)
                        })

                next_link = data.get("@odata.nextLink")

        # Ordenar por displayName
        usuarios_filtrados.sort(key=lambda x: x["displayName"])

        # Asignar índices después de ordenar
        for index, usuario in enumerate(usuarios_filtrados, start=1):
            usuario["id"] = index

        return {"usuarios": usuarios_filtrados}

    async def send_message_to_user(self, token: str, user_id: str, content: str):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # 1. Obtener el ID del usuario autenticado (quien envía el mensaje)
            async with httpx.AsyncClient() as client:
                me_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                )
                me_response.raise_for_status()
                me_data = me_response.json()
                sender_id = me_data["id"]
            
            # 2. Crear chat con ambos miembros
            chat_body = {
                "chatType": "oneOnOne",
                "members": [
                    {
                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                        "roles": ["owner"],
                        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{sender_id}"
                    },
                    {
                        "@odata.type": "#microsoft.graph.aadUserConversationMember",
                        "roles": ["owner"],
                        "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}"
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                chat_response = await client.post(
                    "https://graph.microsoft.com/v1.0/chats",
                    headers=headers,
                    json=chat_body
                )

                chat_response.raise_for_status()
                chat_data = chat_response.json()
                chat_id = chat_data["id"]
         
                # 3. Enviar mensaje
                message_body = {
                    "body": {
                        "contentType": "text",
                        "content": content
                    }
                }

                message_response = await client.post(
                    f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages",
                    headers=headers,
                    json=message_body
                )
                message_response.raise_for_status()
                return message_response.json()

        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP Error {e.response.status_code}: {e.response.text}"
            raise Exception(error_detail)
        except Exception as e:
            raise



    async def send_message_with_attachment(self, token: str, user_ids: list, content: str, file_bytes: bytes, file_name: str):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                # 1. Obtener el ID del usuario autenticado
                me_response = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
                me_response.raise_for_status()
                sender_id = me_response.json()["id"]

                # 2. Crear sesión de subida para OneDrive
                upload_session = await client.post(
                    f"https://graph.microsoft.com/v1.0/me/drive/root:/{file_name}:/createUploadSession",
                    headers=headers,
                    json={"item": {"@microsoft.graph.conflictBehavior": "rename"}}
                )
                upload_session.raise_for_status()
                upload_url = upload_session.json()["uploadUrl"]

                # 3. Subir el archivo
                upload_headers = {
                    "Content-Length": str(len(file_bytes)),
                    "Content-Range": f"bytes 0-{len(file_bytes) - 1}/{len(file_bytes)}"
                }

                upload_response = await client.put(upload_url, headers=upload_headers, content=file_bytes)
                upload_response.raise_for_status()
                drive_item = upload_response.json()
                file_id = drive_item["id"]
                file_web_url = drive_item["webUrl"]

                # 4. Obtener vista previa (thumbnail)
                file_thumbnail_url = None
                thumbnail_response = await client.get(
                    f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/thumbnails",
                    headers=headers
                )

                if thumbnail_response.status_code == 200:
                    thumbnails = thumbnail_response.json().get("value", [])
                    if thumbnails:
                        file_thumbnail_url = thumbnails[0].get("medium", {}).get("url")

                # 5. Enviar mensaje a cada usuario individual
                results = []

                for user_id in user_ids:
                    # Crear chat 1 a 1
                    chat_body = {
                        "chatType": "oneOnOne",
                        "members": [
                            {
                                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                                "roles": ["owner"],
                                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{sender_id}"
                            },
                            {
                                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                                "roles": ["owner"],
                                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}"
                            }
                        ]
                    }

                    chat_response = await client.post("https://graph.microsoft.com/v1.0/chats", headers=headers, json=chat_body)
                    chat_response.raise_for_status()
                    chat_id = chat_response.json()["id"]

                    # Construir tarjeta Adaptive Card
                    adaptive_card = {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"📄 {file_name}",
                                "weight": "bolder",
                                "size": "medium",
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": "Aquí tienes el archivo que solicitaste. Puedes abrirlo o verlo en vista previa si está disponible.",
                                "isSubtle": True,
                                "wrap": True
                            },
                            {
                                "type": "Image",
                                "url": file_thumbnail_url,
                                "size": "medium",
                                "altText": "Vista previa del archivo"
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "📂 Abrir archivo",
                                "url": file_web_url
                            }
                        ],
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.2"
                    }

                    # ✅ Mensaje con attachment y campo "id"
                    message_body = {
                        "body": {
                            "contentType": "html",
                            "content": f"{content}<br><attachment id=\"{file_id}\"></attachment>"  # Usar el ID del archivo subido
                        },
                        "attachments": [
                            {
                                "id": f"{file_id}",  # Asegúrate de que el ID del adjunto sea el correcto
                                "contentType": "application/vnd.microsoft.card.adaptive",
                                "content": json.dumps(adaptive_card)
                            }
                        ]
                    }
                    message_response = await client.post(
                        f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages",
                        headers=headers,
                        json=message_body
                    )
                    message_response.raise_for_status()

                    results.append({
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "message_id": message_response.json().get("id"),
                        "status": "success"
                    })
                return results

        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP Error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            print(e)
            raise



        
    # Función para obtener la miniatura del archivo después de cargarlo a OneDrive
    async def get_file_thumbnail(self, token: str, file_id: str):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
        try:
            async with httpx.AsyncClient() as client:
                # Obtener la miniatura del archivo
                thumbnail_response = await client.get(
                    f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/thumbnails/0/medium",
                    headers=headers
                )
    
                # Verificar si la miniatura está disponible
                thumbnail_response.raise_for_status()
                thumbnail_data = thumbnail_response.json()
                
                # Obtener URL de la miniatura
                thumbnail_url = thumbnail_data.get("link", {}).get("href", None)
    
                if thumbnail_url:
                    return thumbnail_url
                else:
                    # Si no hay miniatura, puedes usar un ícono genérico
                    return "https://example.com/icono_pdf.png"  # Ícono genérico para archivos PDF
    
        except httpx.HTTPStatusError as e:
            raise Exception(f"Error al obtener la miniatura: {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise


graph_service = GraphService()
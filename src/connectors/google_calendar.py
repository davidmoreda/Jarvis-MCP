"""
Conector Google Calendar — leer y crear eventos
Requiere OAuth2 credentials de Google Cloud Console.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.connectors.base import BaseConnector

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "credentials/google_token.json")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")


class GoogleCalendarConnector(BaseConnector):

    def _get_service(self):
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "calendar_list_events",
                    "description": "Lista los próximos eventos del calendario de Google.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days_ahead": {
                                "type": "integer",
                                "description": "Cuántos días hacia adelante buscar (default: 7)",
                                "default": 7
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Número máximo de eventos (default: 10)",
                                "default": 10
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_create_event",
                    "description": "Crea un nuevo evento en Google Calendar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título del evento"},
                            "start": {"type": "string", "description": "Inicio en formato ISO 8601 (ej: 2025-03-10T10:00:00)"},
                            "end": {"type": "string", "description": "Fin en formato ISO 8601"},
                            "description": {"type": "string", "description": "Descripción opcional"},
                            "location": {"type": "string", "description": "Lugar opcional"}
                        },
                        "required": ["title", "start", "end"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        service = self._get_service()

        if tool_name == "calendar_list_events":
            now = datetime.utcnow().isoformat() + "Z"
            days = args.get("days_ahead", 7)
            until = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=until,
                maxResults=args.get("max_results", 10),
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])
            return [
                {
                    "title": e.get("summary", "Sin título"),
                    "start": e["start"].get("dateTime", e["start"].get("date")),
                    "end": e["end"].get("dateTime", e["end"].get("date")),
                    "location": e.get("location", ""),
                    "description": e.get("description", ""),
                }
                for e in events
            ]

        elif tool_name == "calendar_create_event":
            event = {
                "summary": args["title"],
                "start": {"dateTime": args["start"], "timeZone": "Europe/Madrid"},
                "end": {"dateTime": args["end"], "timeZone": "Europe/Madrid"},
            }
            if "description" in args:
                event["description"] = args["description"]
            if "location" in args:
                event["location"] = args["location"]
            result = service.events().insert(calendarId="primary", body=event).execute()
            return {"created": True, "event_id": result.get("id"), "link": result.get("htmlLink")}

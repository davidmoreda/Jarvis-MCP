"""
Conector Gmail — leer y enviar emails via Gmail API
"""
import os
import base64
from email.mime.text import MIMEText
from typing import List, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.connectors.base import BaseConnector

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "credentials/google_token.json")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")


class GmailConnector(BaseConnector):

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
        return build("gmail", "v1", credentials=creds)

    def get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "gmail_list_inbox",
                    "description": "Lista los emails recientes del inbox.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "default": 10},
                            "query": {"type": "string", "description": "Filtro de búsqueda Gmail (ej: 'is:unread from:boss@company.com')"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_send",
                    "description": "Envía un email.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                            "cc": {"type": "string"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            }
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        service = self._get_service()

        if tool_name == "gmail_list_inbox":
            q = args.get("query", "in:inbox")
            results = service.users().messages().list(
                userId="me", q=q, maxResults=args.get("max_results", 10)
            ).execute()
            messages = results.get("messages", [])
            emails = []
            for m in messages[:5]:  # Limitar detalles a 5 para no saturar
                detail = service.users().messages().get(userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]).execute()
                headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
                emails.append({
                    "id": m["id"],
                    "from": headers.get("From"),
                    "subject": headers.get("Subject"),
                    "date": headers.get("Date"),
                    "snippet": detail.get("snippet", "")
                })
            return emails

        elif tool_name == "gmail_send":
            msg = MIMEText(args["body"])
            msg["to"] = args["to"]
            msg["subject"] = args["subject"]
            if args.get("cc"):
                msg["cc"] = args["cc"]
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return {"sent": True, "message_id": result.get("id")}

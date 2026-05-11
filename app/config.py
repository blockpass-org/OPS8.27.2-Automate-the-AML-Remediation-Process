import os
from google.cloud import secretmanager
from dotenv import load_dotenv

load_dotenv()

def get_config(key, default=None):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{key}/versions/latest"
        try:
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception:
            pass
    return os.getenv(key, default)

# Primary Service
BLOCKPASS_API_KEY = get_config("BLOCKPASS_API_KEY")
BLOCKPASS_CLIENT_ID = get_config("BLOCKPASS_CLIENT_ID")

# Supplemental Service
SUPP_API_KEY = get_config("BLOCKPASS_SUPPLEMENTAL_API_KEY")
SUPP_CLIENT_ID = get_config("BLOCKPASS_SUPPLEMENTAL_CLIENT_ID")

SHEET_ID = get_config("SHEET_ID")
GMAIL_USER = get_config("GMAIL_USER")
STAKEHOLDER_EMAIL = get_config("STAKEHOLDER_EMAIL")

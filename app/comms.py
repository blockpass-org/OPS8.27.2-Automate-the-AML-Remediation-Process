import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from app.config import GMAIL_USER, STAKEHOLDER_EMAIL

def get_gmail_service():
    return build('gmail', 'v1')

def draft_investor_email(investor_email, notes):
    """Creates a draft email for an investor."""
    service = get_gmail_service()
    
    message = EmailMessage()
    message.set_content(f"Dear Investor,\n\nWe require further details for your KYC remediation: {notes}\n\nPlease provide these at your earliest convenience.\n\nBest regards,\nCompliance Team")
    message['To'] = investor_email
    message['From'] = GMAIL_USER
    message['Subject'] = "Action Required: KYC Remediation Details Needed"

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'message': {'raw': encoded_message}}
    
    service.users().drafts().create(userId="me", body=create_message).execute()

def send_stakeholder_report(summary_text):
    """Sends a summary report to stakeholders."""
    service = get_gmail_service()
    
    message = EmailMessage()
    message.set_content(summary_text)
    message['To'] = STAKEHOLDER_EMAIL
    message['From'] = GMAIL_USER
    message['Subject'] = "KYC Automation Run Summary Report"

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    send_message = {'raw': encoded_message}
    
    service.users().messages().send(userId="me", body=send_message).execute()

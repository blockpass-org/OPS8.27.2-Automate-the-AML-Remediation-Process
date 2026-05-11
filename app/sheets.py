import datetime
from googleapiclient.discovery import build
from app.config import SHEET_ID

def get_service():
    return build('sheets', 'v4')

def write_to_sheet(data_list):
    if not data_list: return
        
    service = get_service()
    sheet = service.spreadsheets()
    
    # 1. Reset/Ensure sheets exist
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
    
    if "MainData" not in existing_sheets or "AuditLog" not in existing_sheets:
        requests = []
        if "MainData" not in existing_sheets: requests.append({"addSheet": {"properties": {"title": "MainData"}}})
        if "AuditLog" not in existing_sheets: requests.append({"addSheet": {"properties": {"title": "AuditLog"}}})
        service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": requests}).execute()

    # 2. Dynamic Header Discovery
    # We collect all unique keys from all records to build the master header list
    all_keys = set()
    for d in data_list:
        all_keys.update(d.keys())
    
    # Define mandatory compliance columns at the start
    headers = [
        "Record ID", "Ref ID", "Suggested Decision", "Notes", "Status", "AML Status", 
        "AML Hits Summary", "AML Hit URLs", "Last Updated"
    ]
    # Add all other extracted fields
    exclude = ["recordId", "refId", "decision", "notes", "status", "aml_status", "aml_hits_summary", "aml_hit_urls", "raw_data", "aml_hits_raw"]
    other_fields = sorted([k for k in all_keys if k not in exclude and k not in headers])
    headers.extend(other_fields)

    # Reset MainData with new headers (Clear and Overwrite)
    sheet.values().clear(spreadsheetId=SHEET_ID, range="MainData!A:Z").execute()
    sheet.values().update(spreadsheetId=SHEET_ID, range="MainData!A1", valueInputOption="RAW", body={"values": [headers]}).execute()

    # 3. Map records to headers
    rows = []
    now = datetime.datetime.now().isoformat()
    for data in data_list:
        row = []
        for h in headers:
            if h == "Record ID": row.append(data.get("recordId"))
            elif h == "Ref ID": row.append(data.get("refId"))
            elif h == "Suggested Decision": row.append(data.get("decision"))
            elif h == "Notes": row.append(data.get("notes"))
            elif h == "Status": row.append(data.get("status"))
            elif h == "AML Status": row.append(data.get("aml_status"))
            elif h == "AML Hits Summary": row.append(data.get("aml_hits_summary"))
            elif h == "AML Hit URLs": row.append(data.get("aml_hit_urls"))
            elif h == "Last Updated": row.append(now)
            else: row.append(data.get(h, ""))
        rows.append(row)

    # 4. Batch update
    print(f"DEBUG: Appending {len(rows)} rows to MainData...")
    for i in range(0, len(rows), 1000):
        batch = rows[i:i+1000]
        sheet.values().append(spreadsheetId=SHEET_ID, range="MainData!A1", valueInputOption="RAW", body={"values": batch}).execute()

    # Log the reset in AuditLog
    log_reset(len(rows))

def log_reset(count):
    service = get_service()
    sheet = service.spreadsheets()
    timestamp = datetime.datetime.now().isoformat()
    log_row = [timestamp, "SYSTEM", "RESET_SPREADSHEET", f"Reset MainData with {count} records and updated schema", "SYSTEM_AUTO"]
    sheet.values().append(spreadsheetId=SHEET_ID, range="AuditLog!A1", valueInputOption="RAW", body={"values": [log_row]}).execute()

import datetime
from googleapiclient.discovery import build
from app.config import SHEET_ID

def get_service():
    return build('sheets', 'v4')

def write_to_sheet(data_list):
    if not data_list: return
    service = get_service()
    sheet = service.spreadsheets()
    
    # 1. Discover all keys
    all_keys = set()
    for d in data_list:
        all_keys.update(d.keys())
    
    # 2. Define High-Visibility Headers
    headers = [
        "Record ID", "Ref ID", "Suggested Decision", "Notes", 
        "Primary Status", "p_aml_status", "p_aml_hits_summary",
        "Supp Status", "s_aml_status", "s_aml_hits_summary", 
        "Last Updated"
    ]
    
    # Add prefixed identity fields (names, emails, etc)
    exclude = ["recordId", "refId", "decision", "notes", "primary_status", "supp_status", "p_aml_status", "s_aml_status", "p_aml_hits_summary", "s_aml_hits_summary", "raw_data", "aml_hits_raw", "aml_status", "aml_hits_summary", "aml_hit_urls", "p_aml_hits_raw", "s_aml_hits_raw", "p_aml_hit_urls", "s_aml_hit_urls"]
    other_fields = sorted([k for k in all_keys if k not in exclude and k not in headers])
    headers.extend(other_fields)

    # 3. Reset MainData
    sheet.values().clear(spreadsheetId=SHEET_ID, range="MainData!A:ZZ").execute()
    sheet.values().update(spreadsheetId=SHEET_ID, range="MainData!A1", valueInputOption="RAW", body={"values": [headers]}).execute()

    # 4. Map records
    rows = []
    now = datetime.datetime.now().isoformat()
    for data in data_list:
        row = []
        for h in headers:
            if h == "Record ID": row.append(data.get("recordId"))
            elif h == "Ref ID": row.append(data.get("refId"))
            elif h == "Suggested Decision": row.append(data.get("decision"))
            elif h == "Notes": row.append(data.get("notes"))
            elif h == "Primary Status": row.append(data.get("primary_status"))
            elif h == "Supp Status": row.append(data.get("supp_status"))
            elif h == "Last Updated": row.append(now)
            else: row.append(data.get(h, ""))
        rows.append(row)

    print(f"DEBUG: Resetting ledger with {len(rows)} records. Headers: {len(headers)}")
    sheet.values().append(spreadsheetId=SHEET_ID, range="MainData!A1", valueInputOption="RAW", body={"values": rows}).execute()

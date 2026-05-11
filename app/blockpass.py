import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import BLOCKPASS_API_KEY, BLOCKPASS_CLIENT_ID

def get_candidates():
    """Fetches candidates using pagination, handling 429s."""
    all_records = []
    limit = 100
    skip = 0
    
    while True:
        url = f"https://kyc.blockpass.org/kyc/1.0/connect/{BLOCKPASS_CLIENT_ID}/applicants?limit={limit}&skip={skip}"
        headers = {"Authorization": BLOCKPASS_API_KEY}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                wait = int(response.json().get("extra", {}).get("retryAfter", 30))
                time.sleep(wait)
                continue
                
            response.raise_for_status()
            res_data = response.json()
            data = res_data.get("data", {})
            records = data.get("records", [])
            
            if not records:
                break
                
            all_records.extend(records)
            skip += limit
            if skip >= 20000: break
            time.sleep(0.5)
        except Exception as e:
            print(f"DEBUG: Error in pagination: {e}")
            break
            
    return all_records

def get_candidate_data(record_id):
    url = f"https://kyc.blockpass.org/kyc/1.0/connect/{BLOCKPASS_CLIENT_ID}/recordId/{record_id}"
    headers = {"Authorization": BLOCKPASS_API_KEY}
    
    for i in range(3):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                wait = int(response.json().get("extra", {}).get("retryAfter", 10))
                time.sleep(wait + 1)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as e:
            time.sleep(1)
    return None

def flatten_identities(identities):
    """Flattens the identities object into a simple dict."""
    flat = {}
    for key, obj in identities.items():
        if isinstance(obj, dict) and "value" in obj:
            val = obj["value"]
            # Handle nested objects like address
            if isinstance(val, dict):
                for subkey, subval in val.items():
                    flat[f"{key}_{subkey}"] = subval
            else:
                flat[key] = val
    return flat

def extract_aml_data(certs):
    """Extracts detailed AML hits from certificates."""
    aml_cert = certs.get("aml_risk", {})
    status = aml_cert.get("status", "N/A")
    hits = aml_cert.get("hits", [])
    
    hit_summaries = []
    hit_urls = []
    for hit in hits:
        summary = f"[{hit.get('matchType')}] {hit.get('name')} (Source: {hit.get('source')}, Details: {hit.get('details')})"
        hit_summaries.append(summary)
        if hit.get("url"):
            hit_urls.append(hit.get("url"))
            
    return {
        "aml_status": status,
        "aml_hits_raw": str(hits),
        "aml_hits_summary": "; ".join(hit_summaries),
        "aml_hit_urls": "; ".join(hit_urls)
    }

def process_candidate(candidate):
    record_id = candidate.get("recordId")
    try:
        raw_res = get_candidate_data(record_id)
        if not raw_res: return None
        
        data = raw_res.get("data", {})
        identities = data.get("identities", {})
        certs = data.get("certificates", {})
        
        flat_ids = flatten_identities(identities)
        aml_data = extract_aml_data(certs)
        
        full_record = {
            "recordId": record_id,
            "refId": candidate.get("refId"),
            "blockPassId": candidate.get("blockPassID", candidate.get("blockPassId")),
            "status": candidate.get("status"),
            "isArchived": data.get("isArchived"),
            **flat_ids,
            **aml_data,
            "raw_data": raw_res
        }
        return full_record
    except Exception as e:
        print(f"DEBUG: Error processing {record_id}: {e}")
        return None

def extract_us_investors():
    """Extracts ALL data points for ALL applicants."""
    all_candidates = get_candidates()
    applicants = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_candidate, c) for c in all_candidates]
        for future in as_completed(futures):
            res = future.result()
            if res:
                applicants.append(res)
                if len(applicants) % 100 == 0:
                    print(f"DEBUG: Processed {len(applicants)} applicants...")
            
    return applicants

import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import BLOCKPASS_API_KEY, BLOCKPASS_CLIENT_ID, SUPP_API_KEY, SUPP_CLIENT_ID

def get_candidates(api_key, client_id):
    """Fetches candidates using pagination for a specific service."""
    all_records = []
    limit = 100
    skip = 0
    while True:
        url = f"https://kyc.blockpass.org/kyc/1.0/connect/{client_id}/applicants?limit={limit}&skip={skip}"
        headers = {"Authorization": api_key}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                wait = int(response.json().get("extra", {}).get("retryAfter", 30))
                time.sleep(wait)
                continue
            response.raise_for_status()
            res_data = response.json()
            records = res_data.get("data", {}).get("records", [])
            if not records: break
            all_records.extend(records)
            skip += limit
            if skip >= 20000: break
            time.sleep(0.5)
        except Exception as e:
            print(f"DEBUG: Error in pagination for {client_id}: {e}")
            break
    return all_records

def get_record_by_refid(api_key, client_id, ref_id):
    """Fetches record data using refId lookup."""
    url = f"https://kyc.blockpass.org/kyc/1.0/connect/{client_id}/applicant/{ref_id}"
    headers = {"Authorization": api_key}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            time.sleep(10)
            return get_record_by_refid(api_key, client_id, ref_id)
        if response.status_code == 404: return None
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

def get_candidate_data(api_key, client_id, record_id):
    url = f"https://kyc.blockpass.org/kyc/1.0/connect/{client_id}/recordId/{record_id}"
    headers = {"Authorization": api_key}
    for i in range(3):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                wait = int(response.json().get("extra", {}).get("retryAfter", 10))
                time.sleep(wait + 1)
                continue
            response.raise_for_status()
            return response.json()
        except Exception:
            time.sleep(1)
    return None

def flatten_identities(identities):
    flat = {}
    for key, obj in identities.items():
        if isinstance(obj, dict) and "value" in obj:
            val = obj["value"]
            if isinstance(val, dict):
                for subkey, subval in val.items():
                    flat[f"{key}_{subkey}"] = subval
            else:
                flat[key] = val
    return flat

def extract_aml_data(certs):
    aml_cert = certs.get("aml_risk", {})
    status = aml_cert.get("status", "N/A")
    hits = aml_cert.get("hits", [])
    hit_summaries = []
    hit_urls = []
    for hit in hits:
        summary = f"[{hit.get('matchType')}] {hit.get('name')} (Source: {hit.get('source')})"
        hit_summaries.append(summary)
        if hit.get("url"): hit_urls.append(hit.get("url"))
    return {
        "aml_status": status,
        "aml_hits_raw": str(hits),
        "aml_hits_summary": "; ".join(hit_summaries),
        "aml_hit_urls": "; ".join(hit_urls)
    }

def process_record(api_key, client_id, record_id, existing_data=None):
    raw_res = get_candidate_data(api_key, client_id, record_id)
    if not raw_res: return existing_data
    
    data = raw_res.get("data", {})
    identities = data.get("identities", {})
    certs = data.get("certificates", {})
    
    flat_ids = flatten_identities(identities)
    aml_data = extract_aml_data(certs)
    
    merged = existing_data.copy() if existing_data else {}
    # Prioritize non-empty values
    for k, v in {**flat_ids, **aml_data}.items():
        if v and v != "N/A" and v != "Unknown":
            merged[k] = v
            
    merged.update({
        "recordId": record_id,
        "status": data.get("status", merged.get("status")),
        "isArchived": data.get("isArchived", merged.get("isArchived")),
        "aml_hits_raw": str(merged.get("aml_hits_raw", "[]"))
    })
    return merged

def get_all_applicants_full():
    """Main extraction: Primary + Supplemental merge."""
    primary_records = get_candidates(BLOCKPASS_API_KEY, BLOCKPASS_CLIENT_ID)
    print(f"DEBUG: Found {len(primary_records)} records in primary service.")
    
    applicants = []
    def worker(c):
        ref_id = c.get("refId")
        # 1. Process Primary
        p_data = process_record(BLOCKPASS_API_KEY, BLOCKPASS_CLIENT_ID, c.get("recordId"))
        # 2. Supplement from new service using refId
        if ref_id and SUPP_API_KEY and SUPP_CLIENT_ID:
            supp_res = get_record_by_refid(SUPP_API_KEY, SUPP_CLIENT_ID, ref_id)
            if supp_res:
                supp_record_id = supp_res.get("data", {}).get("recordId")
                if supp_record_id:
                    p_data = process_record(SUPP_API_KEY, SUPP_CLIENT_ID, supp_record_id, existing_data=p_data)
        
        p_data["refId"] = ref_id
        return p_data

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, c) for c in primary_records]
        for future in as_completed(futures):
            res = future.result()
            if res: applicants.append(res)
            
    return applicants

def extract_us_investors():
    # Kept for compatibility with main.py trigger
    return get_all_applicants_full()

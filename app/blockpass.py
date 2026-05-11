import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import BLOCKPASS_API_KEY, BLOCKPASS_CLIENT_ID, SUPP_API_KEY, SUPP_CLIENT_ID

def get_candidates(api_key, client_id):
    all_records = []
    limit = 100
    skip = 0
    while True:
        url = f"https://kyc.blockpass.org/kyc/1.0/connect/{client_id}/applicants?limit={limit}&skip={skip}"
        headers = {"Authorization": api_key}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                time.sleep(30)
                continue
            response.raise_for_status()
            res_data = response.json()
            records = res_data.get("data", {}).get("records", [])
            if not records: break
            all_records.extend(records)
            skip += limit
            if skip >= 2000: break
            time.sleep(1)
        except Exception as e:
            print(f"DEBUG: Error in pagination for {client_id}: {e}")
            break
    return all_records

def get_record_by_refid(api_key, client_id, ref_id):
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
    except Exception as e:
        print(f"DEBUG: RefID lookup failed for {ref_id}: {e}")
        return None

def flatten_identities(identities, prefix=""):
    flat = {}
    for key, obj in identities.items():
        if isinstance(obj, dict) and "value" in obj:
            val = obj["value"]
            if isinstance(val, dict):
                for subkey, subval in val.items():
                    flat[f"{prefix}{key}_{subkey}"] = subval
            else:
                flat[f"{prefix}{key}"] = val
    return flat

def extract_aml_data(certs, prefix=""):
    aml_cert = certs.get("aml_risk", {})
    status = aml_cert.get("status", "CLEAR")
    hits = aml_cert.get("hits", [])
    
    hit_summaries = []
    hit_urls = []
    for hit in hits:
        summary = f"[{hit.get('matchType')}] {hit.get('name')} ({hit.get('source')})"
        hit_summaries.append(summary)
        if hit.get("url"): hit_urls.append(hit.get("url"))
        
    return {
        f"{prefix}aml_status": status,
        f"{prefix}aml_hits_raw": str(hits),
        f"{prefix}aml_hits_summary": "; ".join(hit_summaries),
        f"{prefix}aml_hit_urls": "; ".join(hit_urls)
    }

def get_all_applicants_full():
    print(f"DEBUG: Starting extraction. Primary: {BLOCKPASS_CLIENT_ID}, Supp: {SUPP_CLIENT_ID}")
    
    # 1. Fetch candidate summaries from both services independently
    primary_summaries = get_candidates(BLOCKPASS_API_KEY, BLOCKPASS_CLIENT_ID)
    supp_summaries = get_candidates(SUPP_API_KEY, SUPP_CLIENT_ID)
    
    print(f"DEBUG: Found {len(primary_summaries)} primary and {len(supp_summaries)} supplemental summaries.")
    
    # 2. Map unique refIds to available source info (Primary/Supplemental)
    entity_map = {} # refId -> { "p_summary": ..., "s_summary": ... }
    
    for s in primary_summaries:
        rid = s.get("refId")
        if rid:
            entity_map.setdefault(rid, {})["p_summary"] = s
            
    for s in supp_summaries:
        rid = s.get("refId")
        if rid:
            entity_map.setdefault(rid, {})["s_summary"] = s

    applicants = []

    def worker(ref_id, sources):
        p_summary = sources.get("p_summary")
        s_summary = sources.get("s_summary")
        
        record = {"refId": ref_id}
        
        # 3. Pull Full Primary Data if available
        if p_summary:
            p_record_id = p_summary.get("recordId")
            url = f"https://kyc.blockpass.org/kyc/1.0/connect/{BLOCKPASS_CLIENT_ID}/recordId/{p_record_id}"
            try:
                p_res = requests.get(url, headers={"Authorization": BLOCKPASS_API_KEY}).json()
                p_data = p_res.get("data", {})
                record.update({
                    "recordId": p_record_id,
                    "primary_status": p_data.get("status"),
                    **flatten_identities(p_data.get("identities", {}), "p_"),
                    **extract_aml_data(p_data.get("certificates", {}), "p_")
                })
            except Exception as e:
                print(f"DEBUG: Failed to fetch primary full data for {ref_id}: {e}")

        # 4. Pull Full Supplemental Data if available
        if s_summary:
            s_record_id = s_summary.get("recordId")
            url = f"https://kyc.blockpass.org/kyc/1.0/connect/{SUPP_CLIENT_ID}/recordId/{s_record_id}"
            try:
                s_res = requests.get(url, headers={"Authorization": SUPP_API_KEY}).json()
                s_data = s_res.get("data", {})
                record.update({
                    "supp_status": s_data.get("status"),
                    **flatten_identities(s_data.get("identities", {}), "s_"),
                    **extract_aml_data(s_data.get("certificates", {}), "s_")
                })
                # Prioritize supplemental for compliance logic compatibility
                record["aml_hits_raw"] = record.get("s_aml_hits_raw", record.get("p_aml_hits_raw"))
                record["aml_status"] = record.get("s_aml_status", record.get("p_aml_status"))
            except Exception as e:
                print(f"DEBUG: Failed to fetch supplemental full data for {ref_id}: {e}")
        
        # 5. Final Fallbacks for consistent analysis processing
        if "aml_status" not in record:
            record["aml_status"] = record.get("p_aml_status", "CLEAR")
            record["aml_hits_raw"] = record.get("p_aml_hits_raw", "[]")
            
        return record

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, rid, sources) for rid, sources in entity_map.items()]
        for future in as_completed(futures):
            res = future.result()
            if res: applicants.append(res)
            
    return applicants

def extract_us_investors():
    return get_all_applicants_full()

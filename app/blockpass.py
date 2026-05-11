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
    import json
    # Blockpass AML data is stored in 'member_check_cert' as a JSON string
    member_check_raw = certs.get("member_check_cert")
    
    status = "CLEAR"
    hits = []
    
    if member_check_raw:
        try:
            member_check = json.loads(member_check_raw)
            claim = member_check.get("Claim", {})
            custom_fields = claim.get("_customFields", {})
            report = custom_fields.get("report", {})
            
            matched_number = report.get("matchedNumber", 0)
            if matched_number > 0:
                status = "HIT"
                # Map Blockpass 'matchedEntities' to a consistent hit structure for analysis
                entities = report.get("matchedEntities", [])
                for entity in entities:
                    hits.append({
                        "name": f"{entity.get('firstName', '')} {entity.get('middleName', '')} {entity.get('lastName', '')}".replace("  ", " ").strip(),
                        "score": entity.get("matchRate", 100),
                        "dob": entity.get("dob", ""),
                        "category": entity.get("category", "N/A"),
                        "source": entity.get("primaryLocation", "N/A"),
                        "match_type": entity.get("matchedFields", "N/A")
                    })
            else:
                # reviewBody often contains "Name not found in Sanctions and PEP list"
                if "not found" in claim.get("reviewBody", "").lower():
                    status = "CLEAR"
                else:
                    status = "REVIEW_REQUIRED"
                    
        except Exception as e:
            print(f"DEBUG: Error parsing member_check_cert: {e}")
            status = "ERROR"

    hit_summaries = []
    for hit in hits:
        summary = f"[{hit.get('category')}] {hit.get('name')} (Score: {hit.get('score')}%)"
        hit_summaries.append(summary)
        
    return {
        f"{prefix}aml_status": status,
        f"{prefix}aml_hits_raw": json.dumps(hits),
        f"{prefix}aml_hits_summary": "; ".join(hit_summaries),
        f"{prefix}aml_hit_urls": "" # URLs are not directly provided in this cert structure
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

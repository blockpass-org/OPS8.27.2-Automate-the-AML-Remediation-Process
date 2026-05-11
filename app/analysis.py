import os
import re

def load_aml_policy():
    """Loads the AML policy from the markdown file."""
    policy_path = "AML_Discount_Workflow.md"
    if not os.path.exists(policy_path):
        return "Policy file not found."
    with open(policy_path, "r") as f:
        return f.read()

def analyze_record(investor_data):
    """
    Evaluates KYC records based on the AML_Discount_Workflow.md policy.
    """
    import json
    # 1. Hit Quality Logic (Step 2 in Policy)
    aml_hits_raw = investor_data.get("aml_hits_raw", "[]")
    try:
        aml_hits = json.loads(aml_hits_raw)
    except:
        aml_hits = []

    aml_status = investor_data.get("aml_status", "CLEAR")
    if not aml_hits or aml_status == "CLEAR":
        return "False Positive", "No AML hits found. Status is CLEAR."

    name = investor_data.get("name", investor_data.get("given_name", "N/A"))
    dob = investor_data.get("dob", "N/A")
    country = investor_data.get("address_country", investor_data.get("country", "N/A"))

    decisions = []
    notes = []

    for hit in aml_hits:
        hit_name = hit.get("name", "")
        # Identify "Weak Aliases" (missing DOB or Address in hit data)
        # In real logic, we'd check hit details for missing secondary identifiers.
        is_weak_alias = not hit.get("dob") and not hit.get("address")
        
        # 2.2 Auto-Discount Fuzzy Match Logic
        # (Assuming 'score' < 100 indicates fuzzy match)
        score = hit.get("score", 100)
        if is_weak_alias and score < 100:
            decisions.append("False Positive")
            notes.append(f"Weak Alias & Fuzzy Match ({score}%). Auto-discounted per Policy 2.2.")
            continue

        # 2.3 Escalation Exact Match Rule
        if is_weak_alias and score == 100:
            decisions.append("Further Details Required")
            notes.append(f"Weak Alias with 100% Name Match. Pushing to Enrichment/RFI per Policy 2.3.")
            continue

        # 4.1 Systematic Discount (identifiers mismatch)
        if dob != "N/A" and hit.get("dob") and dob != hit.get("dob"):
            decisions.append("False Positive")
            notes.append(f"DOB Mismatch ({dob} vs {hit.get('dob')}). Systematic discount per Policy 4.1.")
            continue

        # Default Escalation for Standard Hits (Policy 2.4)
        decisions.append("Further Details Required")
        notes.append(f"Standard Hit identified. Triggering Automated RFI per Policy 4.3.")

    # Final Resolution Consolidation
    if "Further Details Required" in decisions:
        return "Further Details Required", "; ".join(notes)
    if "True Positive" in decisions:
        return "True Positive", "; ".join(notes)
    
    return "False Positive", "; ".join(notes)

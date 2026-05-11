# Blockpass KYC Automation & AML Remediation System

This system automates the extraction, analysis, and management of Know Your Customer (KYC) data from multiple Blockpass services. It integrates a policy-baked analysis engine to resolve AML alerts according to standardized compliance workflows.

## 🚀 System Architecture

The solution is built as a cloud-native Python application deployed on **Google Cloud Run**, triggered by **Cloud Scheduler**.

1.  **Multi-Service Data Extraction**: 
    *   **Primary Source**: Extracts applicants from the target KYC campaign (e.g., Appeal Service).
    *   **Supplemental Source**: Uses `refId` lookups to pull missing data points from a secondary Blockpass service, merging them into a comprehensive user profile.
2.  **Policy-Baked Analysis**: Evaluates AML hits against the `AML_Discount_Workflow.md` SOP, automatically identifying "Weak Aliases" and suggesting resolutions.
3.  **Automated Ledger**: Maintains a definitive record of all users and decisions in a **Google Sheet** with dynamic header discovery.
4.  **Audit Integrity**: Logs every system action and data change in a dedicated `AuditLog` sheet for compliance transparency.

## 📁 Project Structure

*   `app/main.py`: The central orchestrator and HTTP entry point.
*   `app/blockpass.py`: Logic for paginated extraction and cross-service data merging.
*   `app/analysis.py`: The AML logic engine implementing the cascading workflow.
*   `app/sheets.py`: Optimized batch management for Google Sheets.
*   `AML_Discount_Workflow.md`: The formal Compliance SOP used by the analysis engine.
*   `deploy.sh`: Infrastructure-as-Code script for GCP deployment.

## 🛠️ Setup & Deployment

### 1. Secret Configuration
The system retrieves sensitive API keys from **Google Cloud Secret Manager**. Ensure the following secrets are populated:
*   `BLOCKPASS_API_KEY`: Key for the primary service.
*   `BLOCKPASS_CLIENT_ID`: ID for the primary service (e.g., `kyc_appeal_service_b6213`).
*   `BLOCKPASS_SUPPLEMENTAL_API_KEY`: Key for the supplemental data source.
*   `BLOCKPASS_SUPPLEMENTAL_CLIENT_ID`: ID for the supplemental source (e.g., `0gblockpasskyc_975ed`).
*   `SHEET_ID`: The ID of your target Google Sheet.

### 2. CI/CD Workflow
The project uses a **GitHub-first workflow**. 
*   Pushing changes to the `main` branch automatically triggers a build and redeploy to Cloud Run.
*   GCP Cloud Build handles the container assembly via the included `Dockerfile`.

## 📜 AML Cascading Logic
The system's "False Positive Engine" follows these key steps:
1.  **Weak Alias Identification**: Hits missing secondary identifiers (DOB/Address).
2.  **Auto-Discounting**: Fuzzy name matches on weak aliases are automatically closed.
3.  **Escalation**: 100% name matches or standard AML hits trigger a "Further Details Required" status.
4.  **Systematic Discount**: Identifiers (like DOB) that clearly mismatch the CDD data result in an immediate False Positive resolution.

---
**Maintained by Compliance Engineering**

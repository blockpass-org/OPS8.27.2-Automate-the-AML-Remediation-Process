# Anti-Money Laundering (AML) Cascading Logic & Alert Resolution Policy

## 1. Objective and Scope
This document summarizes the Standard Operating Procedure (SOP) and business logic for processing AML alerts in a centralized ledger. It follows Wolfsberg Group standards for handling "Weak Aliases" and defines a strict, automated cascading workflow.

## 2. Step-by-Step Cascading Logic Table

| Step | Sub-Step | Action / Objective | Compliance / Operational Detail |
| :--- | :--- | :--- | :--- |
| **1. Data Review** | 1.1 Ledger Sourcing | Read User & Hit Data | Pull User CDD and AML Hit data (including source URLs) from the Google Sheet. |
| | 1.2 Integrity Check | Pre-flight Validation | Ensure all fields are populated before initiating the assessment phase. |
| **2. Hit Quality** | 2.1 Weak Alias ID | Classification | Identify hits missing secondary identifiers (DOB, Address) as "Weak Aliases". |
| | 2.2 Auto-Discount | Fuzzy Match Logic | Auto-discount if it's a Weak Alias AND only a partial/fuzzy name match. |
| | 2.3 Escalation | Exact Match Rule | If a Weak Alias is a 100% exact name match, push to Step 3 (Enrichment). |
| | 2.4 Standard Hit | Direct Comparison | If robust data exists, bypass Step 3 and go directly to Step 4. |
| **3. URL Enrichment** | 3.1 Source Extraction | Automated Browsing | Use automated tools to visit the source URLs provided in the AML hit. |
| | 3.2 Context Harvesting | Data Mining | Extract missing context (ages, locations, affiliations) from the webpage text. |
| | 3.3 Data Staging | Profile Update | Append extracted context to the Hit profile for final resolution. |
| **4. Resolution** | 4.1 FALSE_POSITIVE | Systematic Discount | Close alert if identifiers (DOB, Geography, Gender) clearly mismatch. |
| | 4.2 TRUE_POSITIVE | MLRO Escalation | Escalate to MLRO if enriched identifiers align or confirm a match. |
| | 4.3 AUTOMATED RFI | KYC Refresh Loop | Trigger automated "Routine KYC Refresh" form if enrichment fails; check context. |
| | 4.4 FINAL ESCALATION | Dead End RBD | Escalate to MLRO for a Risk-Based Decision if the RFI fails to clear risk. |
| | 4.5 TIMEOUT | Account Suspension | Automatically suspend the account if the RFI is not submitted within 7 days. |
| **5. Audit & Log** | 5.1 Mandatory Logging | Ledger Update | Write Status, Timestamp, and Rationale back to the specific row. |
| | 5.2 Immutability | Compliance Locking | Ensure resolved entries are locked to prevent post-facto alteration. |

## 3. Standardized RFI Payload
When the Automated RFI Loop (4.3) is triggered, the system requests the following structured data from the user to establish contextual risk:
*   Current Occupation & Employer Name
*   Primary Countries of Business/Operation
*   Source of Funds/Wealth
*   Nature of expected transactional activity

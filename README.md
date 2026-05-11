# Technical Specification: Blockpass KYC Automation & Analysis System

## 1. System Overview
The objective of this system is to automate the extraction of Know Your Customer (KYC) data from Blockpass, store it securely in a tamper-evident Google Sheet, perform automated True/False Positive analysis on the records, and trigger appropriate email communications to stakeholders and users.

## 2. Architecture & Tech Stack
* **Compute:** Google Cloud Run
* **Trigger/Automation:** Google Cloud Scheduler
* **External APIs:** Blockpass API, Google Sheets API, Google Workspace / Gmail API

## 3. Core Workflows & Requirements

### A. Data Extraction (Blockpass to GCP)
* The Cloud Run service authenticates with the Blockpass API.
* Queries different KYC services/campaigns within Blockpass.
* **Target Data:** Specifically extracts Investor details, isolating data for US users and capturing their Unique IDs.

### B. Data Storage & Integrity (The Google Sheet)
* **Definitive Record:** The Google Sheet serves as the single source of truth.
* **Immutability & Audit Logging:** The main data sheet must be locked to prevent manual overwriting. 
* **Change Log Mechanism:** Any necessary manual overrides or system updates must be recorded in an automated Audit Log capturing: Who made the change, What the change was (Old Value vs. New Value), and When it occurred.

### C. Automated KYC Analysis (The "False Positive" Engine)
* The script evaluates the extracted KYC records (e.g., sanction/PEP screening results).
* Writes a **"Suggested Decision"** directly into a dedicated column in the Google Sheet.
* **Decision Outcomes:**
    1. **Definitive Decision:** Marked clearly as a True Positive or False Positive.
    2. **Further Details Required:** Marked as needing more information.

### D. Action Generation & Communication
* **Notes & Email Drafting:** If the decision is "Further Details Required," the script populates a "Notes" column specifying exactly what additional details are needed.
* **Draft Generation:** The system automatically drafts an email requesting these specific details from the investor.
* **Stakeholder Reporting:** Compiles the run's results and emails a summary report to the European team ("Euro side").

## 4. Security & Compliance Considerations
* **PII Handling:** Strict IAM access controls for Google Cloud and Google Sheets to comply with data privacy regulations.
* **Secret Management:** API keys must be stored securely using Google Cloud Secret Manager.

from flask import Flask, request
import os
from app.blockpass import extract_us_investors
from app.analysis import analyze_record
from app.sheets import write_to_sheet
from app.comms import draft_investor_email, send_stakeholder_report

app = Flask(__name__)

@app.route("/", methods=["POST", "GET"])
def run_automation():
    try:
        # 1. Extract US Investors from Blockpass
        investors = extract_us_investors()
        
        # 2. Analyze records
        results = []
        summary = {
            "total": len(investors),
            "further_details": 0,
            "false_positives": 0,
            "true_positives": 0
        }
        
        for investor in investors:
            decision, notes = analyze_record(investor)
            investor['decision'] = decision
            investor['notes'] = notes
            results.append(investor)
            
            if decision == "Further Details Required":
                summary["further_details"] += 1
                # Gmail draft creation removed per user request
            elif decision == "False Positive":
                summary["false_positives"] += 1
            elif decision == "True Positive":
                summary["true_positives"] += 1
        
        # 3. Write to Google Sheets (with Audit Log)
        write_to_sheet(results)
        
        # 4. Send Summary Report to Stakeholders (Disabled per testing request)
        # report_text = f"KYC Automation Run Completed.\n\nTotal US Investors processed: {summary['total']}\n"
        # report_text += f"Further Details Required: {summary['further_details']}\n"
        # report_text += f"False Positives: {summary['false_positives']}\n"
        # report_text += f"True Positives: {summary['true_positives']}\n"
        
        # send_stakeholder_report(report_text)
        
        return {"status": "success", "summary": summary}, 200
        
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

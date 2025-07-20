import pandas as pd
import numpy as np
import re

# --- CONFIGURATION ---
# IMPORTANT: Replace this with the correct path to your CSV file.
csv_file_path = 'cleaned_zoho_tickets_final.csv' 
# --- END CONFIGURATION ---


def analyze_support_tickets(file_path):
    """
    Analyzes support ticket data from a CSV file to identify automation opportunities.

    Args:
        file_path (str): The path to the support ticket CSV file.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"---! ERROR !---")
        print(f"The file '{file_path}' was not found.")
        print("Please make sure the script is in the same directory as your CSV file and that the 'csv_file_path' variable is set correctly.")
        return

    # --- Data Cleaning and Preparation ---
    # Combine Subject and Description for semantic analysis
    df['text'] = df['Subject'].fillna('') + ' ' + df['Description'].fillna('')
    df['text'] = df['text'].str.lower()
    total_tickets = len(df)

    # --- Intent Classification ---
    def map_intent(text):
        if any(keyword in text for keyword in ['cancel', 'cancellation', 'unsubscribe', 'end my account', 'close my account']):
            return 'Membership Cancellation'
        if any(keyword in text for keyword in ['password', 'reset', 'forgot', 'login issue', 'can\'t log in']):
            return 'Password Reset / Login Issue'
        if any(keyword in text for keyword in ['refund', 'money back', 'reimburse']):
            return 'Refund Request'
        if any(keyword in text for keyword in ['billing', 'charge', 'invoice', 'overcharged', 'double charge']):
            return 'Billing Inquiry'
        if any(keyword in text for keyword in ['update card', 'new card', 'payment method', 'credit card update']):
            return 'Update Payment Method'
        if any(keyword in text for keyword in ['not working', 'error', 'issue', 'problem', 'bug']):
            return 'Technical Issue'
        if any(keyword in text for keyword in ['hours', 'open', 'close', 'location', 'address']):
            return 'Store Hours/Location Inquiry'
        if any(keyword in text for keyword in ['how to', 'question', 'inquiry', 'information']):
            return 'General Question'
        if any(keyword in text for keyword in ['upgrade', 'downgrade', 'change plan']):
            return 'Plan Change Request'
        if any(keyword in text for keyword in ['product', 'service', 'feature request']):
            return 'Product/Feature Request'
        return 'Other'

    df['Intent'] = df['text'].apply(map_intent)

    # --- Automation Category Classification ---
    df['AutomationCategory'] = 'Human-in-the-Loop' # Default category

    full_automation_intents = [
        'Password Reset / Login Issue', 'Store Hours/Location Inquiry', 
        'General Question', 'Billing Inquiry', 'Plan Change Request'
    ]
    agentic_workflow_intents = [
        'Membership Cancellation', 'Refund Request', 'Update Payment Method'
    ]

    df.loc[df['Intent'].isin(full_automation_intents), 'AutomationCategory'] = 'Full Automation'
    df.loc[df['Intent'].isin(agentic_workflow_intents), 'AutomationCategory'] = 'Agentic Workflow'
    
    # Override for high-sentiment or uncategorized tickets
    human_in_the_loop_keywords = 'angry|frustrated|disappointed|legal|lawsuit|complaint|escalate|manager|unresolved'
    human_in_the_loop_mask = df['text'].str.contains(human_in_the_loop_keywords, na=False)
    df.loc[human_in_the_loop_mask, 'AutomationCategory'] = 'Human-in-the-Loop'
    df.loc[df['Intent'] == 'Other', 'AutomationCategory'] = 'Human-in-the-Loop'

    # --- Begin Analysis Output ---
    
    print("=========================================================")
    print("      AI Support Ticket Automation Analysis        ")
    print("=========================================================\n")

    # 1. Executive Summary
    print("### 1. Executive Summary\n")
    automation_category_counts = df['AutomationCategory'].value_counts()
    fully_automated_count = automation_category_counts.get('Full Automation', 0)
    partially_automated_count = automation_category_counts.get('Agentic Workflow', 0)
    automatable_count = fully_automated_count + partially_automated_count
    automatable_percentage = (automatable_count / total_tickets) * 100 if total_tickets > 0 else 0
    
    automatable_intents_df = df[df['AutomationCategory'] != 'Human-in-the-Loop']
    top_3_automatable_intents = automatable_intents_df['Intent'].value_counts().nlargest(3)

    print(f"* **Automatable Potential:** **{automatable_percentage:.1f}%** of all support tickets are realistically automatable (fully or partially).")
    print(f"  * **Fully Automatable:** {fully_automated_count} tickets")
    print(f"  * **Partially Automatable (Agentic):** {partially_automated_count} tickets\n")
    print("* **Top 3 Automation Opportunities (80/20 Rule):**")
    for i, (intent, count) in enumerate(top_3_automatable_intents.items()):
        print(f"  {i+1}. **{intent}** ({count} tickets)")

    # 2. Ticket Anatomy & Triage Analysis
    print("\n### 2. Ticket Anatomy & Triage Analysis\n")
    print("**Top 10 Reasons for Contact (by Volume):**")
    print(df['Reason for Contact'].value_counts().nlargest(10).to_markdown())
    print("\n**Top 10 Ticket Types (by Volume):**")
    print(df['Ticket Type'].value_counts().nlargest(10).to_markdown())
    print("\n**Semantic Intent Clustering (True Intent):**")
    print(df['Intent'].value_counts().to_markdown())

    # 3. Automation Blueprint
    print("\n### 3. Automation Blueprint\n")

    # Category 1
    print("**Category 1: Full Automation Candidates (Low-Hanging Fruit)**")
    full_automation_candidates = df[df['AutomationCategory'] == 'Full Automation']['Intent'].value_counts().nlargest(5)
    print("* These are repetitive, rule-based tickets that can be resolved instantly by an AI.")
    for intent, count in full_automation_candidates.items():
        automation_type = "RAG from knowledge base"
        if intent in ['Password Reset / Login Issue', 'Billing Inquiry']:
            automation_type = "Simple data lookup via API"
        print(f"* **{intent}** ({count} tickets)\n    * **Automation Type:** {automation_type}")
    
    # Category 2
    print("\n**Category 2: Agentic Workflow Candidates (Multi-Step Processes)**")
    agentic_workflow_candidates = df[df['AutomationCategory'] == 'Agentic Workflow']['Intent'].value_counts().nlargest(3)
    print("* These tickets require a sequence of actions, data gathering, and decision-making.")
    for intent, count in agentic_workflow_candidates.items():
        print(f"* **{intent}** ({count} tickets)")
        if intent == 'Refund Request':
            print("    * **AI Workflow:** 1. Get user account ID -> 2. Look up transaction history -> 3. Check against refund policy -> 4. Process via API or flag for approval.")
        if intent == 'Membership Cancellation':
            print("    * **AI Workflow:** 1. Confirm user identity -> 2. Present retention offer (optional) -> 3. Process cancellation via API -> 4. Send confirmation email.")
        if intent == 'Update Payment Method':
             print("    * **AI Workflow:** 1. Authenticate user -> 2. Provide secure link to payment portal -> 3. Confirm update via API -> 4. Notify user of success.")

    # Category 3
    print("\n**Category 3: Human-in-the-Loop (Complex/High-Sentiment)**")
    print("* These tickets are too complex, emotionally charged, or novel for full automation. The AI's job is to prep the ticket for a human.")
    print("* **Key Characteristics:**")
    print("    * Contains high-sentiment keywords (e.g., 'angry', 'legal', 'frustrated').")
    print("    * Intent is uncategorized ('Other').")
    print("    * Involves multiple, layered issues within a single ticket.")

    # 4. Proposed AI System Architecture
    print("\n### 4. Proposed AI System Architecture\n")
    print("**Layer 1: The AI Triage Engine**")
    print("* An AI model receives every ticket via API. It performs semantic analysis on the subject/description to determine the 'True Intent' and checks for high-sentiment keywords. It then assigns the ticket to one of the three categories (Full Automation, Agentic, Human).")
    print("\n**Layer 2: The Automation Toolkit**")
    print("* A collection of specialized AI agents, each designed for a specific task:")
    print("    * `KnowledgeBot`: Handles 'General Question' and 'Store Hours' by performing RAG on a knowledge base of company policies and information.")
    print("    * `UserAccountAgent`: Manages 'Password Reset' and 'Update Payment Method' by interacting with user account APIs.")
    print("    * `BillingAgent`: Handles 'Billing Inquiry' and 'Refund Request' workflows by securely accessing billing systems and Stripe/payment processor APIs.")
    print("    * `MembershipAgent`: Manages 'Membership Cancellation' and 'Plan Change' requests via API integration.")
    print("\n**Layer 3: The Human Escalation Protocol**")
    print("* When the Triage Engine flags a ticket for a human, it doesn't just forward it. It pre-packages it for 10x faster resolution:")
    print("    1.  **Summarization:** The AI generates a one-sentence summary of the issue.")
    print("    2.  **Data Pre-fetch:** It fetches the customer's account details, order history, and previous support interactions.")
    print("    3.  **Contextualization:** It identifies the core issue (e.g., 'High-Sentiment Billing Dispute') and pulls up the relevant internal policy document.")
    print("    4.  **Smart Routing:** The ticket is routed to the correct human queue (e.g., Tier 2 Support, Billing Department, Leadership).")


# --- Main Execution ---
if __name__ == "__main__":
    analyze_support_tickets(csv_file_path)
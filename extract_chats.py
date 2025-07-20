import requests
import json
import time
import re
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load environment variables from a .env file
load_dotenv()

# It's best practice to load these from environment variables or a secure vault.
# The script will now automatically load them from your .env file.
CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('ZOHO_REFRESH_TOKEN')

# API Endpoints
TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
API_BASE_URL = "https://salesiq.zoho.com/api/v2/"

# Output file for the extracted data
OUTPUT_FILE = "salesiq_chat_transcripts.json"

# --- FUNCTIONS ---

def get_new_access_token():
    """
    Refreshes the OAuth 2.0 access token using the long-lived refresh token.
    Returns the new access token, or None if an error occurs.
    """
    print("Refreshing access token...")
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("Error: Make sure ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, and ZOHO_REFRESH_TOKEN are set in your .env file.")
        return None
        
    payload = {
        'refresh_token': REFRESH_TOKEN,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token'
    }
    try:
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        token_data = response.json()
        if 'access_token' in token_data:
            print("Successfully refreshed access token.")
            return token_data['access_token']
        else:
            print(f"Error refreshing token: {token_data.get('error', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during token refresh: {e}")
        return None

def get_all_chat_ids(access_token):
    """
    Paginates through the SalesIQ API to fetch all chat IDs.
    Handles rate limiting by sleeping if necessary.
    Returns a list of all chat IDs.
    """
    all_chat_ids = []
    start_index = 1
    has_more_data = True
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}

    print("Starting to fetch all chat IDs...")
    while has_more_data:
        print(f"Fetching chats starting from index {start_index}...")
        params = {'limit': 100, 'start_index': start_index}
        try:
            response = requests.get(f"{API_BASE_URL}/chats", headers=headers, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                print("Rate limit hit. Waiting for 60 seconds...")
                time.sleep(60)
                continue # Retry the same request

            response.raise_for_status()
            data = response.json()

            if data.get('code') == 0 and 'data' in data:
                chats = data['data']
                if not chats:
                    has_more_data = False
                    print("No more chats found.")
                else:
                    chat_ids = [chat['id'] for chat in chats]
                    all_chat_ids.extend(chat_ids)
                    print(f"Fetched {len(chat_ids)} chat IDs. Total fetched: {len(all_chat_ids)}")
                    start_index += 100
                    # Be respectful to the API, add a small delay
                    time.sleep(1) 
            else:
                print(f"API Error when fetching chat list: {data.get('message', 'Unknown error')}")
                has_more_data = False

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching chat IDs: {e}")
            has_more_data = False
            
    print(f"Finished fetching. Found a total of {len(all_chat_ids)} chat IDs.")
    return all_chat_ids

def get_chat_conversation(chat_id, access_token):
    """
    Fetches the full conversation transcript for a single chat ID.
    Returns the conversation data, or None if an error occurs.
    """
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    try:
        response = requests.get(f"{API_BASE_URL}/chats/{chat_id}/conversation", headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('code') == 0 and 'data' in data:
            return data['data']
        else:
            print(f"Could not fetch conversation for chat ID {chat_id}: {data.get('message', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred fetching conversation for chat ID {chat_id}: {e}")
        return None

def anonymize_text(text):
    """
    A simple function to scrub Personally Identifiable Information (PII) from text.
    This is a basic implementation and should be expanded based on your specific needs.
    """
    if not isinstance(text, str):
        return text
    # Regex to find email addresses
    text = re.sub(r'\S+@\S+', '[EMAIL_REDACTED]', text)
    # Regex to find phone numbers (basic US format)
    text = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_REDACTED]', text)
    # You can add more regex for names, addresses, etc.
    return text

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    print("Script started. Loading credentials from .env file...")
    
    # 1. Get a fresh access token
    access_token = get_new_access_token()

    if not access_token:
        print("Could not obtain access token. Exiting.")
    else:
        # 2. Fetch all chat IDs
        chat_ids = get_all_chat_ids(access_token)
        
        if not chat_ids:
            print("No chat IDs were found. Exiting.")
        else:
            all_transcripts = []
            total_chats = len(chat_ids)
            
            # 3. Fetch and process each conversation
            for i, chat_id in enumerate(chat_ids):
                print(f"Processing chat {i+1}/{total_chats} (ID: {chat_id})...")
                conversation_data = get_chat_conversation(chat_id, access_token)
                
                if conversation_data and 'conversation' in conversation_data:
                    # Anonymize each message in the conversation
                    for message in conversation_data['conversation']:
                        if 'msg' in message:
                            message['msg'] = anonymize_text(message['msg'])
                        if 'sent_by' in message:
                            message['sent_by'] = anonymize_text(message['sent_by'])
                    
                    all_transcripts.append(conversation_data)
                
                # Add a delay to avoid hitting rate limits
                time.sleep(1)

            # 4. Save the final dataset to a file
            try:
                with open(OUTPUT_FILE, 'w') as f:
                    json.dump(all_transcripts, f, indent=4)
                print(f"\nSuccessfully extracted and anonymized {len(all_transcripts)} transcripts.")
                print(f"Data saved to {OUTPUT_FILE}")
            except IOError as e:
                print(f"Error writing to file {OUTPUT_FILE}: {e}")

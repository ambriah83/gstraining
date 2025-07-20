import pandas as pd
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
import sys

# --- CONFIGURATION ---
# IMPORTANT: Replace this with the correct path to your CSV file.
csv_file_path = 'cleaned_zoho_tickets_final.csv'

# --- Topic Modeling Settings ---
# How many distinct topics should the AI try to find in the "Other" category?
NUM_TOPICS = 10
# How many top words should be displayed for each topic?
NUM_WORDS_PER_TOPIC = 15
# --- END CONFIGURATION ---


def map_initial_intent(text):
    """Maps text to a predefined intent based on keywords."""
    text = str(text).lower() # Ensure text is a lowercase string
    if any(keyword in text for keyword in ['cancel', 'cancellation', 'unsubscribe', 'end my account', 'close my account']):
        return 'Membership Cancellation'
    if any(keyword in text for keyword in ['password', 'reset', 'forgot', 'login issue', 'can\'t log in']):
        return 'Password Reset / Login Issue'
    if any(keyword in text for keyword in ['refund', 'money back', 'reimburse']):
        return 'Refund Request'
    # Add other intents from your initial analysis if you want them to be excluded from 'Other'
    return 'Other'


def analyze_and_count_topics(file_path):
    """
    Analyzes 'Other' tickets, discovers topics, and counts the number of tickets per topic.
    """
    print("--- Starting Full Topic Analysis ---")
    try:
        df = pd.read_csv(file_path)
        print(f"✅ File '{file_path}' loaded successfully ({len(df)} total tickets).")
    except FileNotFoundError:
        print(f"❌ ERROR: The file '{file_path}' was not found.")
        sys.exit()
    except Exception as e:
        print(f"❌ An unexpected error occurred while loading the file: {e}")
        sys.exit()

    # --- 1. Initial Classification ---
    print("\nStep 1: Classifying all tickets to isolate the 'Other' category...")
    df['text'] = df['Subject'].fillna('') + ' ' + df['Description'].fillna('')
    df['Intent'] = df['text'].apply(map_initial_intent)
    other_tickets = df[df['Intent'] == 'Other'].copy()

    if other_tickets.empty:
        print("No tickets were classified as 'Other'. Nothing to analyze.")
        return
    
    print(f"✅ Found {len(other_tickets)} tickets classified as 'Other'.")

    # --- 2. Vectorization (Preparing text for AI) ---
    print("\nStep 2: Preparing text data for the AI model...")
    try:
        # Using min_df=5 means a word must appear in at least 5 different tickets to be considered.
        vectorizer = CountVectorizer(max_df=0.9, min_df=5, stop_words='english')
        X = vectorizer.fit_transform(other_tickets['text'])
        
        vocabulary_size = len(vectorizer.get_feature_names_out())
        if vocabulary_size == 0:
            print("❌ ERROR: Could not build a vocabulary from the text.")
            print("   This can happen if the 'Other' tickets have very little text or no words are shared across at least 5 tickets (based on min_df=5).")
            sys.exit()

        print(f"✅ Text preparation complete. Vocabulary size: {vocabulary_size} words.")

    except Exception as e:
        print(f"❌ An error occurred during text preparation: {e}")
        sys.exit()


    # --- 3. Topic Modeling ---
    print("\nStep 3: Running the AI topic model... (This may take a moment)")
    try:
        # Using random_state=42 makes the topic results reproducible.
        lda = LatentDirichletAllocation(n_components=NUM_TOPICS, random_state=42)
        lda.fit(X)
        print("✅ AI model training complete.")
    except Exception as e:
        print(f"❌ An error occurred while training the AI model: {e}")
        sys.exit()

    # --- 4. Assign Topics and Count ---
    print("\nStep 4: Assigning tickets to topics and counting the results...")
    topic_assignments = lda.transform(X).argmax(axis=1)
    topic_counts = pd.Series(topic_assignments).value_counts().sort_index()
    print("✅ Counting complete.")

    # --- 5. Display Results ---
    print("\n================================================================")
    print(f"      Discovered {NUM_TOPICS} Topics in the 'Other' Category")
    print("================================================================\n")

    feature_names = vectorizer.get_feature_names_out()
    for topic_idx in range(NUM_TOPICS):
        count = topic_counts.get(topic_idx, 0)
        topic_keywords = lda.components_[topic_idx]
        top_words = [feature_names[i] for i in topic_keywords.argsort()[:-NUM_WORDS_PER_TOPIC - 1:-1]]
        
        print(f"## Topic #{topic_idx + 1} ({count} tickets)")
        print(f"   -> Keywords: {', '.join(top_words)}")
        print(f"   -> Your Suggested Name: _________________________________\n")

# --- Main Execution ---
if __name__ == "__main__":
    analyze_and_count_topics(csv_file_path)
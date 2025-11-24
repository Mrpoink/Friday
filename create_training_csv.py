import csv
import os
import glob
import json
import random

def read_csv(file_path):
    with open(file_path, mode='r', newline='', encoding='utf-8', errors='ignore') as file:
        reader = csv.reader(file)
        data = [row for row in reader]
    return data

def parse_data(data):
    parsed_data = []
    for row in data:
        # Example parsing logic; modify as needed
        parsed_row = {
            'Title': row[0],
            'Content': row[1],
            'Date': row[2],
            'Attachments?': row[3]
        }
        parsed_data.append(parsed_row)
    return parsed_data

def section_data_by_time(data, hours=6):
    """
    Aggregates messages into sections based on 6-hour time blocks.
    All messages within a 6-hour window are grouped together.
    """
    from datetime import datetime, timedelta
    import re

    if not data or len(data) == 0:
        return []
    
    # Remove header if present
    if data[0]['Title'] == 'Title':
        data = data[1:]
    
    sections = []
    current_section = []
    section_start_time = None
    
    for row in data:
        # Skip empty messages
        if not row['Date'] or row['Date'].strip() == '':
            continue
            
        try:
            # Parse date - format example: "Friday, Feb 5, 2021 8:51 PM"
            date_str = row['Date'].strip()
            # Remove day of week if present
            date_str = re.sub(r'^[A-Za-z]+,\s*', '', date_str)
            current_time = datetime.strptime(date_str, "%b %d, %Y %I:%M %p")
            
            # Start a new section if this is the first message or if we've exceeded the time window
            if section_start_time is None:
                section_start_time = current_time
                current_section = [row]
            elif (current_time - section_start_time) <= timedelta(hours=hours):
                current_section.append(row)
            else:
                # Save current section and start a new one
                if current_section:
                    sections.append(current_section)
                section_start_time = current_time
                current_section = [row]
        except Exception as e:
            # If date parsing fails, add to current section anyway
            if current_section is not None:
                current_section.append(row)
            else:
                current_section = [row]
    
    # Don't forget the last section
    if current_section:
        sections.append(current_section)
    
    return sections

def create_better_data(data):
    
    total_data = []
    
    if data and data[0]['Title'] == 'Title': #remove headers
        data.pop(0)
    
    # Skip the very first 'Me' message to align the conversation properly
    i = 0
    first_me_skipped = False
    
    while i < len(data):
    
        if not data[i]['Content'] or data[i]['Content'].strip() == '': #Cannot have empty messages
            i += 1
            continue
        
        if data[i]['Title'] == 'Me': #if message is from me
            
            # Skip the first 'Me' message in the entire conversation
            if not first_me_skipped:
                while i < len(data) and data[i]['Title'] != 'Me':
                    i += 1
                first_me_skipped = True
                continue
            
            me_messages = []
            
            while i < len(data) and data[i]['Title'] == 'Me':
                if data[i]['Content'] and data[i]['Content'].strip() != '':
                    me_messages.append(data[i]['Content'].strip())
                i += 1
            
            while i < len(data) and (not data[i]['Content'] or data[i]['Content'].strip() == ''):
                i += 1
            
            if i < len(data) and data[i]['Title'] != 'Me':
                entry = {
                    'Train': ' '.join(me_messages), 
                    'Test': data[i]['Content'].strip()
                }
                total_data.append(entry)
                i += 1
        else:
            
            i += 1
    
    return total_data

def fix_data(data):
    
    new_entry = {}
    new_list = []
    
    for i in range(len(data)):
        if i == 0:
            continue
        new_entry['Train'] = data[i-1]['Test']
        new_entry['Test'] = data[i]['Train']
        new_list.append(new_entry)
        new_entry = {}
        
    return new_list
        
            

def build_progressive_conversations(data):
    """
    Creates progressive conversation context by building up the conversation gradually.
    Returns a list of dictionaries where:
    - 'messages': all conversation history (user/assistant turns)
    - 'target': the most recent assistant response (what we're training to predict)
    """
    progressive_data = []
    
    for conversation in data:
        # For each conversation section, build progressive context
        for i in range(len(conversation)):
            # Build conversation history up to current turn
            messages = []
            
            for j in range(i + 1):
                # Add user message
                messages.append({
                    'role': 'user',
                    'content': conversation[j]['Train']
                })
                # Add assistant response
                messages.append({
                    'role': 'assistant',
                    'content': conversation[j]['Test']
                })
            
            # The target is the most recent assistant message
            target = messages[-1]['content']
            # Messages for context include everything up to (but not including) the target
            context_messages = messages[:-1]
            
            # Create training entry
            training_entry = {
                'messages': context_messages,
                'target': target
            }
            
            progressive_data.append(training_entry)
    
    return progressive_data

# Get all CSV files in the Converted_CSVs directory
csv_files = glob.glob("Converted_CSVs/*.csv")

print(f"Found {len(csv_files)} CSV files to process\n")

# Process all CSV files and aggregate training data
total_data = []

for file_name in csv_files:
    print(f"Processing: {file_name}")
    
    try:
        data = read_csv(file_name)
        parsed_data = parse_data(data)
        
        # Section data into 6-hour conversation blocks
        sections = section_data_by_time(parsed_data, hours=6)
        
        # Process each section through create_better_data and fix_data
        conversations = []
        for section in sections:
            section_processed = create_better_data(section)
            if section_processed:  # Only process if there's data
                fixed_section = fix_data(section_processed)
                conversations.append(fixed_section)
        
        # Build progressive conversations with messages/target format
        file_training_data = build_progressive_conversations(conversations)
        total_data.extend(file_training_data)
        
        print(f"  Added {len(file_training_data)} training examples from this file")
        
    except Exception as e:
        print(f"  Error processing {file_name}: {e}")
    
    print()

print(f"\n{'='*60}")
print(f"TOTAL TRAINING EXAMPLES: {len(total_data)}")
print(f"{'='*60}\n")

# Print a few sample examples
for i in range(min(3, len(total_data))):
    print(f"Sample Example {i+1}:")
    print(f"  Context messages: {len(total_data[i]['messages'])}")
    for msg in total_data[i]['messages']:
        print(f"    {msg['role']}: {msg['content'][:50]}...")
    print(f"  Target: {total_data[i]['target'][:50]}...")
    print()

# Shuffle the data for random train/test split
random.seed(42)  # For reproducibility
random.shuffle(total_data)

# Split into 80% train, 20% test
split_index = int(len(total_data) * 0.8)
train_data = total_data[:split_index]
test_data = total_data[split_index:]

print(f"\nTrain examples: {len(train_data)}")
print(f"Test examples: {len(test_data)}\n")

# Export train data to CSV
def export_to_csv(data, filename):
    """Export training data to CSV with messages serialized as JSON"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['messages', 'target'])
        
        # Write data rows
        for entry in data:
            # Serialize messages list to JSON string
            messages_json = json.dumps(entry['messages'])
            writer.writerow([messages_json, entry['target']])
    
    print(f"Exported {len(data)} examples to {filename}")

# Export both train and test datasets
export_to_csv(train_data, 'training_data.csv')
export_to_csv(test_data, 'test_data.csv')

print("\n✓ Export complete!")


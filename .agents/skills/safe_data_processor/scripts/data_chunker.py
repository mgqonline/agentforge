import csv
import sys
import os

def preview_csv(filepath, num_rows=5):
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        sys.exit(1)
        
    try:
        file_size = os.path.getsize(filepath)
        print(f"File Size: {file_size / (1024*1024):.2f} MB")
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
                print("Headers:", headers)
                print(f"\n--- First {num_rows} Rows ---")
                for i, row in enumerate(reader):
                    if i >= num_rows:
                        break
                    print(row)
            except StopIteration:
                print("File is empty.")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != 'preview':
        print("Usage: python data_chunker.py preview <filepath>")
        sys.exit(1)
    filepath = sys.argv[2]
    preview_csv(filepath)

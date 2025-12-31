import os

def download_professional_dataset():
    """
    Downloads the 'Football Data from Transfermarkt' (5.7M+ records) via Kaggle API.
    Requires: pip install kaggle, and ~/.kaggle/kaggle.json
    """
    dataset_name = "davidcaravajo/football-data-from-transfermarkt"
    output_dir = "soccer_data/raw_data/kaggle_historical"
    
    print(f"Attempting to download {dataset_name}...")
    os.makedirs(output_dir, exist_ok=True)
    
    # Command: kaggle datasets download -d davidcaravajo/football-data-from-transfermarkt --unzip -p soccer_data/raw_data/kaggle_historical
    try:
        os.system(f"kaggle datasets download -d {dataset_name} --unzip -p {output_dir}")
        print("Download complete.")
    except Exception as e:
        print(f"Error: Make sure kaggle API is installed and configured. {e}")
        print(f"Manual download link: https://www.kaggle.com/datasets/{dataset_name}")

if __name__ == "__main__":
    download_professional_dataset()

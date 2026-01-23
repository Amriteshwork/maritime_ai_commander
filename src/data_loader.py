import pandas as pd
from datetime import datetime
import os
import numpy as np

class DataLoader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = None
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Data file not found at: {self.filepath}")
        
        # 1. Load CSV with low_memory=False to prevent dtype warnings
        self.df = pd.read_csv(self.filepath, low_memory=False)
        
        # 2. Rename & Normalize Columns (Handle variations)
        # Some CSVs use 'BaseDateTime', others 'Timestamp'
        col_map = {'BaseDateTime': 'Timestamp', 'LAT': 'LAT', 'LON': 'LON', 
                   'SOG': 'SOG', 'COG': 'COG', 'VesselName': 'VesselName'}
        self.df.rename(columns=lambda x: col_map.get(x, x), inplace=True)
        
        # 3. Robust Type Conversion (The Anti-Crash Layer)
        # Coerce errors: "Invalid" becomes NaN, then we fill with 0
        self.df['LAT'] = pd.to_numeric(self.df['LAT'], errors='coerce')
        self.df['LON'] = pd.to_numeric(self.df['LON'], errors='coerce')
        self.df['SOG'] = pd.to_numeric(self.df['SOG'], errors='coerce').fillna(0.0)
        self.df['COG'] = pd.to_numeric(self.df['COG'], errors='coerce').fillna(0.0)
        self.df['MMSI'] = pd.to_numeric(self.df['MMSI'], errors='coerce').fillna(0).astype(int)
        
        # 4. Handle Timestamps (The "Stale Data" Fix)
        self.df['Timestamp'] = pd.to_datetime(self.df['Timestamp'], errors='coerce')
        # Drop rows with NO time or NO location (useless data)
        self.df.dropna(subset=['Timestamp', 'LAT', 'LON'], inplace=True)
        
        # 5. Clean Names (Remove "nan" strings and whitespace)
        self.df['VesselName'] = self.df['VesselName'].astype(str).str.strip().str.upper()
        self.df = self.df[self.df['VesselName'] != 'NAN']
        
        # 6. Deduplication (Keep only the latest ping per vessel per timestamp)
        self.df.drop_duplicates(subset=['MMSI', 'Timestamp'], inplace=True)
        
        print(f"✅ Robust Load: {len(self.df)} clean records ready.")

    def get_vessel_history(self, vessel_name: str) -> pd.DataFrame:
        """Fetch history, sorted and cleaned."""
        if self.df is None: self.load_data()
        
        # Exact match first
        matches = self.df[self.df['VesselName'] == vessel_name]
        
        if matches.empty:
            return pd.DataFrame() # Return empty DF instead of None
            
        return matches.sort_values(by='Timestamp')

    def get_all_vessel_names(self):
        if self.df is None: self.load_data()
        return self.df['VesselName'].unique().tolist()
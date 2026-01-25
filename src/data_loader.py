import os
import pandas as pd

import logging
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = None
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Data file not found at: {self.filepath}")
        
        # Load CSV
        try:
            self.df = pd.read_csv(self.filepath, low_memory=False)
        except Exception as e:
            logger.error(f"Not able to load CSV data file: {str(e)}")
        
        # Normalize Columns
        col_map = {'BaseDateTime': 'Timestamp', 'LAT': 'LAT', 'LON': 'LON', 
                   'SOG': 'SOG', 'COG': 'COG', 'VesselName': 'VesselName'}
        self.df.rename(columns=lambda x: col_map.get(x, x), inplace=True)
        
        # Type Conversion
        self.df['LAT'] = pd.to_numeric(self.df['LAT'], errors='coerce')
        self.df['LON'] = pd.to_numeric(self.df['LON'], errors='coerce')
        self.df['SOG'] = pd.to_numeric(self.df['SOG'], errors='coerce').fillna(0.0)
        self.df['COG'] = pd.to_numeric(self.df['COG'], errors='coerce').fillna(0.0)
        self.df['MMSI'] = pd.to_numeric(self.df['MMSI'], errors='coerce').fillna(0).astype(int)
        
        # FIX: Enforce UTC Timezone
        self.df['Timestamp'] = pd.to_datetime(self.df['Timestamp'], errors='coerce', utc=True)
        
        # Drop invalid rows
        self.df.dropna(subset=['Timestamp', 'LAT', 'LON'], inplace=True)
        
        # Clean Names
        self.df['VesselName'] = self.df['VesselName'].astype(str).str.strip().str.upper()
        self.df = self.df[self.df['VesselName'] != 'NAN']
        
        # Deduplication
        self.df.drop_duplicates(subset=['MMSI', 'Timestamp'], inplace=True)
    
        logger.info(f"Robust Load: {len(self.df)} clean records ready.")

    def get_vessel_history(self, vessel_name: str) -> pd.DataFrame:
        """Fetch history, sorted and cleaned."""
        if self.df is None: self.load_data()
    
        # Input Normalization
        clean_name = str(vessel_name).strip().upper()
        
        matches = self.df[self.df['VesselName'] == clean_name]
        
        if matches.empty:
            return pd.DataFrame() 
            
        return matches.sort_values(by='Timestamp')

    def get_all_vessel_names(self):
        if self.df is None: self.load_data()
        return self.df['VesselName'].unique().tolist()
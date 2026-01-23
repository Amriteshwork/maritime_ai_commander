import spacy
from spacy.matcher import Matcher
from spacy.tokens import Span
import re

class NLPProcessor:
    def __init__(self, valid_vessels: list):
        self.valid_vessels = valid_vessels
        
        # Load Spacy (Small model, efficient)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("⚠️ Model 'en_core_web_sm' not found. Downloading...")
            from spacy.cli import download
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

        # --- 1. ENTITY RECOGNITION (The "Who") ---
        # We create a specific pipeline for Vessels to override general English entities
        self.ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        patterns = [{"label": "VESSEL", "pattern": v} for v in valid_vessels]
        self.ruler.add_patterns(patterns)

        # --- 2. INTENT MATCHING (The "What") ---
        # We use Matcher to look for linguistic patterns, not just keywords
        self.matcher = Matcher(self.nlp.vocab)
        
        # Pattern: PREDICT (e.g., "Predict where...", "Forecast the...", "Future position")
        self.matcher.add("PREDICT", [
            # 1. Explicit Verbs (Standard)
            [{"LEMMA": {"IN": ["predict", "forecast", "estimate", "project", "calculate"]}}],
            
            # 2. Noun Phrases
            [{"LOWER": "future"}, {"LOWER": "position"}],
            [{"LOWER": "next"}, {"LOWER": "location"}],
            
            # 3. Question Format: "Where will it be?"
            [{"LOWER": "where"}, {"LOWER": "will"}, {"LOWER": "it"}, {"LOWER": "be"}],
            
            # 4. NEW: Relative Clause: "Where it will be" (Fixes your bug)
            [{"LOWER": "where"}, {"LOWER": "it"}, {"LOWER": "will"}, {"LOWER": "be"}],
            
            # 5. NEW: Broad Future Tense Catch-all
            # Catches "It will be at...", "Will be...", "Going to be"
            [{"LOWER": "will"}, {"LOWER": "be"}],
            [{"LOWER": "going"}, {"LOWER": "to"}, {"LOWER": "be"}]
        ])

        # Pattern: VERIFY (e.g., "Verify...", "Check for spoofing", "Validate")
        self.matcher.add("VERIFY", [
            [{"LEMMA": {"IN": ["verify", "check", "validate", "detect", "audit"]}}],
            [{"LOWER": "security"}, {"LOWER": "scan"}],
            [{"LOWER": "is"}, {"LOWER": "it"}, {"LOWER": "consistent"}]
        ])

        # Pattern: SHOW (Default fallback, but explicit here)
        self.matcher.add("SHOW", [
            [{"LEMMA": {"IN": ["show", "display", "get", "find", "track", "locate"]}}],
            [{"LOWER": "current"}, {"LOWER": "position"}],
            [{"LOWER": "last"}, {"LOWER": "seen"}]
        ])

    def parse_query(self, query: str, context_vessel: str = None):
        """
        Parses the query using linguistic structure.
        """
        doc = self.nlp(query.upper()) # Uppercase to match vessel names exactly
        
        # 1. Extract Vessel (NER + Context)
        vessel = None
        
        # Priority A: Explicit Entity Found
        for ent in doc.ents:
            if ent.label_ == "VESSEL":
                vessel = ent.text
                break
        
        # Priority B: Context Resolution (Pronouns)
        # Handles: "IT", "ITS", "THE SHIP"
        if not vessel and context_vessel:
            pronoun_tokens = ["IT", "ITS", "THEIR", "THIS", "SHE", "HE"]
            # Check if any token in the doc is a pronoun referring to the ship
            if any(token.text in pronoun_tokens for token in doc):
                vessel = context_vessel
            elif "THE SHIP" in query.upper() or "THE VESSEL" in query.upper():
                vessel = context_vessel

        # 2. Extract Intent (Pattern Matching)
        matches = self.matcher(doc)
        # Default to SHOW if no specific intent is found
        intent = "SHOW"
        
        # Sort matches by length (longest match wins) to prefer specific phrases
        # e.g., "Future Position" (PREDICT) > "Position" (SHOW)
        if matches:
            matches.sort(key=lambda x: (x[1] - x[2]), reverse=True) # Sort by span length
            match_id, start, end = matches[0]
            intent = self.nlp.vocab.strings[match_id]

        # 3. Extract Time Horizon (Heuristic)
        # "After 30 minutes", "In 1 hour"
        time_minutes = 30 # Default
        if intent == "PREDICT":
            # Simple regex for time extraction is acceptable and robust here
            time_match = re.search(r'(\d+)\s*(MIN|HR|HOUR)', query.upper())
            if time_match:
                val = int(time_match.group(1))
                unit = time_match.group(2)
                time_minutes = val * 60 if "H" in unit else val

        return {
            "intent": intent,
            "vessel": vessel,
            "minutes": time_minutes
        }
    
    def get_suggestions(self, query: str, n=3):
        import difflib
        return difflib.get_close_matches(query.upper(), self.valid_vessels, n=n, cutoff=0.4)
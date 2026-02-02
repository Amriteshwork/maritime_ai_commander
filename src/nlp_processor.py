import re
import spacy
import difflib
from spacy.matcher import Matcher
from typing import Dict

import logging
logger = logging.getLogger(__name__)

class NLPProcessor:
    def __init__(self, valid_vessels: list):
        self.valid_vessels = valid_vessels
        
        # Load Spacy
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.error("Model 'en_core_web_sm' not found. Use 'python -m spacy download en_core_web_sm' to download")

        # ENTITY RECOGNITION (Robust Case-Insensitive Matching). Generate token patterns that match ANY case (LOWER). "INS Kolkata" -> [{"LOWER": "ins"}, {"LOWER": "kolkata"}]
        self.ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        patterns = []
        for v in valid_vessels: # pattern to match word (case-insensitively)
            token_pattern = [{"LOWER": word.lower()} for word in v.split()]
            patterns.append({"label": "VESSEL", "pattern": token_pattern})
        
        self.ruler.add_patterns(patterns)

        # INTENT MATCHING
        self.matcher = Matcher(self.nlp.vocab)
        # Pattern: PREDICT
        self.matcher.add("PREDICT", [
            [{"LEMMA": {"IN": ["predict", "forecast", "estimate", "project", "calculate"]}}],
            [{"LOWER": "future"}, {"LOWER": "position"}],
            [{"LOWER": "next"}, {"LOWER": "location"}],
            [{"LOWER": "where"}, {"LOWER": "will"}, {"LOWER": "it"}, {"LOWER": "be"}],
            [{"LOWER": "where"}, {"LOWER": "it"}, {"LOWER": "will"}, {"LOWER": "be"}],
            [{"LOWER": "will"}, {"LOWER": "be"}],
            [{"LOWER": "going"}, {"LOWER": "to"}, {"LOWER": "be"}]
        ])

        # Pattern: VERIFY
        self.matcher.add("VERIFY", [
            [{"LEMMA": {"IN": ["verify", "check", "validate", "detect", "audit"]}}],
            [{"LOWER": "security"}, {"LOWER": "scan"}],
            [{"LOWER": "is"}, {"LOWER": "it"}, {"LOWER": "consistent"}],
            [{"LOWER": "anomalies"}], 
            [{"LOWER": "spoofing"}]
        ])

        # Pattern: SHOW
        self.matcher.add("SHOW", [
            [{"LEMMA": {"IN": ["show", "display", "get", "find", "track", "locate"]}}],
            [{"LOWER": "current"}, {"LOWER": "position"}],
            [{"LOWER": "last"}, {"LOWER": "seen"}]
        ])

    def parse_query(self, query: str, context_vessel: str = None)-> Dict[str, str]:
        """
        Parses the query using linguistic structure.
        """
        doc = self.nlp(query) 
        
        # Extract Vessel
        vessel = None
        
        # Priority A: Explicit Entity Found (Case-Insensitive)
        for ent in doc.ents:
            if ent.label_ == "VESSEL":
                vessel = ent.text.upper() 
                break
        
        # Priority B: Context Resolution
        if not vessel and context_vessel:
            pronoun_tokens = ["IT", "ITS", "THEIR", "THIS"]
            if any(token.text.upper() in pronoun_tokens for token in doc):
                vessel = context_vessel
            elif "THE SHIP" in query.upper() or "THE VESSEL" in query.upper():
                vessel = context_vessel

        # Extract Intent
        matches = self.matcher(doc)
        intent = "SHOW"
        
        if matches:
            matches.sort(key=lambda x: (x[1] - x[2]), reverse=True)
            match_id, _, _ = matches[0]
            intent = self.nlp.vocab.strings[match_id]

        # Extract Time Horizon
        time_minutes = 30
        if intent == "PREDICT":
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
    
    def get_suggestions(self, query: str, n=3)->str:
        return difflib.get_close_matches(query.upper(), self.valid_vessels, n=n, cutoff=0.4)
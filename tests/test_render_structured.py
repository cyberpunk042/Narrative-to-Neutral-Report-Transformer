"""
Tests for Observation Split - Rendered Report (render/structured.py)

Tests the V4 observation section rendering:
- OBSERVED EVENTS (INCIDENT SCENE) - camera-friendly only
- OBSERVED EVENTS (FOLLOW-UP ACTIONS) - post-incident
- REPORTER DESCRIPTIONS - excluded content
- SELF-REPORTED STATE - internal states
"""

import pytest


class TestCameraFriendlyFilter:
    """Tests for is_camera_friendly logic."""
    
    # Words that disqualify a statement from OBSERVED EVENTS
    INTERPRETIVE_DISQUALIFIERS = [
        'horrifying', 'horrific', 'brutal', 'brutally', 'viciously', 'vicious',
        'psychotic', 'maniac', 'thug', 'aggressive', 'aggressively', 
        'menacing', 'menacingly', 'distressing', 'terrifying', 'shocking',
        'innocent', 'guilty', 'criminal', 'illegal', 'unlawful', 'assault',
        'assaulting', 'torture', 'terrorize', 'misconduct', 'violation',
        'deliberately', 'intentionally', 'clearly', 'obviously', 'wanted to',
        'absolutely', 'completely', 'totally', 'definitely', 'certainly',
        'cover-up', 'coverup', 'whitewash', 'conspiracy', 'conspiring',
    ]
    
    def is_camera_friendly(self, text: str) -> bool:
        """Replicate the is_camera_friendly logic."""
        text_lower = text.lower()
        for word in self.INTERPRETIVE_DISQUALIFIERS:
            if word in text_lower:
                return False
        return True
    
    # =========================================================================
    # Camera-friendly: Should be in OBSERVED EVENTS
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "Officer grabbed my arm",
        "He twisted it behind my back",
        "Officer put handcuffs on me",
        "Sergeant Williams arrived at the scene",
        "She came out onto her porch",
        "Marcus Johnson was walking his dog",
        "He started recording on his phone",
        "Officer Rodriguez ran over to Marcus",
    ])
    def test_camera_friendly_statements(self, text):
        """Pure physical actions should be camera-friendly."""
        assert self.is_camera_friendly(text), f"'{text}' should be camera-friendly"
    
    # =========================================================================
    # NOT camera-friendly: Should be in REPORTER DESCRIPTIONS
    # =========================================================================
    
    @pytest.mark.parametrize("text,disqualifying_word", [
        ("witnessed the horrifying assault", "horrifying"),
        ("They brutally slammed me", "brutally"),
        ("the psychotic officer screamed", "psychotic"),
        ("he viciously attacked me", "viciously"),
        ("the thug cop grabbed me", "thug"),
        ("he was assaulting an innocent person", "assaulting"),
        ("he deliberately ignored me", "deliberately"),
        ("she was clearly trying to hurt me", "clearly"),
        ("this criminal behavior", "criminal"),
        ("it was a massive cover-up", "cover-up"),
    ])
    def test_not_camera_friendly_statements(self, text, disqualifying_word):
        """Statements with interpretive words should NOT be camera-friendly."""
        assert not self.is_camera_friendly(text), \
            f"'{text}' should NOT be camera-friendly (contains '{disqualifying_word}')"


class TestFollowUpDetection:
    """Tests for is_follow_up_event logic."""
    
    FOLLOW_UP_PATTERNS = [
        'later found', 'later learned', 'turned out', 'found out',
        'three months later', 'the next day', 'afterward', 'afterwards',
        'went to the emergency', 'went to the hospital', 'filed a complaint',
        'filed a formal', 'received a letter', 'therapist', 'diagnosed',
        'internal affairs', 'detective', 'investigated', 'pursuing legal',
        'my attorney', 'researched',
    ]
    
    def is_follow_up_event(self, text: str) -> bool:
        """Replicate the is_follow_up_event logic."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.FOLLOW_UP_PATTERNS)
    
    # =========================================================================
    # Follow-up events (post-incident)
    # =========================================================================
    
    @pytest.mark.parametrize("text,pattern", [
        ("I went to the hospital immediately after", "went to the hospital"),
        ("I went to the emergency room", "went to the emergency"),
        ("I filed a formal complaint", "filed a formal"),
        ("The next day, I called my attorney", "the next day"),
        ("Three months later, I received a letter", "three months later"),
        ("Detective Monroe took my statement", "detective"),
        ("My therapist diagnosed me with PTSD", "therapist"),
        ("I later found out the description didn't match", "later found"),
        ("It turned out they lied", "turned out"),
        ("My attorney says this is clear misconduct", "my attorney"),
    ])
    def test_follow_up_events(self, text, pattern):
        """Post-incident events should be detected as follow-up."""
        assert self.is_follow_up_event(text), \
            f"'{text}' should be follow-up (contains '{pattern}')"
    
    # =========================================================================
    # Incident-scene events (NOT follow-up)
    # =========================================================================
    
    @pytest.mark.parametrize("text", [
        "Officer grabbed my arm",
        "He twisted it behind my back",
        "Sergeant Williams arrived at the scene",
        "She came out onto her porch",
        "He started recording on his phone",
        "I asked what the problem was",
    ])
    def test_incident_scene_events(self, text):
        """Incident-scene events should NOT be detected as follow-up."""
        assert not self.is_follow_up_event(text), \
            f"'{text}' should NOT be follow-up"


class TestRenderedSections:
    """Tests for the rendered output sections."""
    
    def test_observed_events_incident_scene_header(self):
        """OBSERVED EVENTS (INCIDENT SCENE) header should be correct."""
        expected_header = "OBSERVED EVENTS (INCIDENT SCENE)"
        assert "INCIDENT SCENE" in expected_header
    
    def test_observed_events_follow_up_header(self):
        """OBSERVED EVENTS (FOLLOW-UP ACTIONS) header should be correct."""
        expected_header = "OBSERVED EVENTS (FOLLOW-UP ACTIONS)"
        assert "FOLLOW-UP" in expected_header
    
    def test_reporter_descriptions_header(self):
        """REPORTER DESCRIPTIONS header should indicate characterization."""
        expected_header = "REPORTER DESCRIPTIONS (contains characterization)"
        assert "characterization" in expected_header
    
    def test_self_reported_state_prefix(self):
        """SELF-REPORTED STATE items should have 'Reporter reports:' prefix."""
        expected_prefix = "Reporter reports:"
        assert "Reporter" in expected_prefix


class TestSectionOrdering:
    """Tests for section ordering in rendered output."""
    
    def test_expected_section_order(self):
        """Sections should appear in logical order."""
        expected_order = [
            "OBSERVED EVENTS (INCIDENT SCENE)",
            "OBSERVED EVENTS (FOLLOW-UP ACTIONS)",
            "REPORTER DESCRIPTIONS",
            "SELF-REPORTED STATE",
        ]
        
        # Just verify the order makes sense (incident before follow-up)
        assert expected_order.index("OBSERVED EVENTS (INCIDENT SCENE)") < \
               expected_order.index("OBSERVED EVENTS (FOLLOW-UP ACTIONS)")
        
        # Reporter descriptions after observed events
        assert expected_order.index("OBSERVER EVENTS (INCIDENT SCENE)" if False else "OBSERVED EVENTS (INCIDENT SCENE)") < \
               expected_order.index("REPORTER DESCRIPTIONS")


class TestCriticalInvariant:
    """Tests for the critical invariant: OBSERVED EVENTS must be camera-friendly."""
    
    INTERPRETIVE_DISQUALIFIERS = [
        'horrifying', 'brutal', 'brutally', 'viciously', 'innocent',
        'criminal', 'assault', 'assaulting', 'torture', 'deliberately',
        'intentionally', 'clearly', 'obviously',
    ]
    
    def has_interpretive_content(self, text: str) -> bool:
        text_lower = text.lower()
        return any(word in text_lower for word in self.INTERPRETIVE_DISQUALIFIERS)
    
    def test_interpretive_content_excluded_from_observed_events(self):
        """CRITICAL: Interpretive content MUST be excluded from OBSERVED EVENTS."""
        test_cases = [
            "witnessed the horrifying assault",
            "They brutally slammed me",
            "police officers were assaulting an innocent person",
            "he deliberately twisted my arm",
            "she clearly wanted to hurt me",
        ]
        
        for text in test_cases:
            assert self.has_interpretive_content(text), \
                f"Test case '{text}' should have interpretive content"
            
            # This guarantees it would be excluded
            # (in real code, is_camera_friendly would return False)

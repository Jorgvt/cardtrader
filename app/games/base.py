from abc import ABC, abstractmethod
import re

class BaseGame(ABC):
    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def rarities(self):
        pass

    @property
    @abstractmethod
    def domains(self):
        pass

    @property
    @abstractmethod
    def expansions(self):
        """Map of code to CardTrader expansion ID."""
        pass

    @abstractmethod
    def normalize_name(self, name):
        """Lowercases and removes all non-alphanumeric characters."""
        return re.sub(r'[^a-z0-9]', '', name.lower())

    @abstractmethod
    def is_foil(self, listing):
        """Game-specific foil detection."""
        pass

    @abstractmethod
    def get_domain_property_name(self):
        """Property name in CardTrader for domain/color (e.g., 'riftbound_language' or 'mtg_rarity')."""
        pass

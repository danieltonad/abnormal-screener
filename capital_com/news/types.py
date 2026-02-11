from enum import Enum


class Countries(Enum):
    # CHINA = "CN"
    US = "US" 
    # UK = "GB" 
    # EUROPE = "EU" 
    
    @staticmethod
    def get_countries() -> list:
        return [country for country in Countries]


class EventRating(Enum):
    ONE_STAR = -1
    TWO_STAR = 0
    THREE_STAR = 1
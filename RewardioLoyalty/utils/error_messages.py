from enum import Enum


class Errormessages(Enum):
    
    #invalid data error
    ACCESS_DENIED = "Shop not found or you don't have permission to access it"
    INVALID_DATA = "Invalid data"
    INVALID_REQUEST = "Invalid request"
    INVALID_CREDENTIALS = "Invalid credentials"
    INVALID_TOKEN = "Invalid token"
    INVALID_ID = "Invalid id"
    INVALID_EMAIL = "Invalid email"
    INVALID_PASSWORD = "Invalid password"
    INVALID_PHONE_NUMBER = "Invalid phone number"
    INVALID_ADDRESS = "Invalid address"
    
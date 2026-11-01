"""Status and type values from docs/previous/db-schema.html, shared by the models and the API."""

from enum import StrEnum


class Role(StrEnum):
    HOUSEHOLD = "household"
    VENDOR = "vendor"
    ADMIN = "admin"


class Lang(StrEnum):
    EN = "en"
    HI = "hi"
    GU = "gu"


class RequestStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVISED = "revised"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class StateCategory(StrEnum):
    GENERAL = "general"
    SPECIAL = "special"


class LocationSource(StrEnum):
    MAP_PIN = "map_pin"
    GPS = "gps"
    SEARCH = "search"


class RoofType(StrEnum):
    RCC_FLAT = "rcc_flat"
    SLOPED = "sloped"
    TIN_SHEET = "tin_sheet"
    ASBESTOS = "asbestos"


class BuildingType(StrEnum):
    INDEPENDENT = "independent"
    RWA_GHS = "rwa_ghs"


class InputMethod(StrEnum):
    FORM = "form"
    VOICE = "voice"
    BILL = "bill"


class FilePurpose(StrEnum):
    TERRACE_PHOTO = "terrace_photo"
    ELECTRICITY_BILL = "electricity_bill"
    VOICE_AUDIO = "voice_audio"
    QUOTE_DOCUMENT = "quote_document"
    QUOTE_PDF = "quote_pdf"
    COMPARISON_REPORT = "comparison_report"
    VENDOR_DOCUMENT = "vendor_document"
    LOGO = "logo"
    INSTALLATION_PHOTO = "installation_photo"


class AttachmentKind(StrEnum):
    TERRACE_PHOTO = "terrace_photo"
    ELECTRICITY_BILL = "electricity_bill"
    OTHER = "other"


class SttProvider(StrEnum):
    GROQ_WHISPER = "groq_whisper"
    WEB_SPEECH = "web_speech"


class VoiceLanguage(StrEnum):
    EN = "en"
    HI = "hi"
    GU = "gu"
    AUTO = "auto"


class AssessmentStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class Level(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ObstructionType(StrEnum):
    WATER_TANK = "water_tank"
    STAIRCASE_ROOM = "staircase_room"
    PARAPET = "parapet"
    TREE_SHADE = "tree_shade"
    DISH_ANTENNA = "dish_antenna"
    SOLAR_WATER_HEATER = "solar_water_heater"
    OTHER = "other"


class CalculationScope(StrEnum):
    REQUEST_ESTIMATE = "request_estimate"
    QUOTE_FINANCIALS = "quote_financials"


class QuoteSource(StrEnum):
    FORM = "form"
    UPLOADED_DOCUMENT = "uploaded_document"


class PanelTechnology(StrEnum):
    MONO_PERC = "mono_perc"
    TOPCON = "topcon"
    BIFACIAL = "bifacial"


class InverterType(StrEnum):
    STRING = "string"
    MICRO = "micro"
    HYBRID = "hybrid"


class LineItemType(StrEnum):
    PANELS = "panels"
    INVERTER = "inverter"
    MOUNTING_STRUCTURE = "mounting_structure"
    CABLING = "cabling"
    EARTHING = "earthing"
    LIGHTNING_ARRESTER = "lightning_arrester"
    ACDB_DCDB = "acdb_dcdb"
    NET_METER = "net_meter"
    DISCOM_FEES = "discom_fees"
    INSTALLATION = "installation"
    TRANSPORT = "transport"
    AMC = "amc"
    INSURANCE = "insurance"
    OTHER = "other"


class JobType(StrEnum):
    PHOTO_ASSESS = "photo_assess"
    VOICE_EXTRACT = "voice_extract"
    BILL_EXTRACT = "bill_extract"
    QUOTE_EXTRACT = "quote_extract"
    QUOTE_REVIEW = "quote_review"
    RECOMMEND = "recommend"
    CHAT = "chat"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(StrEnum):
    HIGH = "high"
    LOW = "low"


class OtpPurpose(StrEnum):
    LOGIN = "login"
    VERIFY_PHONE = "verify_phone"

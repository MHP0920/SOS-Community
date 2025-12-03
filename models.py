"""
Copyright (c) 2025 Nexuron
Licensed under the Nexuron Custom License — see LICENSE.
"""
from pydantic import BaseModel, Field, EmailStr, field_validator, StringConstraints
from typing import List, Optional, Annotated
from datetime import datetime
from enum import Enum
from pydantic.functional_validators import AfterValidator
import re

# Regex for Vietnamese + ASCII + Basic Punctuation
# Allows: a-z, A-Z, 0-9, Vietnamese chars, spaces, and common punctuation
SAFE_STRING_REGEX = r"""^[a-zA-Z0-9\s\.,\-\?!:;'"\(\)\[\]\{\}@#\$%&\*\+=_/\\àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]*$"""

def validate_safe_chars(v: str) -> str:
    if not v:
        return v
    if not re.match(SAFE_STRING_REGEX, v):
        raise ValueError("Chứa ký tự không hợp lệ (chỉ chấp nhận tiếng Việt, tiếng Anh, số và dấu câu cơ bản)")
    return v

# --- Domain Specific Types ---
SafeString = Annotated[str, AfterValidator(validate_safe_chars)]
RequestId = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{24}$")]

# User Types
Username = Annotated[SafeString, StringConstraints(max_length=100)]
Password = Annotated[str, StringConstraints(min_length=1)] # Plain text or hash

# Pagination Types
PageNumber = Annotated[int, Field(ge=1)]
PageLimit = Annotated[int, Field(ge=1, le=25)]

# Request Types
ReporterName = Annotated[SafeString, StringConstraints(max_length=100)]
Content = Annotated[SafeString, StringConstraints(max_length=500)]
Address = Annotated[SafeString, StringConstraints(max_length=200)]
PhoneNumber = Annotated[str, StringConstraints(pattern=r"^(09|03|07|08|05)\d{8}$")]
PeopleCount = Annotated[int, Field(ge=0, le=1000)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]

# News Types
Title = Annotated[SafeString, StringConstraints(max_length=100)]
SourceUrl = Annotated[SafeString, StringConstraints(max_length=200)]

# Phone Types
PhoneName = Annotated[SafeString, StringConstraints(max_length=100)]
PhoneDesc = Annotated[SafeString, StringConstraints(max_length=200)]

# Rescue Point Types
RescuePointName = Annotated[SafeString, StringConstraints(max_length=100)]
RescuePointDesc = Annotated[SafeString, StringConstraints(max_length=500)]

class RequestType(str, Enum):
    URGENT_HOSPITAL = "Đi viện gấp"
    SAFE_PLACE = "Đến nơi an toàn"
    SUPPLIES = "Nhu yếu phẩm"
    MEDICAL = "Thiết bị y tế"
    CLOTHES = "Quần áo"
    CUSTOM = "Tự viết yêu cầu riêng"

class RequestStatus(str, Enum):
    PENDING = "Chưa duyệt"
    VERIFIED = "Chưa hỗ trợ"
    SUPPORTED = "Đã hỗ trợ"

class UserRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"

class User(BaseModel):
    username: Username
    password: Password
    role: UserRole = UserRole.MODERATOR

class BaseSOSRequest(BaseModel):
    id: Optional[RequestId] = Field(None, alias="_id")
    username: Optional[Username] = "Vô danh"
    reporter: Optional[ReporterName] = "Vô danh"
    type: RequestType
    phones: List[PhoneNumber]
    content: Content
    total_people: PeopleCount
    address: Address
    lat: Latitude
    lng: Longitude
    status: RequestStatus = RequestStatus.PENDING
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

class SOSRequest(BaseSOSRequest):
    """Strict Model for Public API"""
    # Validation is now handled by Types
    pass

class AdminSOSRequest(BaseSOSRequest):
    """Lenient Model for Admin API"""
    pass

class NewsType(str, Enum):
    INFO = "info"
    WARN = "warn"
    DANGER = "danger"

class BaseNews(BaseModel):
    id: Optional[RequestId] = Field(None, alias="_id")
    title: Title
    content: Content
    type: NewsType = NewsType.INFO
    is_banner: bool = False
    source_url: Optional[SourceUrl] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class News(BaseNews):
    """Strict Model for Public/Community News"""
    pass

class AdminNews(BaseNews):
    pass

class BasePhone(BaseModel):
    id: Optional[RequestId] = Field(None, alias="_id")
    name: PhoneName
    number: PhoneNumber
    description: Optional[PhoneDesc] = None

class Phone(BasePhone):
    pass

class AdminPhone(BasePhone):
    pass

class BaseRescuePoint(BaseModel):
    id: Optional[RequestId] = Field(None, alias="_id")
    name: RescuePointName
    description: RescuePointDesc
    lat: Latitude
    lng: Longitude
    source_url: Optional[SourceUrl] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class RescuePoint(BaseRescuePoint):
    pass

class AdminRescuePoint(BaseRescuePoint):
    pass

class StatusUpdate(BaseModel):
    status: RequestStatus
    username: Username

class BulkDeleteRequest(BaseModel):
    ids: List[RequestId]
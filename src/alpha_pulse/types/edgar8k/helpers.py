from pydantic import BaseModel

class ExtractedUrls(BaseModel):
    url_8k: str
    url_ex99: str
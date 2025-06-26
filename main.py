from fastapi import FastAPI
from settings import settings

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print(settings.TDV_SCREENER_HEADER)
    pass
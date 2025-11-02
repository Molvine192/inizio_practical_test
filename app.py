from fastapi import FastAPI, Response
from pydantic import BaseModel, Field
import httpx, os, csv, io, json

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

class SearchIn(BaseModel):
    query: str = Field(min_length=1)

async def fetch_results(query: str):
    if not SERPAPI_KEY:
        return {"results": []}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                "https://serpapi.com/search.json",
                params={"engine":"google","q":query,"num":10,"hl":"cs","api_key":SERPAPI_KEY}
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError:
        return {"results": []}

    items = []
    for i, it in enumerate(data.get("organic_results", []), start=1):
        items.append({
            "rank": i,
            "title": it.get("title"),
            "url": it.get("link"),
            "snippet": it.get("snippet"),
        })
    return {"results": items}

@app.post("/search")
async def search(inp: SearchIn):
    return await fetch_results(inp.query)

@app.post("/download/json")
async def download_json(inp: SearchIn):
    data = await fetch_results(inp.query)
    blob = json.dumps(data["results"], ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=blob,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=results.json"}
    )

@app.post("/download/csv")
async def download_csv(inp: SearchIn):
    data = await fetch_results(inp.query)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["rank","title","url","snippet"])
    writer.writeheader()
    for row in data["results"]:
        writer.writerow(row)
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=results.csv"}
    )

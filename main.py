import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Tournament, Prediction

app = FastAPI(title="Crypto Prediction Tournaments API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Crypto Prediction Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# Helper to convert Mongo doc
class TournamentOut(BaseModel):
    id: str
    title: str
    asset: str
    start_time: str
    end_time: str
    entry_fee: float
    prize_pool: float
    status: str


@app.post("/api/tournaments", response_model=dict)
def create_tournament(t: Tournament):
    try:
        inserted_id = create_document("tournament", t)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tournaments", response_model=List[TournamentOut])
def list_tournaments(status: str | None = None):
    try:
        filter_q = {"status": status} if status else {}
        docs = get_documents("tournament", filter_q)
        out = []
        for d in docs:
            out.append(TournamentOut(
                id=str(d.get("_id")),
                title=d.get("title"),
                asset=d.get("asset"),
                start_time=d.get("start_time").isoformat() if d.get("start_time") else "",
                end_time=d.get("end_time").isoformat() if d.get("end_time") else "",
                entry_fee=float(d.get("entry_fee", 0)),
                prize_pool=float(d.get("prize_pool", 0)),
                status=d.get("status", "upcoming"),
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predictions", response_model=dict)
def create_prediction(p: Prediction):
    try:
        # verify tournament exists
        try:
            oid = ObjectId(p.tournament_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid tournament id")
        t = db["tournament"].find_one({"_id": oid})
        if not t:
            raise HTTPException(status_code=404, detail="Tournament not found")

        inserted_id = create_document("prediction", p)
        return {"id": inserted_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/predictions", response_model=List[dict])
def list_predictions(tournament_id: str | None = None):
    try:
        q = {"tournament_id": tournament_id} if tournament_id else {}
        docs = get_documents("prediction", q)
        return [
            {
                "id": str(d.get("_id")),
                "tournament_id": d.get("tournament_id"),
                "user": d.get("user"),
                "direction": d.get("direction"),
                "amount": float(d.get("amount", 0)),
                "created_at": d.get("created_at").isoformat() if d.get("created_at") else None,
            }
            for d in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

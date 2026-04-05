# House Divided MVP

## Run locally

1. `pip install -r requirements.txt`
2. `uvicorn app.main:app --reload`

Open: http://127.0.0.1:8000/docs

## Endpoints
- POST /houses
- POST /users
- POST /bills
- GET /houses/{house_id}/balances

## Next
- Stripe billing (later)
- Deploy to Render free hobby web service (later)

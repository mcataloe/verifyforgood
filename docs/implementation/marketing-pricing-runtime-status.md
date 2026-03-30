# Marketing Pricing Runtime Status

## Status

implemented

## Summary

- marketing pricing continues to use the backend-authored `GET /v1/plans` catalog
- local marketing development now expects explicit `VITE_API_BASE_URL` runtime configuration through `frontend/marketing/.env.example`
- local dev CORS expectations now include the marketing origin on `http://localhost:5174`

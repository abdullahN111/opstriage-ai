# 01: Backend Core, Environment Config & Dual-Mode Google Workspace Adapter

Status: resolved

## Scope
- Set up `backend/` with FastAPI, `.env` with the provided Gemini API key, Google OAuth Client ID/Secret, Drive Folder ID (`1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU`), and Sheet ID (`1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek`).
- Build Dual-Mode Workspace Service (`sandbox` and `live` Google OAuth 2.0 flow for Gmail, Drive, and Sheets).
- Seed realistic Recruiter Sandbox inquiries, SOP documents, and initial tracking sheet rows.

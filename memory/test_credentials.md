# Test Credentials

## User Accounts
- **Main user**: `Graffux` / `Thrashpw06!` (production data, real cards)

## Notes
- Older `testuser/testpass` reference removed — that account does not exist in MongoDB.
- For new test runs, register a fresh account via `POST /api/auth/register` with any
  username/password and capture credentials there. The login flow returns the user
  object directly (no JWT), and the frontend persists session via AsyncStorage.

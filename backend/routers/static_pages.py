"""
Static / metadata endpoints: root, health, downloads, privacy policy,
and the public-facing account-deletion page.
No business logic, no DB. Pure responses.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Thrash Kan Kidz Card Collector API"}


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/download/frontend")
async def download_frontend():
    """Download the frontend project as a zip file"""
    zip_path = Path("/app/frontend_build.zip")
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Download file not found")
    return FileResponse(
        path=str(zip_path),
        filename="thrash-kan-kidz-frontend.zip",
        media_type="application/zip",
    )


@router.get("/download/backend")
async def download_backend():
    """Download the backend project as a zip file"""
    zip_path = Path("/app/backend_deploy.zip")
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Download file not found")
    return FileResponse(
        path=str(zip_path),
        filename="thrash-kan-kidz-backend.zip",
        media_type="application/zip",
    )


@router.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thrash Kan Kidz - Privacy Policy</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #e0e0e0; }
        h1 { color: #FFD700; }
        h2 { color: #FFD700; margin-top: 24px; }
        p { line-height: 1.6; }
        a { color: #FFD700; }
    </style>
</head>
<body>
    <h1>Thrash Kan Kidz - Privacy Policy</h1>
    <p><strong>Last Updated: April 14, 2026</strong></p>
    
    <h2>1. Information We Collect</h2>
    <p>When you create an account, we collect your chosen username and password. We do not collect your real name, email address, phone number, or location data.</p>
    
    <h2>2. How We Use Your Information</h2>
    <p>Your username and password are used solely for authentication and to save your game progress, including your card collection, coin balance, and trade history.</p>
    
    <h2>3. Data Storage</h2>
    <p>Your data is stored securely on cloud servers (MongoDB Atlas). Passwords are hashed and never stored in plain text.</p>
    
    <h2>4. In-App Purchases</h2>
    <p>Coin purchases are processed through Google Play Billing. We do not collect or store any payment information. All payment processing is handled by Google.</p>
    
    <h2>5. Third-Party Services</h2>
    <p>We use the following third-party services:</p>
    <ul>
        <li>Google Play Billing for in-app purchases</li>
        <li>MongoDB Atlas for data storage</li>
    </ul>
    
    <h2>6. Children's Privacy</h2>
    <p>Thrash Kan Kidz is not intended for children under 18. We do not knowingly collect information from children under 18.</p>
    
    <h2>7. Data Deletion</h2>
    <p>You may request deletion of your account and all associated data by visiting our <a href="/api/delete-account">Account Deletion page</a>.</p>
    
    <h2>8. Changes to This Policy</h2>
    <p>We may update this Privacy Policy from time to time. Changes will be reflected by the "Last Updated" date above.</p>
    
    <h2>9. Contact Us</h2>
    <p>If you have questions about this Privacy Policy, please contact us through the Google Play Store listing.</p>
</body>
</html>
"""


@router.get("/delete-account", response_class=HTMLResponse)
async def delete_account_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thrash Kan Kidz - Delete Account</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #e0e0e0; }
        h1 { color: #FFD700; }
        p { line-height: 1.6; }
        input { width: 100%; padding: 12px; margin: 8px 0 16px 0; border-radius: 8px; border: 1px solid #444; background: #2a2a4e; color: #fff; font-size: 16px; box-sizing: border-box; }
        button { background: #cc0000; color: #fff; border: none; padding: 14px 24px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%; }
        button:hover { background: #ff0000; }
        .result { margin-top: 20px; padding: 16px; border-radius: 8px; font-weight: bold; text-align: center; }
        .success { background: rgba(76, 175, 80, 0.2); color: #4CAF50; border: 1px solid #4CAF50; }
        .error { background: rgba(255, 59, 48, 0.2); color: #ff6b6b; border: 1px solid #ff6b6b; }
        .warning { background: rgba(255, 215, 0, 0.15); color: #FFD700; border: 1px solid #FFD700; padding: 16px; border-radius: 8px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Delete Your Account</h1>
    <div class="warning">
        <strong>Warning:</strong> This action is permanent and cannot be undone. All your data including your card collection, coins, trade history, and account will be permanently deleted.
    </div>
    <p>Enter your username and password to confirm account deletion:</p>
    <label for="username" style="color: #FFD700;">Username</label>
    <input type="text" id="username" placeholder="Enter your username">
    <label for="password" style="color: #FFD700;">Password</label>
    <input type="password" id="password" placeholder="Enter your password">
    <button onclick="deleteAccount()">Permanently Delete My Account</button>
    <div id="result"></div>
    <script>
        async function deleteAccount() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            if (!username || !password) {
                document.getElementById('result').innerHTML = '<div class="result error">Please enter both username and password.</div>';
                return;
            }
            try {
                const res = await fetch('/api/auth/delete-account', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('result').innerHTML = '<div class="result success">Your account and all associated data have been permanently deleted.</div>';
                } else {
                    document.getElementById('result').innerHTML = '<div class="result error">' + (data.detail || 'Failed to delete account.') + '</div>';
                }
            } catch (e) {
                document.getElementById('result').innerHTML = '<div class="result error">Something went wrong. Please try again.</div>';
            }
        }
    </script>
</body>
</html>
"""

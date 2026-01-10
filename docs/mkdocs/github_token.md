# GitHub Authentication Token

## Overview

The GitHub Authentication Token feature allows you to configure a personal access token from GitHub to avoid rate limiting when the Blender Launcher makes requests to GitHub's API.

## Why Use a GitHub Token?

GitHub limits the number of API requests that can be made without authentication:

- **Without authentication**: 60 requests per hour
- **With authentication**: 5,000 requests per hour

The Blender Launcher uses GitHub's API to:

- Check for new launcher updates
- Download API data files
- Fetch release notes and patch information

If you use the Blender Launcher frequently or check for updates often, you may hit the rate limit. Adding a GitHub token prevents this issue.

## How to Create a GitHub Token

1. **Log in to GitHub**  
   Go to [github.com](https://github.com) and sign in to your account.

2. **Access Developer Settings**  
   - Click on your profile picture in the top right corner
   - Select **Settings**
   - Scroll down and click on **Developer settings** (bottom of the left sidebar)

3. **Create a Personal Access Token**  
   - Click on **Personal access tokens** → **Tokens (classic)**
   - Click **Generate new token** → **Generate new token (classic)**

4. **Configure Token Settings**  
   - **Note**: Enter a descriptive name like "Blender Launcher"
   - **Expiration**: Choose an expiration period (recommended: 90 days or 1 year)
   - **Scopes**: You **don't need to select any scopes** for basic API access
     - The token only needs public read access to GitHub API
     - No repository or user permissions are required

5. **Generate and Copy Token**  
   - Click **Generate token** at the bottom
   - **Important**: Copy the token immediately! GitHub only shows it once
   - The token will look like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## How to Add Token to Blender Launcher

1. Open **Blender Launcher**
2. Click the **Settings** button (gear icon) in the top left
3. Go to the **Connection** tab
4. Scroll down to the **Connection Authentication** section
5. Find the **GitHub Token** field
6. Paste your token into the field
7. Changes are saved automatically **in your system's secure credential manager**

!!! tip
    The token is stored securely in your system's credential manager (Windows Credential Manager, macOS Keychain, or Linux Secret Service), if it fail to save it in the system's credential manager, it will fall back to the user settings file with a warning.

## Token Security

- Your token is stored securely using your system's credential manager:
  - **Windows**: Windows Credential Manager (same place Windows stores passwords)
  - **macOS**: macOS Keychain
  - **Linux**: Secret Service API (gnome-keyring, KWallet, etc.)
  - Falls back to user settings file if system keyring is unavailable
- The token is only sent to `api.github.com` when the launcher checks for updates or fetches UPBGE builds
- **Never share your token** with anyone else
- If you believe your token has been compromised, revoke it on GitHub and create a new one

!!! info
    If your system's keyring is unavailable, the token will fall back to user settings with a warning. This ensures the feature always works, even in restricted environments.

## Revoking a Token

If you need to revoke your token:

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens**
2. Find your "Blender Launcher" token
3. Click **Delete** or **Revoke**
4. Create a new token if needed

## Troubleshooting

### Token Not Working

- Verify the token was copied correctly (no extra spaces)
- Ensure the token hasn't expired
- Check that the token is a **classic token** (fine-grained tokens may have different requirements)

## Additional Resources

- [GitHub Personal Access Tokens Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api)

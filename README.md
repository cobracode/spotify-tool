# Spotify Tool

A simple Python desktop app (Tkinter) to fetch all playlists and Liked Songs from your Spotify account using the Spotify Web API.

## Features
- Login with your Spotify account (OAuth)
- Fetch all playlists and Liked Songs
- Export playlist and track data (CSV/JSON)

## Setup

### 1. Create a Spotify Developer App
1. Go to https://developer.spotify.com/dashboard/applications
2. Click "Create an App"
3. Fill in the app details:
   - App name: "Spotify Tool" (or any name you prefer)
   - App description: "Personal tool for accessing Spotify data"
   - Redirect URI: `http://localhost:8888/callback`
   - Website: (optional)
4. Click "Save"
5. Note your **Client ID** and **Client Secret**

### 2. Set up the Environment
1. Clone this repo and set up the virtual environment:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root:
   ```sh
   cp .env.example .env
   ```

3. Edit the `.env` file and add your Spotify credentials:
   ```
   SPOTIFY_CLIENT_ID=your_actual_client_id_here
   SPOTIFY_CLIENT_SECRET=your_actual_client_secret_here
   ```

## Run
```sh
python main.py
```

## How it Works
- The app uses OAuth2 authentication to securely access your Spotify account
- On first run, it will open your browser for authentication
- After authentication, tokens are cached locally for future use
- The app requests permissions to read your playlists and liked songs

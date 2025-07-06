import tkinter as tk
from tkinter import messagebox
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import webbrowser

# Load environment variables
load_dotenv()

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Scope for accessing user data
SCOPE = 'user-library-read playlist-read-private playlist-read-collaborative'

def authenticate_with_spotify():
    """Authenticate with Spotify using OAuth2"""
    try:
        if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
            messagebox.showerror("Configuration Error", 
                               "Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your .env file")
            return None
        
        # Create Spotify OAuth object
        sp_oauth = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE,
            open_browser=True
        )
        
        # Get cached token or start auth flow
        token_info = sp_oauth.get_cached_token()
        
        if not token_info:
            # Get authorization URL and open browser
            auth_url = sp_oauth.get_authorize_url()
            webbrowser.open(auth_url)
            
            # Show message to user
            messagebox.showinfo("Authentication", 
                              "Please complete authentication in your browser.\n"
                              "You will be redirected back to this application.")
            
            # Get access token
            token_info = sp_oauth.get_access_token()
        
        if token_info:
            # Create Spotify client
            sp = spotipy.Spotify(auth=token_info['access_token'])
            
            # Test the connection by getting user info
            user_info = sp.current_user()
            messagebox.showinfo("Success", 
                              f"Successfully authenticated as {user_info['display_name']}!")
            
            return sp
        else:
            messagebox.showerror("Authentication Failed", 
                               "Failed to authenticate with Spotify. Please try again.")
            return None
            
    except Exception as e:
        messagebox.showerror("Error", f"Authentication error: {str(e)}")
        print(e);
        print(e.traceback);
        return None


def main():
    root = tk.Tk()
    root.title("Spotify Tool")
    root.geometry("400x300")

    label = tk.Label(root, text="Spotify Playlist & Liked Songs Tool", font=("Arial", 14))
    label.pack(pady=20)

    # Variable to store the authenticated Spotify client
    spotify_client = None

    def on_auth_click():
        nonlocal spotify_client
        spotify_client = authenticate_with_spotify()
        if spotify_client:
            # Enable additional buttons after successful authentication
            test_button.config(state=tk.NORMAL)
            test_button.pack(pady=5)

    def test_connection():
        if spotify_client:
            try:
                user_info = spotify_client.current_user()
                playlists = spotify_client.current_user_playlists()
                messagebox.showinfo("Connection Test", 
                                  f"Connected as: {user_info['display_name']}\n"
                                  f"Total playlists: {playlists['total']}")
            except Exception as e:
                messagebox.showerror("Error", f"Connection test failed: {str(e)}")

    auth_button = tk.Button(root, text="Login with Spotify", command=on_auth_click)
    auth_button.pack(pady=10)

    test_button = tk.Button(root, text="Test Connection", command=test_connection, state=tk.DISABLED)

    root.mainloop()


if __name__ == "__main__":
    main()

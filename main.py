import tkinter as tk
from tkinter import messagebox, ttk
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import webbrowser
import json
from datetime import datetime
import glob
import csv

# Load environment variables
load_dotenv()

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Scope for accessing user data
SCOPE = 'user-library-read playlist-read-private playlist-read-collaborative user-modify-playback-state user-read-playback-state playlist-modify-public playlist-modify-private'

def get_cache_filename(username):
    """Generate cache filename for a user"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{username}-liked-songs-{timestamp}.txt"

def get_latest_cache_file(username):
    """Get the latest cache file for a user"""
    pattern = f"{username}-liked-songs-*.txt"
    cache_files = glob.glob(pattern)
    
    if not cache_files:
        return None
    
    # Sort by modification time (newest first)
    cache_files.sort(key=os.path.getmtime, reverse=True)
    return cache_files[0]

def load_liked_songs_from_cache(username):
    """Load liked songs from cache file"""
    cache_file = get_latest_cache_file(username)
    if not cache_file:
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('liked_songs', []), data.get('cached_at', 'Unknown')
    except Exception as e:
        print(f"Error loading cache file {cache_file}: {e}")
        return None

def save_liked_songs_to_cache(username, liked_songs):
    """Save liked songs to cache file"""
    try:
        cache_filename = get_cache_filename(username)
        cache_data = {
            'username': username,
            'liked_songs': liked_songs,
            'cached_at': datetime.now().isoformat(),
            'total_songs': len(liked_songs)
        }
        
        with open(cache_filename, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        return cache_filename
    except Exception as e:
        print(f"Error saving cache file: {e}")
        return None

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

def load_liked_songs_data(spotify_client, force_refresh=False):
    user_info = spotify_client.current_user()
    username = user_info['display_name'].replace(' ', '-') + '-' + user_info['id']
    liked_songs = []
    cache_info = ""
    if not force_refresh:
        cached_data = load_liked_songs_from_cache(username)
        if cached_data:
            liked_songs, cached_at = cached_data
            cache_info = f" (Loaded from cache: {cached_at[:10]})"
            return liked_songs, cache_info, username
    offset = 0
    limit = 50
    while True:
        results = spotify_client.current_user_saved_tracks(limit=limit, offset=offset)
        if not results['items']:
            break
        liked_songs.extend(results['items'])
        offset += limit
    cache_filename = save_liked_songs_to_cache(username, liked_songs)
    if cache_filename:
        cache_info = f" (Fresh data saved to cache: {cache_filename})"
    else:
        cache_info = " (Fresh data from Spotify)"
    return liked_songs, cache_info, username

def export_songs_to_csv(liked_songs, filename='liked-songs-latest.csv'):
    """Export liked songs to CSV file"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(['Song Number', 'Artist', 'Title', 'Duration', 'Popularity', 'Spotify URL', 'Liked Date'])
            
            # Write song data
            for i, item in enumerate(liked_songs, 1):
                track = item['track']
                artist = ', '.join([artist['name'] for artist in track['artists']])
                title = track['name']
                liked_date = item['added_at'][:10]  # YYYY-MM-DD format
                
                # Convert duration from milliseconds to mm:ss format
                duration_ms = track.get('duration_ms', 0)
                duration_minutes = duration_ms // 60000
                duration_seconds = (duration_ms % 60000) // 1000
                duration_formatted = f"{duration_minutes:02d}:{duration_seconds:02d}"
                
                # Get popularity (0-100 scale)
                popularity = track.get('popularity', 0)
                
                # Get Spotify URL
                spotify_url = track.get('external_urls', {}).get('spotify', '')
                
                writer.writerow([i, artist, title, duration_formatted, popularity, spotify_url, liked_date])
        
        return True
    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return False

def display_songs_in_window(liked_songs, scrollable_frame):
    for widget in scrollable_frame.winfo_children():
        widget.destroy()
    for i, item in enumerate(liked_songs, 1):
        track = item['track']
        added_at = item['added_at'][:10]
        song_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=1)
        song_frame.pack(fill=tk.X, pady=2, padx=5)
        number_label = tk.Label(song_frame, text=f"{i}.", width=4, anchor="w")
        number_label.pack(side=tk.LEFT, padx=(5, 0))
        song_info = f"{track['name']} - {', '.join([artist['name'] for artist in track['artists']])}"
        song_label = tk.Label(song_frame, text=song_info, anchor="w", wraplength=500)
        song_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        album_label = tk.Label(song_frame, text=track['album']['name'], anchor="w", fg="gray", font=("Arial", 9))
        album_label.pack(side=tk.LEFT, padx=5)
        date_label = tk.Label(song_frame, text=added_at, anchor="w", fg="gray", font=("Arial", 9))
        date_label.pack(side=tk.RIGHT, padx=5)

def show_liked_songs(spotify_client):
    try:
        liked_window = tk.Toplevel()
        liked_window.title("Liked Songs")
        liked_window.geometry("800x600")
        main_frame = tk.Frame(liked_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        title_label = tk.Label(header_frame, text="Your Liked Songs", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # Variable to store current liked songs data
        current_liked_songs = []
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        summary_label = tk.Label(main_frame, text="", font=("Arial", 12, "bold"))
        summary_label.pack(pady=(0, 10))
        liked_window.update()
        
        # Export button
        export_button = tk.Button(header_frame, text="📄 Export CSV")
        export_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        refresh_button = tk.Button(header_frame, text="🔄 Refresh")
        refresh_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        def export_to_csv():
            if current_liked_songs:
                if export_songs_to_csv(current_liked_songs):
                    messagebox.showinfo("Success", f"Successfully exported {len(current_liked_songs)} songs to 'liked-songs-latest.csv'")
                else:
                    messagebox.showerror("Error", "Failed to export songs to CSV")
            else:
                messagebox.showwarning("Warning", "No songs to export. Please load your liked songs first.")
        
        export_button.config(command=export_to_csv)
        
        def load_and_display_data(force_refresh=False):
            try:
                refresh_button.config(state=tk.DISABLED)
                export_button.config(state=tk.DISABLED)
                # Create a new loading label for each refresh
                loading_label = tk.Label(scrollable_frame, text="Refreshing liked songs from Spotify..." if force_refresh else "Loading liked songs...", font=("Arial", 12))
                loading_label.pack(pady=20)
                liked_window.update()
                liked_songs, cache_info, username = load_liked_songs_data(spotify_client, force_refresh)
                loading_label.destroy()
                # Store the liked songs data for export
                nonlocal current_liked_songs
                current_liked_songs = liked_songs
                display_songs_in_window(liked_songs, scrollable_frame)
                summary_label.config(text=f"Total Liked Songs: {len(liked_songs)}{cache_info}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load liked songs: {str(e)}")
            finally:
                refresh_button.config(state=tk.NORMAL)
                export_button.config(state=tk.NORMAL)
        refresh_button.config(command=lambda: load_and_display_data(force_refresh=True))
        load_and_display_data(force_refresh=False)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            liked_window.destroy()
        liked_window.protocol("WM_DELETE_WINDOW", on_closing)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load liked songs: {str(e)}")

def search_spotify(spotify_client, query, search_type='track', limit=20):
    """Search Spotify for tracks, artists, or albums"""
    try:
        results = spotify_client.search(q=query, type=search_type, limit=limit)
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return None

def get_audio_features(spotify_client, track_ids):
    """Get audio features for tracks"""
    try:
        features = spotify_client.audio_features(track_ids)
        return features
    except Exception as e:
        print(f"Error getting audio features: {e}")
        return None

def create_playlist(spotify_client, name, description="", public=False):
    """Create a new playlist"""
    try:
        user_id = spotify_client.current_user()['id']
        playlist = spotify_client.user_playlist_create(
            user=user_id,
            name=name,
            description=description,
            public=public
        )
        return playlist
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return None

def add_tracks_to_playlist(spotify_client, playlist_id, track_uris):
    """Add tracks to a playlist"""
    try:
        spotify_client.playlist_add_items(playlist_id, track_uris)
        return True
    except Exception as e:
        print(f"Error adding tracks to playlist: {e}")
        return False

def get_current_playback(spotify_client):
    """Get current playback state"""
    try:
        playback = spotify_client.current_playback()
        return playback
    except Exception as e:
        print(f"Error getting playback state: {e}")
        return None

def control_playback(spotify_client, action, track_uri=None):
    """Control playback (play, pause, next, previous)"""
    try:
        if action == 'play':
            if track_uri:
                spotify_client.start_playback(uris=[track_uri])
            else:
                spotify_client.start_playback()
        elif action == 'pause':
            spotify_client.pause_playback()
        elif action == 'next':
            spotify_client.next_track()
        elif action == 'previous':
            spotify_client.previous_track()
        return True
    except Exception as e:
        print(f"Error controlling playback: {e}")
        return False

def show_search_window(spotify_client):
    """Show search window for finding tracks"""
    search_window = tk.Toplevel()
    search_window.title("Spotify Search")
    search_window.geometry("600x500")
    
    main_frame = tk.Frame(search_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Search frame
    search_frame = tk.Frame(main_frame)
    search_frame.pack(fill=tk.X, pady=(0, 10))
    
    search_label = tk.Label(search_frame, text="Search:")
    search_label.pack(side=tk.LEFT)
    
    search_entry = tk.Entry(search_frame, width=40)
    search_entry.pack(side=tk.LEFT, padx=(5, 10))
    
    search_type_var = tk.StringVar(value="track")
    search_type_menu = tk.OptionMenu(search_frame, search_type_var, "track", "artist", "album")
    search_type_menu.pack(side=tk.LEFT, padx=(0, 10))
    
    # Results frame
    results_frame = tk.Frame(main_frame)
    results_frame.pack(fill=tk.BOTH, expand=True)
    
    canvas = tk.Canvas(results_frame)
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    def perform_search():
        query = search_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search term")
            return
        
        # Clear previous results
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        
        # Show loading
        loading_label = tk.Label(scrollable_frame, text="Searching...", font=("Arial", 12))
        loading_label.pack(pady=20)
        search_window.update()
        
        # Perform search
        search_type = search_type_var.get()
        results = search_spotify(spotify_client, query, search_type, limit=20)
        
        loading_label.destroy()
        
        if not results or not results.get(f'{search_type}s', {}).get('items'):
            no_results_label = tk.Label(scrollable_frame, text="No results found", font=("Arial", 12))
            no_results_label.pack(pady=20)
            return
        
        items = results[f'{search_type}s']['items']
        
        for i, item in enumerate(items, 1):
            item_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=1)
            item_frame.pack(fill=tk.X, pady=2, padx=5)
            
            if search_type == 'track':
                # Track info
                track_name = item['name']
                artists = ', '.join([artist['name'] for artist in item['artists']])
                album = item['album']['name']
                
                info_text = f"{i}. {track_name} - {artists} ({album})"
                info_label = tk.Label(item_frame, text=info_text, anchor="w", wraplength=400)
                info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                # Play button
                play_button = tk.Button(item_frame, text="▶️", width=3)
                play_button.config(command=lambda uri=item['uri']: control_playback(spotify_client, 'play', uri))
                play_button.pack(side=tk.RIGHT, padx=5)
                
                # Open in Spotify button
                open_button = tk.Button(item_frame, text="🌐", width=3)
                open_button.config(command=lambda url=item['external_urls']['spotify']: webbrowser.open(url))
                open_button.pack(side=tk.RIGHT, padx=2)
                
            elif search_type == 'artist':
                artist_name = item['name']
                genres = ', '.join(item.get('genres', [])[:3])  # First 3 genres
                
                info_text = f"{i}. {artist_name}"
                if genres:
                    info_text += f" - {genres}"
                
                info_label = tk.Label(item_frame, text=info_text, anchor="w", wraplength=400)
                info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                # Open in Spotify button
                open_button = tk.Button(item_frame, text="🌐", width=3)
                open_button.config(command=lambda url=item['external_urls']['spotify']: webbrowser.open(url))
                open_button.pack(side=tk.RIGHT, padx=5)
                
            elif search_type == 'album':
                album_name = item['name']
                artists = ', '.join([artist['name'] for artist in item['artists']])
                release_date = item.get('release_date', 'Unknown')
                
                info_text = f"{i}. {album_name} - {artists} ({release_date})"
                info_label = tk.Label(item_frame, text=info_text, anchor="w", wraplength=400)
                info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                # Open in Spotify button
                open_button = tk.Button(item_frame, text="🌐", width=3)
                open_button.config(command=lambda url=item['external_urls']['spotify']: webbrowser.open(url))
                open_button.pack(side=tk.RIGHT, padx=5)
    
    search_button = tk.Button(search_frame, text="Search", command=perform_search)
    search_button.pack(side=tk.LEFT, padx=(0, 10))
    
    # Bind Enter key to search
    search_entry.bind('<Return>', lambda e: perform_search())

def show_playback_controls(spotify_client):
    """Show playback control window"""
    control_window = tk.Toplevel()
    control_window.title("Playback Controls")
    control_window.geometry("400x300")
    
    main_frame = tk.Frame(control_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    title_label = tk.Label(main_frame, text="Playback Controls", font=("Arial", 16, "bold"))
    title_label.pack(pady=(0, 20))
    
    # Current track info
    track_info_label = tk.Label(main_frame, text="No track playing", font=("Arial", 12))
    track_info_label.pack(pady=(0, 20))
    
    # Control buttons
    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=20)
    
    prev_button = tk.Button(button_frame, text="⏮️ Previous", width=12, height=2)
    prev_button.pack(side=tk.LEFT, padx=5)
    
    play_pause_button = tk.Button(button_frame, text="▶️ Play", width=12, height=2)
    play_pause_button.pack(side=tk.LEFT, padx=5)
    
    next_button = tk.Button(button_frame, text="⏭️ Next", width=12, height=2)
    next_button.pack(side=tk.LEFT, padx=5)
    
    def update_playback_info():
        """Update current playback information"""
        playback = get_current_playback(spotify_client)
        if playback and playback.get('is_playing'):
            track = playback['item']
            if track:
                track_name = track['name']
                artists = ', '.join([artist['name'] for artist in track['artists']])
                track_info_label.config(text=f"Now Playing: {track_name} - {artists}")
                play_pause_button.config(text="⏸️ Pause")
            else:
                track_info_label.config(text="No track information available")
                play_pause_button.config(text="▶️ Play")
        else:
            track_info_label.config(text="No track playing")
            play_pause_button.config(text="▶️ Play")
    
    def toggle_play_pause():
        """Toggle play/pause"""
        playback = get_current_playback(spotify_client)
        if playback and playback.get('is_playing'):
            control_playback(spotify_client, 'pause')
        else:
            control_playback(spotify_client, 'play')
        control_window.after(1000, update_playback_info)  # Update after 1 second
    
    # Configure button commands
    prev_button.config(command=lambda: [control_playback(spotify_client, 'previous'), 
                                       control_window.after(1000, update_playback_info)])
    play_pause_button.config(command=toggle_play_pause)
    next_button.config(command=lambda: [control_playback(spotify_client, 'next'), 
                                       control_window.after(1000, update_playback_info)])
    
    # Initial update
    update_playback_info()
    
    # Auto-refresh every 5 seconds
    def auto_refresh():
        update_playback_info()
        control_window.after(5000, auto_refresh)
    
    auto_refresh()

def show_playlist_manager(spotify_client):
    """Show playlist management window"""
    playlist_window = tk.Toplevel()
    playlist_window.title("Playlist Manager")
    playlist_window.geometry("700x500")
    
    main_frame = tk.Frame(playlist_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    title_label = tk.Label(main_frame, text="Playlist Manager", font=("Arial", 16, "bold"))
    title_label.pack(pady=(0, 20))
    
    # Create playlist frame
    create_frame = tk.Frame(main_frame)
    create_frame.pack(fill=tk.X, pady=(0, 20))
    
    tk.Label(create_frame, text="Create New Playlist:").pack(side=tk.LEFT)
    
    name_entry = tk.Entry(create_frame, width=30)
    name_entry.pack(side=tk.LEFT, padx=(5, 10))
    
    desc_entry = tk.Entry(create_frame, width=30)
    desc_entry.pack(side=tk.LEFT, padx=(0, 10))
    
    public_var = tk.BooleanVar(value=False)
    public_check = tk.Checkbutton(create_frame, text="Public", variable=public_var)
    public_check.pack(side=tk.LEFT, padx=(0, 10))
    
    def create_new_playlist():
        name = name_entry.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Please enter a playlist name")
            return
        
        description = desc_entry.get().strip()
        public = public_var.get()
        
        playlist = create_playlist(spotify_client, name, description, public)
        if playlist:
            messagebox.showinfo("Success", f"Playlist '{name}' created successfully!")
            name_entry.delete(0, tk.END)
            desc_entry.delete(0, tk.END)
            load_playlists()  # Refresh playlist list
        else:
            messagebox.showerror("Error", "Failed to create playlist")
    
    create_button = tk.Button(create_frame, text="Create", command=create_new_playlist)
    create_button.pack(side=tk.LEFT)
    
    # Playlists list
    playlists_frame = tk.Frame(main_frame)
    playlists_frame.pack(fill=tk.BOTH, expand=True)
    
    canvas = tk.Canvas(playlists_frame)
    scrollbar = ttk.Scrollbar(playlists_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    def load_playlists():
        """Load and display user playlists"""
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        
        try:
            playlists = spotify_client.current_user_playlists(limit=50)
            
            for playlist in playlists['items']:
                playlist_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=1)
                playlist_frame.pack(fill=tk.X, pady=2, padx=5)
                
                # Playlist info
                name = playlist['name']
                owner = playlist['owner']['display_name']
                track_count = playlist['tracks']['total']
                public = "Public" if playlist['public'] else "Private"
                
                info_text = f"{name} by {owner} ({track_count} tracks, {public})"
                info_label = tk.Label(playlist_frame, text=info_text, anchor="w", wraplength=400)
                info_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                
                # Open in Spotify button
                open_button = tk.Button(playlist_frame, text="🌐", width=3)
                open_button.config(command=lambda url=playlist['external_urls']['spotify']: webbrowser.open(url))
                open_button.pack(side=tk.RIGHT, padx=5)
        
        except Exception as e:
            error_label = tk.Label(scrollable_frame, text=f"Error loading playlists: {str(e)}", fg="red")
            error_label.pack(pady=20)
    
    # Load playlists initially
    load_playlists()

def main():
    root = tk.Tk()
    root.title("Spotify Tool")
    root.geometry("400x450")  # Made taller for new buttons

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
            liked_songs_button.config(state=tk.NORMAL)
            search_button.config(state=tk.NORMAL)
            playback_button.config(state=tk.NORMAL)
            playlist_button.config(state=tk.NORMAL)
            test_button.pack(pady=5)
            liked_songs_button.pack(pady=5)
            search_button.pack(pady=5)
            playback_button.pack(pady=5)
            playlist_button.pack(pady=5)

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

    def on_liked_songs_click():
        if spotify_client:
            show_liked_songs(spotify_client)
        else:
            messagebox.showerror("Error", "Please authenticate with Spotify first.")

    def on_search_click():
        if spotify_client:
            show_search_window(spotify_client)
        else:
            messagebox.showerror("Error", "Please authenticate with Spotify first.")

    def on_playback_click():
        if spotify_client:
            show_playback_controls(spotify_client)
        else:
            messagebox.showerror("Error", "Please authenticate with Spotify first.")

    def on_playlist_click():
        if spotify_client:
            show_playlist_manager(spotify_client)
        else:
            messagebox.showerror("Error", "Please authenticate with Spotify first.")

    auth_button = tk.Button(root, text="Login with Spotify", command=on_auth_click)
    auth_button.pack(pady=10)

    test_button = tk.Button(root, text="Test Connection", command=test_connection, state=tk.DISABLED)
    liked_songs_button = tk.Button(root, text="Show Liked Songs", command=on_liked_songs_click, state=tk.DISABLED)
    search_button = tk.Button(root, text="🔍 Search Spotify", command=on_search_click, state=tk.DISABLED)
    playback_button = tk.Button(root, text="🎵 Playback Controls", command=on_playback_click, state=tk.DISABLED)
    playlist_button = tk.Button(root, text="📋 Playlist Manager", command=on_playlist_click, state=tk.DISABLED)

    root.mainloop()


if __name__ == "__main__":
    main()

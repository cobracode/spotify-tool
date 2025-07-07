import tkinter as tk
from tkinter import messagebox, ttk
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import webbrowser
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
SCOPE = 'user-library-read playlist-read-private playlist-read-collaborative user-modify-playback-state user-read-playback-state playlist-modify-public playlist-modify-private user-top-read user-read-recently-played user-read-private'

def get_cache_filename(username):
    """Generate cache filename for a user"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{username}-liked-songs-{timestamp}.csv"

def get_latest_cache_file(username):
    """Get the latest cache file for a user"""
    # First try to find CSV cache files (new format)
    csv_pattern = f"{username}-liked-songs-*.csv"
    csv_files = glob.glob(csv_pattern)
    
    # Also check for old TXT cache files (backward compatibility)
    txt_pattern = f"{username}-liked-songs-*.txt"
    txt_files = glob.glob(txt_pattern)
    
    # Combine both lists
    cache_files = csv_files + txt_files
    
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
        liked_songs = []
        with open(cache_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert CSV row back to Spotify API format
                track_data = {
                    'track': {
                        'id': row.get('Track ID', ''),
                        'name': row['Title'],
                        'artists': [{'name': artist.strip()} for artist in row['Artist'].split(',')],
                        'album': {'name': row.get('Album', 'Unknown')},
                        'duration_ms': (int(row['Duration'].split(':')[0]) * 60 + int(row['Duration'].split(':')[1])) * 1000 if ':' in row['Duration'] else 0,
                        'popularity': int(row['Popularity']) if row['Popularity'].isdigit() else 0,
                        'external_urls': {'spotify': row['Spotify URL']}
                    },
                    'added_at': row['Liked Date'] + 'T00:00:00Z'  # Convert back to ISO format
                }
                liked_songs.append(track_data)
        
        # Get cache timestamp from filename
        cache_timestamp = cache_file.split('-liked-songs-')[1].replace('.csv', '')
        cached_at = f"{cache_timestamp[:4]}-{cache_timestamp[4:6]}-{cache_timestamp[6:8]}"
        
        return liked_songs, cached_at
    except Exception as e:
        print(f"Error loading cache file {cache_file}: {e}")
        return None

def save_liked_songs_to_cache(username, liked_songs):
    """Save liked songs to cache file"""
    try:
        cache_filename = get_cache_filename(username)
        
        with open(cache_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(['Song Number', 'Artist', 'Title', 'Duration', 'Popularity', 'Spotify URL', 'Liked Date', 'Album', 'Track ID'])
            
            # Write song data
            for i, item in enumerate(liked_songs, 1):
                track = item['track']
                artist = ', '.join([artist['name'] for artist in track['artists']])
                title = track['name']
                liked_date = item['added_at'][:10]  # YYYY-MM-DD format
                album = track['album']['name']
                track_id = track.get('id', '')
                
                # Convert duration from milliseconds to mm:ss format
                duration_ms = track.get('duration_ms', 0)
                duration_minutes = duration_ms // 60000
                duration_seconds = (duration_ms % 60000) // 1000
                duration_formatted = f"{duration_minutes:02d}:{duration_seconds:02d}"
                
                # Get popularity (0-100 scale)
                popularity = track.get('popularity', 0)
                
                # Get Spotify URL
                spotify_url = track.get('external_urls', {}).get('spotify', '')
                
                writer.writerow([i, artist, title, duration_formatted, popularity, spotify_url, liked_date, album, track_id])
        
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
            writer.writerow(['Song Number', 'Artist', 'Title', 'Duration', 'Popularity', 'Spotify URL', 'Liked Date', 'Album', 'Track ID'])
            
            # Write song data
            for i, item in enumerate(liked_songs, 1):
                track = item['track']
                artist = ', '.join([artist['name'] for artist in track['artists']])
                title = track['name']
                liked_date = item['added_at'][:10]  # YYYY-MM-DD format
                album = track['album']['name']
                track_id = track.get('id', '')
                
                # Convert duration from milliseconds to mm:ss format
                duration_ms = track.get('duration_ms', 0)
                duration_minutes = duration_ms // 60000
                duration_seconds = (duration_ms % 60000) // 1000
                duration_formatted = f"{duration_minutes:02d}:{duration_seconds:02d}"
                
                # Get popularity (0-100 scale)
                popularity = track.get('popularity', 0)
                
                # Get Spotify URL
                spotify_url = track.get('external_urls', {}).get('spotify', '')
                
                writer.writerow([i, artist, title, duration_formatted, popularity, spotify_url, liked_date, album, track_id])
        
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

def get_artist_genres(spotify_client, artist_ids):
    """Get genres for artists"""
    try:
        artists = spotify_client.artists(artist_ids)
        return {artist['id']: artist.get('genres', []) for artist in artists['artists']}
    except Exception as e:
        print(f"Error getting artist genres: {e}")
        return {}

def analyze_music_taste(spotify_client, tracks, limit=50):
    """Analyze music taste from a list of tracks"""
    if not tracks:
        return None
    
    # Limit analysis to avoid API rate limits
    tracks_to_analyze = tracks[:limit]
    
    # Extract track and artist IDs
    track_ids = [track['track']['id'] for track in tracks_to_analyze if track['track']['id']]
    artist_ids = []
    for track in tracks_to_analyze:
        for artist in track['track']['artists']:
            if artist['id'] not in artist_ids:
                artist_ids.append(artist['id'])
    
    print(f"Analyzing {len(track_ids)} tracks and {len(artist_ids)} artists")
    
    # Try to get audio features, but don't fail if we can't
    audio_features = []
    feature_analysis = {}
    
    try:
        # Get audio features in batches to avoid rate limits
        batch_size = 50  # Spotify allows up to 100, but let's be conservative
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i + batch_size]
            try:
                batch_features = get_audio_features(spotify_client, batch)
                if batch_features:
                    audio_features.extend(batch_features)
                else:
                    print(f"Failed to get audio features for batch {i//batch_size + 1}")
            except Exception as e:
                print(f"Error getting audio features for batch {i//batch_size + 1}: {e}")
        
        # Analyze audio features if we got any
        if audio_features:
            feature_names = ['danceability', 'energy', 'valence', 'tempo', 'acousticness', 
                            'instrumentalness', 'liveness', 'speechiness']
            
            for feature in feature_names:
                values = [f[feature] for f in audio_features if f and f[feature] is not None]
                if values:
                    feature_analysis[feature] = {
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
        else:
            print("No audio features available - continuing with basic analysis")
            
    except Exception as e:
        print(f"Audio features analysis failed: {e}")
        print("Continuing with basic analysis...")
    
    # Get artist genres in batches
    artist_genres = {}
    try:
        for i in range(0, len(artist_ids), batch_size):
            batch = artist_ids[i:i + batch_size]
            try:
                batch_genres = get_artist_genres(spotify_client, batch)
                artist_genres.update(batch_genres)
            except Exception as e:
                print(f"Error getting artist genres for batch {i//batch_size + 1}: {e}")
    except Exception as e:
        print(f"Artist genres analysis failed: {e}")
    
    # Analyze genres
    genre_count = {}
    for track in tracks_to_analyze:
        for artist in track['track']['artists']:
            genres = artist_genres.get(artist['id'], [])
            for genre in genres:
                genre_count[genre] = genre_count.get(genre, 0) + 1
    
    # Get top genres
    top_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Analyze artists
    artist_count = {}
    for track in tracks_to_analyze:
        for artist in track['track']['artists']:
            artist_name = artist['name']
            artist_count[artist_name] = artist_count.get(artist_name, 0) + 1
    
    top_artists = sorted(artist_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Analyze albums
    album_count = {}
    for track in tracks_to_analyze:
        album_name = track['track']['album']['name']
        album_count[album_name] = album_count.get(album_name, 0) + 1
    
    top_albums = sorted(album_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Analyze release years
    year_count = {}
    for track in tracks_to_analyze:
        release_date = track['track']['album']['release_date']
        if release_date:
            year = release_date[:4]  # Extract year
            year_count[year] = year_count.get(year, 0) + 1
    
    top_years = sorted(year_count.items(), key=lambda x: int(x[0]), reverse=True)[:10]
    
    return {
        'audio_features': feature_analysis,
        'top_genres': top_genres,
        'top_artists': top_artists,
        'top_albums': top_albums,
        'top_years': top_years,
        'total_tracks_analyzed': len(tracks_to_analyze),
        'total_tracks': len(tracks)
    }

def get_music_taste_insights(analysis):
    """Generate insights from music taste analysis"""
    if not analysis:
        return []
    
    insights = []
    features = analysis['audio_features']
    
    # Audio features insights (only if available)
    if features:
        # Danceability insights
        if 'danceability' in features:
            dance_avg = features['danceability']['average']
            if dance_avg > 0.7:
                insights.append("🎵 You love danceable music! Your tracks have high danceability scores.")
            elif dance_avg < 0.3:
                insights.append("🎵 You prefer more laid-back, less danceable tracks.")
            else:
                insights.append("🎵 You have a balanced taste in danceability.")
        
        # Energy insights
        if 'energy' in features:
            energy_avg = features['energy']['average']
            if energy_avg > 0.7:
                insights.append("⚡ You're drawn to high-energy, energetic tracks!")
            elif energy_avg < 0.3:
                insights.append("🌙 You prefer calm, low-energy music.")
            else:
                insights.append("⚡ You enjoy a mix of energetic and calm tracks.")
        
        # Valence (happiness) insights
        if 'valence' in features:
            valence_avg = features['valence']['average']
            if valence_avg > 0.7:
                insights.append("😊 You love happy, positive music!")
            elif valence_avg < 0.3:
                insights.append("🎭 You're drawn to more melancholic, emotional tracks.")
            else:
                insights.append("😊 You have a balanced emotional range in your music.")
        
        # Acousticness insights
        if 'acousticness' in features:
            acoustic_avg = features['acousticness']['average']
            if acoustic_avg > 0.7:
                insights.append("🎸 You prefer acoustic and unplugged music.")
            elif acoustic_avg < 0.3:
                insights.append("🎛️ You love electronic and heavily produced music.")
            else:
                insights.append("🎸 You enjoy both acoustic and electronic music.")
        
        # Tempo insights
        if 'tempo' in features:
            tempo_avg = features['tempo']['average']
            if tempo_avg > 140:
                insights.append("🏃 You love fast-paced, high-tempo music!")
            elif tempo_avg < 100:
                insights.append("🐌 You prefer slower, more relaxed tempos.")
            else:
                insights.append("🏃 You enjoy a good mix of tempos.")
    else:
        insights.append("📊 Audio features analysis not available - showing basic insights only.")
    
    # Genre insights
    if analysis['top_genres']:
        top_genre = analysis['top_genres'][0][0]
        insights.append(f"🎼 Your most common genre is: {top_genre}")
    
    # Artist insights
    if analysis['top_artists']:
        top_artist = analysis['top_artists'][0][0]
        insights.append(f"👤 Your most listened artist is: {top_artist}")
    
    # Era insights
    if analysis['top_years']:
        recent_year = analysis['top_years'][0][0]
        oldest_year = analysis['top_years'][-1][0]
        if int(recent_year) - int(oldest_year) > 20:
            insights.append("📅 You have a diverse taste spanning multiple decades!")
        elif int(recent_year) >= 2020:
            insights.append("📅 You mostly listen to recent music.")
        else:
            insights.append("📅 You appreciate music from different eras.")
    
    return insights

def show_music_analysis(spotify_client):
    """Show music taste analysis window"""
    analysis_window = tk.Toplevel()
    analysis_window.title("Music Taste Analysis")
    analysis_window.geometry("800x700")
    
    main_frame = tk.Frame(analysis_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    title_label = tk.Label(main_frame, text="Music Taste Analysis", font=("Arial", 16, "bold"))
    title_label.pack(pady=(0, 20))
    
    # Analysis options frame
    options_frame = tk.Frame(main_frame)
    options_frame.pack(fill=tk.X, pady=(0, 20))
    
    tk.Label(options_frame, text="Analyze:").pack(side=tk.LEFT)
    
    analysis_type_var = tk.StringVar(value="liked_songs")
    analysis_menu = tk.OptionMenu(options_frame, analysis_type_var, 
                                "liked_songs", "recent_tracks", "top_tracks")
    analysis_menu.pack(side=tk.LEFT, padx=(5, 10))
    
    limit_var = tk.IntVar(value=50)
    tk.Label(options_frame, text="Limit:").pack(side=tk.LEFT, padx=(10, 5))
    limit_entry = tk.Entry(options_frame, width=5, textvariable=limit_var)
    limit_entry.pack(side=tk.LEFT, padx=(0, 10))
    
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
    
    def perform_analysis():
        """Perform music taste analysis"""
        # Clear previous results
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        
        # Show loading
        loading_label = tk.Label(scrollable_frame, text="Analyzing your music taste...", font=("Arial", 12))
        loading_label.pack(pady=20)
        analysis_window.update()
        
        try:
            analysis_type = analysis_type_var.get()
            limit = limit_var.get()
            
            # Get tracks based on analysis type
            if analysis_type == "liked_songs":
                tracks, _, _ = load_liked_songs_data(spotify_client, force_refresh=False)
            elif analysis_type == "recent_tracks":
                # Get recently played tracks
                recent = spotify_client.current_user_recently_played(limit=limit)
                tracks = recent['items']
            elif analysis_type == "top_tracks":
                # Get top tracks (short term)
                top_tracks = spotify_client.current_user_top_tracks(limit=limit, offset=0, time_range='short_term')
                tracks = [{'track': track} for track in top_tracks['items']]
            else:
                tracks = []
            
            if not tracks:
                loading_label.config(text="No tracks found for analysis")
                return
            
            # Perform analysis
            analysis = analyze_music_taste(spotify_client, tracks, limit)
            
            if not analysis:
                loading_label.config(text="Error performing analysis")
                return
            
            loading_label.destroy()
            
            # Display insights
            insights = get_music_taste_insights(analysis)
            
            # Insights section
            insights_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=2)
            insights_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
            
            tk.Label(insights_frame, text="🎯 Music Taste Insights", font=("Arial", 14, "bold")).pack(pady=(10, 5))
            
            for insight in insights:
                insight_label = tk.Label(insights_frame, text=f"• {insight}", anchor="w", wraplength=700)
                insight_label.pack(anchor="w", padx=10, pady=2)
            
            tk.Label(insights_frame, text=f"\nAnalyzed {analysis['total_tracks_analyzed']} tracks out of {analysis['total_tracks']} total", 
                    font=("Arial", 10, "italic")).pack(pady=(10, 10))
            
            # Audio features section
            if analysis['audio_features']:
                features_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=2)
                features_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
                
                tk.Label(features_frame, text="📊 Audio Features Analysis", font=("Arial", 14, "bold")).pack(pady=(10, 5))
                
                features_data = analysis['audio_features']
                feature_names = {
                    'danceability': 'Danceability',
                    'energy': 'Energy',
                    'valence': 'Happiness',
                    'tempo': 'Tempo (BPM)',
                    'acousticness': 'Acousticness',
                    'instrumentalness': 'Instrumentalness',
                    'liveness': 'Liveness',
                    'speechiness': 'Speechiness'
                }
                
                for feature, display_name in feature_names.items():
                    if feature in features_data:
                        data = features_data[feature]
                        if feature == 'tempo':
                            value_text = f"{data['average']:.0f} BPM"
                        else:
                            value_text = f"{data['average']:.2f}"
                        
                        feature_label = tk.Label(features_frame, 
                                               text=f"{display_name}: {value_text}", 
                                               anchor="w")
                        feature_label.pack(anchor="w", padx=10, pady=2)
            
            # Top genres section
            if analysis['top_genres']:
                genres_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=2)
                genres_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
                
                tk.Label(genres_frame, text="🎼 Top Genres", font=("Arial", 14, "bold")).pack(pady=(10, 5))
                
                for i, (genre, count) in enumerate(analysis['top_genres'][:10], 1):
                    genre_label = tk.Label(genres_frame, 
                                         text=f"{i}. {genre.title()} ({count} tracks)", 
                                         anchor="w")
                    genre_label.pack(anchor="w", padx=10, pady=2)
            
            # Top artists section
            if analysis['top_artists']:
                artists_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=2)
                artists_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
                
                tk.Label(artists_frame, text="👤 Top Artists", font=("Arial", 14, "bold")).pack(pady=(10, 5))
                
                for i, (artist, count) in enumerate(analysis['top_artists'][:10], 1):
                    artist_label = tk.Label(artists_frame, 
                                          text=f"{i}. {artist} ({count} tracks)", 
                                          anchor="w")
                    artist_label.pack(anchor="w", padx=10, pady=2)
            
            # Top albums section
            if analysis['top_albums']:
                albums_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=2)
                albums_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
                
                tk.Label(albums_frame, text="💿 Top Albums", font=("Arial", 14, "bold")).pack(pady=(10, 5))
                
                for i, (album, count) in enumerate(analysis['top_albums'][:10], 1):
                    album_label = tk.Label(albums_frame, 
                                         text=f"{i}. {album} ({count} tracks)", 
                                         anchor="w")
                    album_label.pack(anchor="w", padx=10, pady=2)
            
            # Top years section
            if analysis['top_years']:
                years_frame = tk.Frame(scrollable_frame, relief=tk.RAISED, borderwidth=2)
                years_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
                
                tk.Label(years_frame, text="📅 Top Release Years", font=("Arial", 14, "bold")).pack(pady=(10, 5))
                
                for i, (year, count) in enumerate(analysis['top_years'][:10], 1):
                    year_label = tk.Label(years_frame, 
                                        text=f"{i}. {year} ({count} tracks)", 
                                        anchor="w")
                    year_label.pack(anchor="w", padx=10, pady=2)
        
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            print(f"DEBUG: {error_msg}")
            loading_label.config(text=error_msg)
    
    analyze_button = tk.Button(options_frame, text="Analyze", command=perform_analysis)
    analyze_button.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add test button for debugging
    def test_api_calls():
        """Test individual API calls to identify the issue"""
        try:
            # Test 1: Get user info
            user_info = spotify_client.current_user()
            print(f"✓ User info: {user_info['display_name']}")
            
            # Test 2: Get liked songs
            liked_songs = spotify_client.current_user_saved_tracks(limit=5)
            print(f"✓ Liked songs: {len(liked_songs['items'])} tracks")
            
            # Test 3: Get audio features for one track
            if liked_songs['items']:
                track_id = liked_songs['items'][0]['track']['id']
                features = spotify_client.audio_features([track_id])
                print(f"✓ Audio features: {len(features)} features retrieved")
            
            # Test 4: Get artist info
            if liked_songs['items']:
                artist_id = liked_songs['items'][0]['track']['artists'][0]['id']
                artists = spotify_client.artists([artist_id])
                print(f"✓ Artist info: {artists['artists'][0]['name']}")
            
            # Test 5: Get top tracks
            try:
                top_tracks = spotify_client.current_user_top_tracks(limit=5)
                print(f"✓ Top tracks: {len(top_tracks['items'])} tracks")
            except Exception as e:
                print(f"✗ Top tracks failed: {e}")
            
            # Test 6: Get recently played
            try:
                recent = spotify_client.current_user_recently_played(limit=5)
                print(f"✓ Recently played: {len(recent['items'])} tracks")
            except Exception as e:
                print(f"✗ Recently played failed: {e}")
                
            messagebox.showinfo("API Test", "Check console for detailed results")
            
        except Exception as e:
            print(f"✗ API test failed: {e}")
            messagebox.showerror("API Test Error", str(e))
    
    test_button = tk.Button(options_frame, text="🔧 Test APIs", command=test_api_calls)
    test_button.pack(side=tk.LEFT, padx=(0, 10))
    
    # Add export button
    def export_analysis():
        """Export analysis results to CSV"""
        try:
            analysis_type = analysis_type_var.get()
            limit = limit_var.get()
            
            # Get tracks
            if analysis_type == "liked_songs":
                tracks, _, _ = load_liked_songs_data(spotify_client, force_refresh=False)
            elif analysis_type == "recent_tracks":
                recent = spotify_client.current_user_recently_played(limit=limit)
                tracks = recent['items']
            elif analysis_type == "top_tracks":
                top_tracks = spotify_client.current_user_top_tracks(limit=limit, offset=0, time_range='short_term')
                tracks = [{'track': track} for track in top_tracks['items']]
            else:
                tracks = []
            
            if not tracks:
                messagebox.showwarning("Warning", "No tracks to analyze")
                return
            
            # Perform analysis
            analysis = analyze_music_taste(spotify_client, tracks, limit)
            if not analysis:
                messagebox.showerror("Error", "Failed to perform analysis")
                return
            
            # Export to CSV
            filename = f"music_analysis_{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write summary
                writer.writerow(['Music Taste Analysis Summary'])
                writer.writerow(['Analysis Type', analysis_type])
                writer.writerow(['Tracks Analyzed', analysis['total_tracks_analyzed']])
                writer.writerow(['Total Tracks', analysis['total_tracks']])
                writer.writerow([])
                
                # Write audio features
                writer.writerow(['Audio Features'])
                writer.writerow(['Feature', 'Average', 'Min', 'Max'])
                for feature, data in analysis['audio_features'].items():
                    writer.writerow([feature, f"{data['average']:.3f}", f"{data['min']:.3f}", f"{data['max']:.3f}"])
                writer.writerow([])
                
                # Write top genres
                writer.writerow(['Top Genres'])
                writer.writerow(['Rank', 'Genre', 'Count'])
                for i, (genre, count) in enumerate(analysis['top_genres'], 1):
                    writer.writerow([i, genre, count])
                writer.writerow([])
                
                # Write top artists
                writer.writerow(['Top Artists'])
                writer.writerow(['Rank', 'Artist', 'Count'])
                for i, (artist, count) in enumerate(analysis['top_artists'], 1):
                    writer.writerow([i, artist, count])
                writer.writerow([])
                
                # Write top albums
                writer.writerow(['Top Albums'])
                writer.writerow(['Rank', 'Album', 'Count'])
                for i, (album, count) in enumerate(analysis['top_albums'], 1):
                    writer.writerow([i, album, count])
                writer.writerow([])
                
                # Write top years
                writer.writerow(['Top Release Years'])
                writer.writerow(['Rank', 'Year', 'Count'])
                for i, (year, count) in enumerate(analysis['top_years'], 1):
                    writer.writerow([i, year, count])
            
            messagebox.showinfo("Success", f"Analysis exported to '{filename}'")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export analysis: {str(e)}")
    
    export_button = tk.Button(options_frame, text="📄 Export CSV", command=export_analysis)
    export_button.pack(side=tk.LEFT)

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
    root.geometry("400x500")  # Made taller for new button

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
            analysis_button.config(state=tk.NORMAL)
            test_button.pack(pady=5)
            liked_songs_button.pack(pady=5)
            search_button.pack(pady=5)
            playback_button.pack(pady=5)
            playlist_button.pack(pady=5)
            analysis_button.pack(pady=5)

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

    def on_analysis_click():
        if spotify_client:
            show_music_analysis(spotify_client)
        else:
            messagebox.showerror("Error", "Please authenticate with Spotify first.")

    auth_button = tk.Button(root, text="Login with Spotify", command=on_auth_click)
    auth_button.pack(pady=10)

    test_button = tk.Button(root, text="Test Connection", command=test_connection, state=tk.DISABLED)
    liked_songs_button = tk.Button(root, text="Show Liked Songs", command=on_liked_songs_click, state=tk.DISABLED)
    search_button = tk.Button(root, text="🔍 Search Spotify", command=on_search_click, state=tk.DISABLED)
    playback_button = tk.Button(root, text="🎵 Playback Controls", command=on_playback_click, state=tk.DISABLED)
    playlist_button = tk.Button(root, text="📋 Playlist Manager", command=on_playlist_click, state=tk.DISABLED)
    analysis_button = tk.Button(root, text="📊 Music Taste Analysis", command=on_analysis_click, state=tk.DISABLED)

    root.mainloop()


if __name__ == "__main__":
    main()

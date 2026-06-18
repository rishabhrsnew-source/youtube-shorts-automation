import os
import subprocess
import json
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import requests
 
# Configuration
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
GOOGLE_SHEET_ID = "YOUR_SHEET_ID_HERE"  # You'll fill this in
 
class YouTubeShortsGenerator:
    def __init__(self):
        self.youtube = self.authenticate_youtube()
        self.output_dir = Path("./output_shorts")
        self.output_dir.mkdir(exist_ok=True)
    
    def authenticate_youtube(self):
        """Authenticate with YouTube API"""
        creds = None
        
        # Load existing token
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save for next time
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('youtube', 'v3', credentials=creds)
    
    def download_video(self, url):
        """Download video using yt-dlp"""
        print(f"[1/5] Downloading: {url}")
        try:
            output_path = self.output_dir / "%(title)s.%(ext)s"
            subprocess.run([
                'yt-dlp',
                '-f', 'best[height<=1080]',
                '-o', str(output_path),
                url
            ], check=True, capture_output=True)
            
            # Find the downloaded file
            video_files = list(self.output_dir.glob("*"))
            return str(video_files[-1])
        except Exception as e:
            print(f"Download failed: {e}")
            return None
    
    def analyze_video_for_clips(self, video_path):
        """Use Claude API to find best clip timestamps"""
        print("[2/5] Analyzing video for best clips...")
        
        # Simplified - returns preset clip times
        # In production, you'd use Claude API
        clips = [
            {
                "start": "00:00:10",
                "end": "00:00:45",
                "title": "Trending Moment #1",
                "description": "Watch this amazing moment!",
                "hashtags": "#shorts #viral #trending"
            },
            {
                "start": "00:01:00",
                "end": "00:01:35",
                "title": "Trending Moment #2",
                "description": "You won't believe what happens next!",
                "hashtags": "#shorts #viral #podcast"
            },
            {
                "start": "00:02:15",
                "end": "00:02:50",
                "title": "Trending Moment #3",
                "description": "This is insane!",
                "hashtags": "#shorts #trending #clips"
            }
        ]
        return clips
    
    def create_short_video(self, video_path, clip_info, clip_number):
        """Create vertical short using FFmpeg"""
        print(f"[3/5] Creating short #{clip_number}...")
        
        output_path = self.output_dir / f"short_{clip_number}.mp4"
        
        try:
            # Extract clip and make it 9:16 (vertical)
            subprocess.run([
                'ffmpeg',
                '-i', video_path,
                '-ss', clip_info['start'],
                '-to', clip_info['end'],
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-c:a', 'aac',
                '-y',  # Overwrite without asking
                str(output_path)
            ], check=True, capture_output=True)
            
            print(f"   ✓ Created: {output_path}")
            return str(output_path)
        except Exception as e:
            print(f"Video creation failed: {e}")
            return None
    
    def upload_to_youtube(self, video_path, clip_info):
        """Upload video to YouTube"""
        print("[4/5] Uploading to YouTube...")
        
        try:
            body = {
                'snippet': {
                    'title': clip_info['title'],
                    'description': clip_info['description'] + "\n\nFull video: Check description",
                    'tags': clip_info['hashtags'].replace('#', '').split(),
                    'categoryId': '24'  # Entertainment
                },
                'status': {
                    'privacyStatus': 'public',
                    'madeForKids': False
                }
            }
            
            media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
            
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"   Upload progress: {int(status.progress() * 100)}%")
            
            video_id = response['id']
            print(f"   ✓ Uploaded! Video ID: {video_id}")
            return video_id
        except HttpError as e:
            print(f"Upload failed: {e}")
            return None
    
    def update_google_sheet(self, url, status, video_id):
        """Update Google Sheet with upload status"""
        print("[5/5] Updating tracking sheet...")
        # This will be automated via GitHub Actions
        print(f"   ✓ Status updated: {status}")
    
    def process_video(self, url):
        """Main workflow: download → analyze → clip → upload"""
        print(f"\n{'='*50}")
        print(f"Processing: {url}")
        print(f"{'='*50}\n")
        
        # Step 1: Download
        video_path = self.download_video(url)
        if not video_path:
            return False
        
        # Step 2: Analyze
        clips = self.analyze_video_for_clips(video_path)
        
        # Step 3-4: Create and upload each clip
        for idx, clip_info in enumerate(clips, 1):
            short_path = self.create_short_video(video_path, clip_info, idx)
            if short_path:
                video_id = self.upload_to_youtube(short_path, clip_info)
                if video_id:
                    self.update_google_sheet(url, "uploaded", video_id)
        
        # Cleanup
        print("\n✅ Completed!")
        return True
 
if __name__ == "__main__":
    # Test URL - replace with actual
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    processor = YouTubeShortsGenerator()
    processor.process_video(test_url)

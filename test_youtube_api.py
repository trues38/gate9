from youtube_transcript_api import YouTubeTranscriptApi
import sys

print(f"Python Executable: {sys.executable}")
print(f"Importing YouTubeTranscriptApi...")

try:
    print(f"Module File: {sys.modules['youtube_transcript_api'].__file__}")
    
    # Try instantiating and finding transcript
    video_id = "0dSIgvN4RDg"
    print(f"Instantiating YouTubeTranscriptApi()...")
    api = YouTubeTranscriptApi()
    print(f"Calling api.list('{video_id}')...")
    transcript_list = api.list(video_id)
    
    print("Finding transcript (ko, en)...")
    try:
        transcript = transcript_list.find_transcript(['ko', 'en'])
    except:
        transcript = transcript_list.find_transcript(['ko', 'en', 'ja', 'zh-Hans', 'zh-Hant'])
        
    data = transcript.fetch()
    print("✅ Success! Fetched transcript.")
    print(f"First 100 chars: {str(data)[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")

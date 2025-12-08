from youtube_transcript_api import YouTubeTranscriptApi
import sys

def debug_type():
    video_id = "0dSIgvN4RDg" # Sampro video
    print(f"Fetching {video_id}...")
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript(['ko', 'en'])
        data = transcript.fetch()
        
        print(f"Type of data: {type(data)}")
        if len(data) > 0:
            item = data[0]
            print(f"Type of item: {type(item)}")
            print(f"Attributes of item: {dir(item)}")
            
            # Try accessing text
            try:
                print(f"item.text: {item.text}")
            except:
                print("item.text failed")
                
            try:
                print(f"item['text']: {item['text']}")
            except Exception as e:
                print(f"item['text'] failed: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_type()

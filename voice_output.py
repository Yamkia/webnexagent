import sys
import pyaudio
from deepgram import DeepgramClient, SpeakOptions
import config
from shared_events import interrupt_playback_event

def speak_text(text: str):
    """Converts text to speech using Deepgram and plays it back through the speakers."""
    if not text:
        return

    p = None
    stream = None

    try:
        # --- Download Phase ---
        # First, we download the entire audio stream and buffer it in memory.
        # This adds a small amount of latency but is far more robust against
        # network jitter and buffer underruns, which can cause static and clicks.
        deepgram = DeepgramClient(config.DEEPGRAM_API_KEY)
        options = SpeakOptions(
            model="aura-asteria-en",
            encoding="linear16",
            sample_rate=16000
        )
        speak_stream = deepgram.speak.v("1").stream({"text": text}, options)

        audio_data = bytearray()
        if speak_stream and hasattr(speak_stream, 'stream'):
            for chunk in speak_stream.stream:
                if chunk:
                    audio_data.extend(bytes(chunk))
        
        if not audio_data:
            print("--- TTS Warning ---: Received no audio data from Deepgram.", file=sys.stderr)
            return

        # --- Playback Phase ---
        # Now, play the complete audio data from the memory buffer.
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000, # Must match the sample_rate requested from Deepgram
                        output=True)

        # Play audio in chunks to allow for interruption (barge-in).
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            # If the interrupt event is set by the listening thread, stop talking.
            if interrupt_playback_event.is_set():
                print("\nINFO: Playback interrupted by user.")
                break
            stream.write(audio_data[i:i+chunk_size])

        # This check prevents a long, silent pause if the user interrupts early.
        if not interrupt_playback_event.is_set():
            # Wait for the stream to finish playing all buffered data
            stream.stop_stream()

    except Exception as e:
        print(f"\n--- TTS Playback Error ---", file=sys.stderr)
        print(f"Could not play audio: {e}", file=sys.stderr)
        print("Please ensure your audio output device is working correctly.", file=sys.stderr)
        # As a fallback, just print the text if TTS fails, so the user still gets a response.
        print(f"Agent (audio fallback): {text}")

    finally:
        if stream:
            stream.close()
        if p:
            p.terminate()
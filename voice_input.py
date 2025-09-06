import asyncio
import sys
import pyaudio
import keyboard
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

from shared_events import interrupt_playback_event
import config

class _SharedState:
    """A simple mutable class to share state between the hotkey callback and the async loop."""
    is_muted = False

def _toggle_mute():
    """Toggles the mute state and prints the current status to the console."""
    _SharedState.is_muted = not _SharedState.is_muted
    status = "MUTED" if _SharedState.is_muted else "UNMUTED"
    # Write over the "Listening..." line without adding a newline. Add padding to clear the line.
    sys.stdout.write(f"\rINFO: --- {status} --- (Press 'm' to toggle)        ")
    sys.stdout.flush()

def _get_deepgram_client():
    """Initializes the Deepgram client."""
    return DeepgramClient(config.DEEPGRAM_API_KEY)

def _get_microphone_stream():
    """Opens a microphone stream using PyAudio."""
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024
    )
    return audio, stream

def _create_deepgram_connection(deepgram: DeepgramClient):
    """Creates a live transcription connection to Deepgram."""
    try:
        dg_connection = deepgram.listen.asynclive.v("1")
        return dg_connection
    except Exception as e:
        print(f"Could not open connection to Deepgram: {e}")
        return None

async def _configure_and_connect(dg_connection, queue: asyncio.Queue):
    """Configures the Deepgram connection options and registers event handlers."""
    options = LiveOptions(
        model="nova-2",
        language="en-US",
        smart_format=True,
        encoding="linear16",
        channels=1,
        sample_rate=16000,
        # We use interim_results=False and endpointing to get complete utterances.
        # 'endpointing' detects the end of speech. 300ms is a good starting value.
        # For barge-in, we enable interim_results. The first interim result will
        # trigger the interruption.
        endpointing=300,
        interim_results=True
    )

    # Event handler for receiving a transcript
    async def on_message(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        if len(transcript) > 0:
            # If we get any transcript (even an interim one), signal an interruption.
            if not interrupt_playback_event.is_set():
                interrupt_playback_event.set()

            # When a *final* transcript is received, put it in the queue to be returned.
            if result.is_final:
                await queue.put(transcript)

    # Event handler for errors
    async def on_error(self, error, **kwargs):
        print(f"Deepgram Error: {error}")

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    await dg_connection.start(options)
    return dg_connection

async def _microphone_sender(dg_connection, stream):
    """Reads audio from the microphone and sends it to Deepgram."""
    try:
        while True:
            # Read data from the stream to prevent the buffer from overflowing, even when muted.
            data = stream.read(1024, exception_on_overflow=False)
            if not _SharedState.is_muted:
                await dg_connection.send(data)
    except asyncio.CancelledError:
        # This is expected when the main function decides to stop listening.
        pass
    except Exception as e:
        print(f"Error while sending audio: {e}")

async def get_voice_input():
    """
    Listens to the microphone for a single utterance and returns the transcribed text.
    """
    # Reset mute state for each new listening session
    _SharedState.is_muted = False

    # Create a new queue for each call. This is crucial to avoid event loop conflicts
    # when this function is called multiple times, as `asyncio.run()` creates a new
    # event loop for each execution.
    transcription_queue = asyncio.Queue()

    deepgram = _get_deepgram_client()
    dg_connection = await _configure_and_connect(_create_deepgram_connection(deepgram), transcription_queue)
    if not dg_connection:
        return None

    audio, stream = _get_microphone_stream()

    # Register the hotkey for muting.
    try:
        keyboard.add_hotkey('m', _toggle_mute)
    except Exception as e:
        # This can happen on some systems (e.g., without a display server or permissions)
        print(f"\nWARNING: Could not register mute hotkey 'm'. Mute functionality will be disabled. Error: {e}")

    print("INFO: Listening... (speak and then pause for a moment, press 'm' to mute/unmute)")

    # Run the microphone sender as a background task
    sender_task = asyncio.create_task(_microphone_sender(dg_connection, stream))

    try:
        # Wait for a transcript to be added to the queue.
        transcript = await transcription_queue.get()
        return transcript
    finally:
        # Clean up resources
        try:
            keyboard.remove_hotkey('m')
        except (KeyError, Exception):
            # Ignore if hotkey was not set or already removed
            pass
        # Clear the mute status line from the console before the next prompt
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        sender_task.cancel()
        await dg_connection.finish()
        stream.stop_stream()
        stream.close()
        audio.terminate()
        # The queue is local and will be garbage collected, so no manual clearing is needed.

def run_transcription_loop():
    """
    A simple helper to run the async get_voice_input function.
    This is the main entry point to be called from main.py.
    """
    try:
        return asyncio.run(get_voice_input())
    except KeyboardInterrupt:
        print("\nExiting.")
        return None
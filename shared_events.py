import threading

# An event to signal that the agent's text-to-speech playback should be interrupted.
interrupt_playback_event = threading.Event()
from audio_player import AudioManager
from azure_text_to_speech import AzureTTSManager

class TTSManager:
    audio_manager = AudioManager()

    def __init__(self):
        self.azuretts_manager = AzureTTSManager()

        file_path = self.azuretts_manager.text_to_audio("Chat God App is now running!")
        self.audio_manager.play_audio(file_path, True, True, True)

    def text_to_audio(self, text, voice_name, voice_style):
        tts_file = self.azuretts_manager.text_to_audio(text, voice_name, voice_style)
        self.audio_manager.play_audio(tts_file, True, True, True)

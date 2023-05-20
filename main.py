from voicevox import Client
import asyncio
import sounddevice as sd
import soundfile as sf
import requests
import pyaudio
import wave
import keyboard
import openai
import threading
import sys
import subprocess
ListOfDependancies = ["voicevox-client", "sounddevice", "soundfile", "requests", "pyaudio", "keyboard", "openai"]
DoDependacyCheck = False # Checks for missing dependacies and installs, toggle this off for faster startup if you have already installed dependancies previously.
TextOnlyMode = False # Toggles off voice recording
#
# MAKE SURE YOU HAVE VOICEVOX DOWNLOADED AND OPEN ON YOUR PC
# YOU CAN FIND IT HERE, https://voicevox.hiroshiba.jp/product/nekotsuka_bi/
# PICK THE CORRECT VERSION FOR YOU OPERATING SYSTEM AND ALSO IF YOU HAVE AN AMD GPU SELECT THE CPU ONE INSTEAD OF GPU
# ONCE DOWNLOADED INSTALL AND IGNORE PC WARNING BECAUSE
# THE PC IS JUST BEING RACIST AGAINST THE JAPANESE
# NEXT OPEN IT AND KEEP IT OPEN WHILST RUNNING THIS PROGRAM
if DoDependacyCheck:
    print("Installing Dependancies!")
    for x in ListOfDependancies:
        # implement pip as a subprocess:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', x])
        print("Installed " + x)
    #
    print("\n\n\n")




# Configuration parameters
chunk_size = 1024  # Buffer size for recording
sample_format = pyaudio.paInt16
channels = 1
RecordKey = "v"
sampling_rate = 44100
record_seconds = 10  # Maximum recording duration in seconds
frames = []  # List to store the audio frames
is_recording = False
SpeakerID = 14 # The character speaking
filename = "recorded_audio.wav"  # Output filename

api_url = "https://api-free.deepl.com/v2/translate"# DeepL API endpoint

api_key = "" #  DeepL API key... Put your api key here. Can be found at https://www.deepl.com/pro/change-plan#developer
openai.api_key = ""  # Replace with your Whisper API key, can be found here: https://platform.openai.com/account/api-keys





# Get available input devices
input_devices = sd.query_devices()
output_devices = sd.query_devices()
input_devices = [device["name"] for device in input_devices if device["max_input_channels"] > 0]
output_devices = [device["name"] for device in output_devices if device["max_output_channels"] > 0]
if not input_devices:
    print("No input devices available.")
    sys.exit(1)
if not output_devices:
    print("No output devices available.")
    sys.exit(1)

# Prompt user to select an input device
print("Available input devices:")
for i, device in enumerate(input_devices):
    print(f"{i + 1}. {device}")
print()
while True:
    input_device_index = input("Enter the number corresponding to the desired input device: ")
    try:
        input_device_index = int(input_device_index) - 1
        if input_device_index < 0 or input_device_index >= len(input_devices):
            raise ValueError
        break
    except ValueError:
        print("Invalid input device selection.")


# Prompt user to select an output device

print("Available output devices:")
for i, device in enumerate(output_devices):
    print(f"{i + 1}. {device}")
print()
while True:
    output_device_index = input("Enter the number corresponding to the desired output device: ")
    try:
        output_device_index = int(output_device_index) - 1
        if output_device_index < 0 or output_device_index >= len(output_devices):
            raise ValueError
        break
    except ValueError:
        print("Invalid output device selection.")


selected_input_device = input_device_index
selected_output_device = output_device_index



def play_audio(audio_file):
    try:
        data, fs = sf.read(audio_file, dtype='float32')
        sd.play(data, fs, device=selected_output_device) # 20 is my default headphones and 22 is my virtal cable
        sd.wait()
    except Exception as e:
        print(f"Error playing audio: {e}")



async def GenerateSpeechFile(speechtext):
    try:
        async with Client() as client:

            audio_query = await client.create_audio_query(speechtext, speaker=SpeakerID)
            audio_query.volume_scale = 2.0
            audio_query.intonation_scale = 1.5
            audio_query.pre_phoneme_length = 1.0
            audio_query.post_phoneme_length = 1.0
            audio_query.output_sampling_rate = 44100
            with open("voice.wav", "wb") as f:
                f.write(await audio_query.synthesis(speaker=SpeakerID))
            print("Created Speech file!")
            play_audio("voice.wav")
    except Exception as e:
        print(f"Error generating speech file: {e}")

def translate_text(text):
    params = {
        "auth_key": api_key,
        "text": text,
        "target_lang": "JA"  # JA represents Japanese language
    }
    try:
        response = requests.post(api_url, data=params)
        translated_text = response.json()["translations"][0]["text"]
        print(f"Translated Text: {translated_text}")
        asyncio.run(GenerateSpeechFile(translated_text))
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {e}")

def transcribe_audio():
    print("Transcribing audio...")
    audio_file = open(filename, "rb")
    try:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    except:
        return print("Failed getting transcript")
    
    
    if(len(transcript.text) > 0):
        print("Transcription:\n" + transcript.text)
        translate_text(transcript.text)
    else:
        print("Nothing was said so not translating!")

def record_audio():
    global frames, is_recording
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=sample_format,
        channels=channels,
        rate=sampling_rate,
        frames_per_buffer=chunk_size,
        input=True,
        input_device_index=selected_input_device
    )
    print("Recording started...")
    is_recording = True
    while is_recording:
        data = stream.read(chunk_size)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    audio.terminate()
    print("Recording finished!")
    save_audio(frames)
    transcribe_audio()

def save_audio(frames):
    wave_file = wave.open(filename, 'wb')
    wave_file.setnchannels(channels)
    wave_file.setsampwidth(pyaudio.get_sample_size(sample_format))
    wave_file.setframerate(sampling_rate)
    wave_file.writeframes(b''.join(frames))
    wave_file.close()
    print(f"Recording saved to '{filename}'.")

def on_key_release(event):
    if event.name == RecordKey:
        stop_recording()

def start_recording():
    global is_recording, frames
    if not is_recording:
        frames = []
        is_recording = True
        thread = threading.Thread(target=record_audio)
        thread.start()

def stop_recording():
    global is_recording
    is_recording = False
    
async def ActiveKeyboardRecordBind():
    keyboard.on_press_key(RecordKey, lambda _: start_recording())
    keyboard.on_release(on_key_release)

    print("Press 'v' to start recording...")

    keyboard.wait()
    
if(not TextOnlyMode):
    asyncio.run(ActiveKeyboardRecordBind())
else:
    while True:
        text = input("Type something to be translated to Japanese!")
        translate_text(text)

import whisper
from pydub import AudioSegment, silence
import os
import tempfile
import subprocess
import time

# Load audio from various formats
def load_audio(file_path, format=None):
    ext = os.path.splitext(file_path)[-1].lower().replace('.', '')
    try:
        if format:
            return AudioSegment.from_file(file_path, format=format)
        else:
            return AudioSegment.from_file(file_path, format=ext)
    except Exception as e:
        print(f"❌ Failed to load {file_path} as format '{ext}' (or '{format}'): {e}")
        raise

def convert_to_mp3(input_path):
    print(f"🔄 Converting {input_path} to .mp3 for processing...")
    temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    try:
        audio = load_audio(input_path)
        audio.export(temp_mp3, format="mp3")
        return temp_mp3
    except Exception as e:
        print(f"🔥 Error during conversion to MP3: {e}")
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)
        raise

# Remove long silences
def trim_silences(audio, silence_thresh=-60, min_silence_len=250, target_silence_len=180):
    silent_ranges = silence.detect_silence(audio,
                                           min_silence_len=min_silence_len,
                                           silence_thresh=silence_thresh)
    output = AudioSegment.empty()
    last_end = 0
    for start, end in silent_ranges:
        output += audio[last_end:start]
        output += AudioSegment.silent(duration=target_silence_len)
        last_end = end
    output += audio[last_end:]
    return output

# Transcribe audio and get timestamps
def transcribe_audio(file_path, model_size="small"):
    model = whisper.load_model(model_size)
    result = model.transcribe(file_path, word_timestamps=True, verbose=False)
    return result

# Remove filler words
def remove_filler_words(audio, transcription, fillers=["uh", "um", "ah", "erm", "hmm"]):
    segments = transcription.get("segments", [])
    words_to_cut = []
    for seg in segments:
        for word_info in seg.get("words", []):
            word = word_info["word"].strip(".,?!").lower()
            if word in fillers:
                start_ms = int(word_info["start"] * 1000)
                end_ms = int(word_info["end"] * 1000)
                print(f"🗑️ Removing filler: '{word}' at {start_ms}ms–{end_ms}ms")
                words_to_cut.append((start_ms, end_ms))
    output = AudioSegment.empty()
    last_end = 0
    for start, end in words_to_cut:
        output += audio[last_end:start]
        last_end = end
    output += audio[last_end:]
    return output

# Save final audio in original format
def save_audio(audio, output_path):
    ext = os.path.splitext(output_path)[-1].lower()
    format_ext = ext.replace(".", "")
    if format_ext == "m4a":
        format_ext = "ipod"
    audio.export(output_path, format=format_ext)

# Clean audio main function
def clean_audio(input_file, output_file):
    print(f"🧹 Cleaning: {input_file}")
    processing_path = input_file
    temp_extracted_audio = None

    try:
        if input_file.lower().endswith((".mp4", ".mov", ".mkv")):
            print("🎞️ Input is a video file.")
            temp_extracted_audio = convert_to_mp3(input_file)
            processing_path = temp_extracted_audio
        elif input_file.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")):
            print("🎧 Input is an audio file.")
            # No conversion needed for common audio formats
        else:
            print(f"⚠️ Unsupported input file format: {input_file}")
            return

        if not os.path.exists(processing_path):
            print(f"❌ Could not access processing file: {processing_path}")
            return

        # Step 1: Load audio for processing (now loading the processing_path)
        audio = AudioSegment.from_mp3(processing_path)

        # Step 2: Transcribe
        print("🧠 Transcribing for filler word detection...")
        transcription = transcribe_audio(processing_path)

        # Step 3: Remove filler words
        print("✂️ Removing filler words...")
        audio_no_fillers = remove_filler_words(audio, transcription)

        # Step 4: Trim silences
        print("🎧 Trimming long silences...")
        final_audio = trim_silences(audio_no_fillers)

        # Step 5: Save final output
        print(f"💾 Saving cleaned audio to: {output_file}")
        save_audio(final_audio, output_file)
        print(f"✅ Cleaning complete! Output saved as: {output_file}")

    except Exception as e:
        print(f"🔥 An error occurred during the cleaning process: {e}")
    finally:
        if temp_extracted_audio and os.path.exists(temp_extracted_audio):
            os.remove(temp_extracted_audio)
            print(f"🗑️ Removed temporary extracted audio file: {temp_extracted_audio}")

# Script entry point
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ Please provide the input file path as a command-line argument.")
        print("   Example: python cleaner.py input.mp4")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = f"cleaned_{os.path.splitext(os.path.basename(input_file))[0]}.mp3"  # Force .mp3 extension

    clean_audio(input_file, output_file)
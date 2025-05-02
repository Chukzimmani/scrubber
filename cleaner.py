import whisper
from pydub import AudioSegment, silence
import os
import tempfile
import subprocess

# Load audio from various formats
def load_audio(file_path):
    ext = os.path.splitext(file_path)[-1].lower().replace('.', '')
    try:
        return AudioSegment.from_file(file_path, format=ext)
    except Exception as e:
        print(f"❌ Failed to load {file_path} as format '{ext}': {e}")
        raise

def convert_to_mp3_if_needed(input_path):
    ext = os.path.splitext(input_path)[-1].lower()
    if ext == ".mp3":
        print("✅ Already mp3, skipping conversion.")
        return input_path  # No need to convert
    print("🔄 Converting to .mp3 for processing...")
    audio = load_audio(input_path)
    temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    audio.export(temp_mp3, format="mp3")
    return temp_mp3


# Remove long silences
def trim_silences(audio, silence_thresh=-40, min_silence_len=100, target_silence_len=70):
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

# Extract audio from video
def extract_audio_from_video(video_path, output_audio_path="temp_audio.wav"):
    command = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        output_audio_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_audio_path

# Clean audio main function
def clean_audio(file_path, output_path):
    print(f"🧹 Cleaning: {file_path}")

    # Extract audio if it's a video
    if file_path.lower().endswith((".mp4", ".mov", ".mkv")):
        print("🎞️ Extracting audio from video...")
        file_path = extract_audio_from_video(file_path)

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    # Step 1: Convert to mp3 if needed
    processing_path = convert_to_mp3_if_needed(file_path)
    audio = AudioSegment.from_file(processing_path)

    # Step 2: Transcribe
    print("🧠 Transcribing for filler word detection...")
    transcription = transcribe_audio(processing_path)

    # Step 3: Remove filler words
    print("✂️ Removing filler words...")
    audio_no_fillers = remove_filler_words(audio, transcription)

    # Step 4: Trim silences
    print("🎧 Trimming long silences...")
    final_audio = trim_silences(audio_no_fillers)

    # Step 5: Save final output in original format
    print("💾 Saving final audio...")
    save_audio(final_audio, output_path)
    print(f"✅ Done! Output saved as: {output_path}")

# Script entry point
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ Please provide a file to clean. Example:")
        print("   python cleaner.py your_audio_file.mp3")
        sys.exit(1)

    input_file = sys.argv[1]

    # Get extension to preserve original format
    ext = os.path.splitext(input_file)[-1].lower()
    output_file = f"cleaned_{os.path.splitext(os.path.basename(input_file))[0]}{ext}"

    clean_audio(input_file, output_file)


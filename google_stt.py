import requests
import os
import io
import wave
import pickle
from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.cloud import storage
import pandas as pd
from pydub import AudioSegment

#Path to file
filepath = "G:\My Drive\AVP_data\polis_api\\audio"

## Get file info
def frame_rate_channel(audio_file_name):
    with wave.open(audio_file_name, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
        channels = wave_file.getnchannels()
        return frame_rate,channels

## Convert file from stereo to mono for Google API
def stereo_to_mono(audio_file_name):
    sound = AudioSegment.from_wav(audio_file_name)
    sound = sound.set_channels(1)
    sound.export(audio_file_name, format="wav")

## Convert file from MP3 to WAV for Google API
def mp3_to_wav(audio_file_name):
    if audio_file_name.split('.')[1] == 'MP3':    
        sound = AudioSegment.from_mp3(audio_file_name)
        audio_file_name = audio_file_name.split('.')[0] + '.wav'
        sound.export(audio_file_name, format="wav")

## Upload file to Google Cloud Bucket
def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

## Transcribe File
## - Requires audio file uploaded to Google Cloud
def transcribe_gcs(gcs_uri):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""

    ##Path to service account credentials
    credential_path = "G:\My Drive\AVP_data\polis_api\\hs-american-voices-project-b12d8ea9a82f.json"
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
    client = speech.SpeechClient()

    audio = speech.types.RecognitionAudio(uri=gcs_uri)

    config =speech.types.RecognitionConfig(
    #encoding = speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
    #sample_rate_hertz = 8000,
    language_code = 'en-US',
    enable_speaker_diarization = True,
    diarization_speaker_count = 2,
    model = 'video',
    use_enhanced=True)
    
    operation = client.long_running_recognize(config, audio)

    print('Waiting for operation to complete...')
    response = operation.result(timeout=1800)
    wanted_result = response.results[-1]
    with open('out_work.pkl', 'wb') as f:
        pickle.dump(wanted_result, f)

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    output=[]
    prev_speaker_tag = wanted_result.alternatives[0].words[0].speaker_tag
    s = 'Speaker {}:'.format(prev_speaker_tag)
    for i in wanted_result.alternatives[0].words:
        if(i.speaker_tag != prev_speaker_tag):
            output.append(s+'\n')
            s = 'Speaker {}:'.format(i.speaker_tag)
        s += " "+i.word
        prev_speaker_tag = i.speaker_tag
        # The first alternative is the most likely one for this portion.

    output.append(s+'\n')
    return(output)

## Upload test file to GCS

## Transcribe Test File
## Try with shorter file "Baltimore Short.mp3"

filename_mp3 = "G:\My Drive\AVP_data\polis_api\\audio\Baltimore 10min.MP3"
filename_wav = "G:\My Drive\AVP_data\polis_api\\audio\Baltimore 10min.wav"

## Real File (convert to wave)
# mp3_to_wav(filename_mp3)
# stereo_to_mono(filename_wav)
to_print = transcribe_gcs("gs://avp-audio/Baltimore 10min.wav")
print(to_print[0])
with open("transcript.txt", "w") as fout:
    fout.writelines(to_print)
    fout.close()


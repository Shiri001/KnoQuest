import os
import shutil
import tempfile
import base64
import logging
import subprocess
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from .config import settings
from .models.schemas import SpeechTranscriptionResponse, SpeechSynthesisRequest, SpeechSynthesisResponse
from .auth import get_current_identity, IdentityContext

logger = logging.getLogger("knoquest.speech")
speech_router = APIRouter(prefix="/api/speech", tags=["Speech"])

def _convert_audio_to_pcm_wav(input_bytes: bytes) -> str:
    """
    Converts incoming audio (WebM, Ogg, MP3, etc.) to 16kHz 16-bit Mono PCM WAV
    using ffmpeg if available, otherwise writes raw bytes to a temp file.
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as in_tmp:
        in_tmp.write(input_bytes)
        in_path = in_tmp.name

    out_path = in_path + ".wav"
    ffmpeg_bin = shutil.which("ffmpeg") or r"C:\msys64\ucrt64\bin\ffmpeg.EXE"

    try:
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", in_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        try:
            os.remove(in_path)
        except Exception:
            pass
        return out_path
    except Exception as e:
        logger.warning(f"ffmpeg conversion notice ({e}), using raw temp audio file.")
        try:
            os.remove(in_path)
        except Exception:
            pass
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw_tmp:
            raw_tmp.write(input_bytes)
            return raw_tmp.name

@speech_router.post("/transcribe", response_model=SpeechTranscriptionResponse)
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...),
    language: Optional[str] = Form("en"),
    identity: IdentityContext = Depends(get_current_identity)
):
    """
    Transcribes audio into text using Azure Cognitive Services Speech SDK.
    Converts browser audio (WebM/Opus) into standard 16kHz PCM WAV for Azure.
    """
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio payload")

        # If Azure Speech Key is configured, transcribe via Azure Cognitive Services
        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            wav_path = None
            try:
                import azure.cognitiveservices.speech as speechsdk

                speech_config = speechsdk.SpeechConfig(
                    subscription=settings.AZURE_SPEECH_KEY,
                    region=settings.AZURE_SPEECH_REGION
                )
                lang_map = {
                    "en": "en-US",
                    "hi": "hi-IN",
                    "es": "es-ES",
                    "fr": "fr-FR"
                }
                speech_config.speech_recognition_language = lang_map.get(language or "en", "en-US")

                wav_path = _convert_audio_to_pcm_wav(audio_bytes)
                audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
                recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
                result = recognizer.recognize_once_async().get()

                # Release Windows file handles before removing temp file
                del recognizer
                del audio_config
                try:
                    if wav_path and os.path.exists(wav_path):
                        os.remove(wav_path)
                except Exception:
                    pass

                if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    logger.info(f"Azure Speech Recognized: '{result.text}'")
                    return SpeechTranscriptionResponse(text=result.text, language=language or "en")
                elif result.reason == speechsdk.ResultReason.NoMatch:
                    logger.info("Azure Speech returned NoMatch (silence or unintelligible audio).")
                    return SpeechTranscriptionResponse(text="", language=language or "en")
                else:
                    cancellation = result.cancellation_details
                    logger.warning(f"Azure Speech recognition issue: {cancellation.reason} | Detail: {cancellation.error_details}")
                    return SpeechTranscriptionResponse(text="", language=language or "en")
            except Exception as e:
                logger.error(f"Azure Speech SDK failed during transcription: {e}", exc_info=True)
                if wav_path:
                    try:
                        os.remove(wav_path)
                    except Exception:
                        pass
                return SpeechTranscriptionResponse(text="", language=language or "en")

        return SpeechTranscriptionResponse(text="", language=language or "en")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@speech_router.post("/synthesize", response_model=SpeechSynthesisResponse)
async def synthesize_speech_endpoint(
    request: SpeechSynthesisRequest,
    identity: IdentityContext = Depends(get_current_identity)
):
    """
    Synthesizes text to speech using Azure Cognitive Services Speech SDK
    or returns browser-ready audio metadata for native client synthesis.
    """
    try:
        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            try:
                import azure.cognitiveservices.speech as speechsdk

                speech_config = speechsdk.SpeechConfig(
                    subscription=settings.AZURE_SPEECH_KEY,
                    region=settings.AZURE_SPEECH_REGION
                )
                voice_map = {
                    "en": "en-US-JennyNeural",
                    "hi": "hi-IN-SwaraNeural",
                    "es": "es-ES-ElviraNeural",
                    "fr": "fr-FR-DeniseNeural"
                }
                speech_config.speech_synthesis_voice_name = voice_map.get(request.language or "en", "en-US-JennyNeural")
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                result = synthesizer.speak_text_async(request.text).get()

                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    audio_b64 = base64.b64encode(result.audio_data).decode("utf-8")
                    return SpeechSynthesisResponse(
                        status="success",
                        audio_format="wav",
                        audio_base64=audio_b64,
                        message="Synthesized via Azure Speech SDK"
                    )
            except Exception as e:
                logger.warning(f"Azure Speech synthesis failed: {e}. Defaulting to client TTS.")

        return SpeechSynthesisResponse(
            status="client_tts_ready",
            audio_format="browser_speech",
            audio_base64=None,
            message="Ready for native Web Speech API synthesis"
        )
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

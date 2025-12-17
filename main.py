import tempfile, os, shutil
import whisper
import google.generativeai as genai
from fastapi import FastAPI, UploadFile
import base64
from gtts import gTTS

app = FastAPI()

class AudioFileManager:
    path = ""

    def __init__(self):
        # returns file object
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a")
        # get path (tmp/tmpxyz.mp3) for Whipser
        self.path = self.tmp.name
        self.tmp.close()

    # returns path name
    def getFile(self):
        print("path is at: ", self.path)
        return self.path
    
    # save stream
    def saveStream(self, upload_file: UploadFile):
        with open(self.path, 'wb') as dest:
            shutil.copyfileobj(upload_file.file, dest)
        return self.path
        
    # clean up temp file
    def cleanUp(self):
        if os.path.exists(self.path):
            os.remove(self.path)
            print(f"Deleted temp file: {self.path}")

class TranscriberService:

    def __init__(self):
        print("Loading Whisper model... ")
        self.model = whisper.load_model("base")

    def transcribe(self, path):
        result = self.model.transcribe(path)
        text = result["text"]
        
        return text

class LLMService:
    model = None

    def __init__(self):
        genai.configure(api_key=API_KEY)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generateResponse(self, textFromWhisper):
        response = self.model.generate_content(textFromWhisper)
        return response.text

transcriber = TranscriberService()
llm_service = LLMService()

# controller 
@app.post("/chat")
async def receiveAudio(file: UploadFile):
    print("received endpoint")
    # setup file manager
    file_manager = AudioFileManager()

    try:
        # save audio to disk
        saved_path = file_manager.saveStream(file)

        # transcribe
        user_text = transcriber.transcribe(saved_path)
        print(f"User said: {user_text}")

        # response by AI
        ai_reply = llm_service.generateResponse(f"User texts: {user_text}. Reply in Japanese and translate in English as well. Append 'English:' before you start saying English")
        print(f"AI replied: {ai_reply}")

        tts_path = "temp_reply.mp3"
        trancated_response = ai_reply.split("English:")[0]
        tts = gTTS(text=trancated_response, lang='ja')
        tts.save(tts_path)

        # convert audio file to base64
        with open(tts_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            base64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        if os.path.exists(tts_path):
            os.remove(tts_path)

        return {
            "user_text": user_text,
            "reply_text": ai_reply,
            "audio_base64": base64_audio
        }
    
    finally:
        # clean up file
        file_manager.cleanUp()
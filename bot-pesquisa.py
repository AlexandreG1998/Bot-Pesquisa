from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Start, Stream
from flask_sockets import Sockets
import base64
import json
import logging
import io
from pydub import AudioSegment
from pydub.playback import play
#import soundfile as sf

import threading
from google.cloud.speech import RecognitionConfig, StreamingRecognitionConfig

#from SpeechClientBridge import SpeechClientBridge


from flask import Flask
from flask_sockets import Sockets


from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import os

from google.cloud import speech

stream_url = ''
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''

config = RecognitionConfig(
    encoding=RecognitionConfig.AudioEncoding.MULAW,
    sample_rate_hertz=8000,
    language_code="pt-BR",
)
streaming_config = StreamingRecognitionConfig(config=config, interim_results=True)

dados_inbound = []


    
app = Flask(__name__)
sockets = Sockets(app)

HTTP_SERVER_PORT = 5000

dados_call = []

dados_ = []
audios = []
audios2 = []
audios3 = []

account_sid = ""
auth_token = ""



#Agrupar .wav para formação de banco de dados com objetivo de melhorias
def agrupar_call(array = dados_inbound):
    compilado_ = array[0]
    for i in range(1, len(array)):
        compilado_ = compilado_ + array[i]

    return(compilado_)

#Transcrever audio
def transcrever(data = None):
    client = speech.SpeechClient()
    
    audio = speech.RecognitionAudio(content=data)
    
    config = RecognitionConfig(
    encoding=RecognitionConfig.AudioEncoding.MULAW,
    sample_rate_hertz=8000,
    language_code="pt-BR",
    )

    response = client.recognize(config = config, audio = audio)
    transcricoes = []
    
    for result in response.results:
        transcricoes.append(result.alternatives[0].transcript)
        print("Transcript: {}".format(result.alternatives[0].transcript))
    return(transcricoes)

    

    
#Separa audios enviados e recebidos    
def split_in_out(array = None):
    inbound  = []
    outbound = []

    for i in range(len(array)):
        data = array[i]
        if(data['event'] == 'media'):
            media = data['media']
            payload = media['payload']
            chunk = base64.b64decode(payload)
            if(media['track'] == 'inbound'):
                inbound.append(chunk)
            else:
                outbound.append(chunk)
    return([inbound, outbound])

#Audio da ligação para .wav por frame        
def render_audio(array = None, channels= 1, sample_width=1,frame_rate = 16000,
                 caminho = 'C:/Users/Alexandre/Desktop/twilio/server/audios/',
                 arquivo_final = ''):
    
    names = []
    data = []
    outfile = arquivo_final
    import wave
    
    for i in range(len(array)):

        f_ = io.BytesIO(array[i])
        recording = AudioSegment.from_file(f_,channels= channels, sample_width=sample_width,format="raw",
                                           frame_rate = frame_rate)
        nome = caminho + 'teste_' + str(i) + '.wav'
        names.append(nome)
        recording.export(nome, format='wav')

        
        #nome = caminho + 'teste_' + str(i) + '.wav'
        #names.append(nome)
        #a = bytearray(array[i])
        #b = np.array(a, dtype=np.int16)

        #scipy.io.wavfile.write(nome, 8000, b)
        
    for infile in names:
        w = wave.open(infile, 'rb')
        data.append( [w.getparams(), w.readframes(w.getnframes())] )
        w.close()

    output = wave.open(outfile, 'wb')
    output.setparams(data[0][0])
    for i in range(len(data)):
        output.writeframes(data[i][1])
    output.close()
        
#Função que inicia fluxo da ligação
@app.route("/voice", methods=['GET', 'POST'])
def voice():
    # Start a TwiML response

    cliente = Client(account_sid, auth_token)
    calls = cliente.calls.list()

    call_sid = calls[0].sid
    
    resp = VoiceResponse()

    #resp.say('Ligação Iniciada....', voice = 'Polly.Camila-Neural', language = 'pt-BR')
    start = Start()

    start.stream(url= stream_url,
                 track = 'both_tracks')

    resp.append(start)
    
    #start = Start()

    #resp.update(twiml=mensagem2)
    #call = cliente.calls(call_sid).update(twiml=mensagem2)

    
    
    #gather = Gather(num_digits=1, action='/gather')
    
    #resp.append(gather)
    resp.redirect('/primeirapergunta')
    #dados_.append(resp)
    return str(resp)
#Função de exemplo para pergunta/dialogo
@app.route('/primeirapergunta', methods=['GET', 'POST'])
def primeirapergunta():
    resp = VoiceResponse()
    
    resp.say('Mensagem número 2.....', voice = 'Polly.Camila-Neural', language = 'pt-BR')
    
    #resp.redirect('/voice')
    #resp.play('C:/Users/Alexandre/Desktop/twilio/server/sn.mp3')
    resp.redirect('/segundapergunta')
    return str(resp)

#Função de exemplo para pergunta/dialogo
@app.route('/segundapergunta', methods=['GET', 'POST'])
def segundapergunta():
    
    resp = VoiceResponse()
    resp.say('Mensagem número 3.....', voice = 'Polly.Camila-Neural', language = 'pt-BR')
    
    #resp.redirect('/voice')
    #resp.play('C:/Users/Alexandre/Desktop/twilio/server/sn.mp3')
    resp.redirect('/primeirapergunta')
    return str(resp)

def on_transcription_response(response):
    if not response.results:
        return

    result = response.results[0]
    if not result.alternatives:
        return

    transcription = result.alternatives[0].transcript
    print("Transcription: " + transcription)


#Web Socket que recebe o áudio da ligação em tempo real e transcreve
@sockets.route('/media')
def transcript(ws):
    print("WS connection opened")
    #bridge = SpeechClientBridge(streaming_config, on_transcription_response)
    #t = threading.Thread(target=bridge.start)
    #t.start()

    while not ws.closed:
        message = ws.receive()
        if message is None:
            bridge.add_request(None)
            bridge.terminate()
            break

        data = json.loads(message)
        if data["event"] in ("connected", "start"):
            print(f"Media WS: Received event '{data['event']}': {message}")
            continue
        if data["event"] == "media":
            media = data["media"]
            if(media['track'] == 'inbound'):
                chunk = base64.b64decode(media["payload"])
                dados_inbound.append(chunk)
                #bridge.add_request(chunk)
        if data["event"] == "stop":
            print(f"Media WS: Received event 'stop': {message}")
            print("Stopping...")
            break

    #bridge.terminate()
    print("WS connection closed")

#Inicia servidor na porta 5000
HTTP_SERVER_PORT = 5000
if __name__ == "__main__":
    app.logger.setLevel(logging.DEBUG)
    

    server = pywsgi.WSGIServer(('', HTTP_SERVER_PORT), app, handler_class=WebSocketHandler)
    print("Server listening on: http://localhost:" + str(5000))
    server.serve_forever()

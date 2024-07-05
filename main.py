import os
import pybase64
import requests
import azure.cognitiveservices.speech as speechsdk
import http.client
import json
import threading
from azure.ai.contentsafety import ContentSafetyClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.ai.contentsafety.models import AnalyzeTextOptions
from dotenv import load_dotenv

load_dotenv()

key_api_chat= os.environ.get("API_KEY_CHAT")


key = os.environ.get("API_KEY_CONTENT_SAFETY")
endpoint = os.environ.get("ENDPOINT_CONTENT_SAFETY")

# Configuração do Azure Speech
speech_config = speechsdk.SpeechConfig(subscription=key_api_chat, region="eastus2")

# Variável global para controlar a execução da função recognize_from_text
continue_speaking = True

def searchAI(texto):
    # Substitua com o seu endpoint e chave API do Azure Cognitive Search
    texto_convertido = texto.split(" ")[1]
    
    endpoint = "https://chagaspesquisa.search.windows.net/"
    api_key = os.getenv("API_SERPER")
    # Defina o endpoint de pesquisa e os parâmetros de consulta
    search_endpoint = f"{endpoint}indexes/azureblobchagas-index/docs?api-version=2021-04-30-Preview&search={texto_convertido}"
    headers = {
        'Content-Type': 'application/json',
        'api-key': api_key,
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    print(search_endpoint)
    # Realize a requisição GET para o Azure Cognitive Search
    response = requests.get(search_endpoint, headers=headers)

    # Verifique se a requisição foi bem-sucedida
    if response.status_code == 200:
        search_results = response.json()
        for result in search_results['value']:            # Convert from base64
            base64_str = result["metadata_storage_path"]
            print("base64:" + base64_str)

            # Adicionar padding se necessário
            padding = len(base64_str) % 4
            if padding != 0:
                base64_str += "=" * (4 - padding)

            # Decodificar do base64 para bytes
            try:
                decoded_bytes = pybase64.b64decode(base64_str)
            except Exception as e:
                print(f"Error decoding base64: {e}")
                continue

            # Converter de bytes para string, especificando o encoding correto
            url = decoded_bytes.decode('utf-8')

            print(url)
            # Verificar e remover o caractere '5' no final, se presente
            if url.endswith(".docx5"):
                url = url[:-5] + "docx"
            elif url.endswith(".pdf5"):
                url = url[:-4] + "pdf"

            # Exibir a URL final
            print(url)
        
            # Nome da pasta onde os arquivos serão salvos
            folder_name = "downloads"

            # Criar a pasta se não existir
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            # Baixar o conteúdo da URL
            r = requests.get(url, allow_redirects=True)

            # Nome do arquivo a partir da URL
            filename = url.split('/')[-1]

            # Limpar o nome do arquivo de caracteres inválidos
            filename = filename.replace('\r', '').replace('\n', '')

            # Caminho completo para salvar o arquivo na pasta criada
            file_path = os.path.join(folder_name, filename)

            # Salvar o arquivo na pasta
            with open(file_path, 'wb') as file:
                file.write(r.content)

            print(f"Arquivo salvo em: {file_path}")
            
    else:
        print(f"Erro na requisição: {response.status_code} - {response.text}")

    return
def contentSafety(texto):
    
    """
    Sends a request to the Azure Content Safety API to moderate the provided text.
    Returns True if no category has a severity level greater than 1, False otherwise.

    Parameters:
    texto (str): The text to be moderated.

    Returns:
    bool: True if the text is safe, False otherwise.
    """

    # Create a Content Safety client
    client = ContentSafetyClient(endpoint, AzureKeyCredential(key))

    # Create a request to analyze the text
    request = AnalyzeTextOptions(text=texto)

    try:
        # Send the request and get the response
        response = client.analyze_text(request)
    except HttpResponseError as error:
        # If there is an error, print the error message and raise the exception
        if error.error:
            print(error.error)
        print(error)
        raise

    # Check if any category has a severity level greater than 1
    for category in response.categories_analysis:
        if category.severity > 1:
            return False

    # If no category has a severity level greater than 1, the text is safe
    return True

def recognize_from_microphone():
    """
    Continuously monitors the microphone for speech and performs actions based on the recognized text.
    """
    # Configurações do reconhecimento de fala
    speech_config.speech_recognition_language = "pt-BR"
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("Pode falar.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    textoFalado = speech_recognition_result.text if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech else None

    if textoFalado:
        print("Recognized: {}".format(textoFalado))
        
        # Check if the recognized text is safe to use
        texto = contentSafety(textoFalado)
        
        if(texto == True):
            return textoFalado
        else:
            return None
        
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")

def recognize_from_text():
    global continue_speaking
    # Configurações da síntese de fala
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    speech_config.speech_synthesis_voice_name = 'pt-BR-JulioNeural'
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    text = chatAI()
    if text:
        speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Speech synthesized for text [{}]".format(text))
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print("Error details: {}".format(cancellation_details.error_details))
                    print("Did you set the speech resource key and region values?")

def chatAI():
    """
    This function sends a POST request to the "google.serper.dev" API to retrieve search results for the user's query.
    It then accesses the first result's snippet and returns it as a string.
    """
    
    # Create a connection to the API
    conn = http.client.HTTPSConnection("google.serper.dev")
    
    # Get the user's speech-to-text input
    texto = recognize_from_microphone()
    
        # If the user didn't say anything, return a predefined response
    if not texto:
        recognize_from_textDefinido("foi salvo o que voce disse e sera enviado para o centro de policia mais proximo")
        return ""
    
    
    # Split the input into individual words
    texto_quebrado = texto.split(' ')
    
    print(texto_quebrado)
    
    # Check if the user said "pesquise" (which means "search" in Portuguese)
    for i in texto_quebrado:
        if i.lower() == "consulte":
            # If so, call the searchAI function
            return searchAI(texto)
    
    
    # Prepare the payload for the API request
    payload = json.dumps({
        "q": texto,  # The user's query
        "hl": "pt-br",  # The language of the search results
        "gl": "br"  # The country to search in
    })
    
    # Set the headers for the API request
    headers = {
        'X-API-KEY': os.getenv("X_API_KEY"),
        'Content-Type': 'application/json'
    }
    
    # Send the API request
    conn.request("POST", "/search", payload, headers)
    res = conn.getresponse()
    data = res.read()
    
    # Parse the API response as JSON
    json_data = json.loads(data.decode("utf-8"))
    
    # Access the first result's snippet and return it as a string
    answer = json_data['organic'][0]['snippet']
    answer_str = str(answer) if answer else None
    
    # Print the answer for debugging purposes
    print(answer_str)
    
    return answer_str

def monitor_microphone():
    """
    Continuously monitors the microphone for speech and performs actions based on the recognized text.
    """
    global continue_speaking
    while continue_speaking:
        # Recognize speech from the microphone
        textoFalado = recognize_from_microphone()
        
        # If no speech was recognized, print a message and continue the loop
        if not textoFalado:
            print("Nenhum texto foi falado")
            continue
        
        # Print the recognized text
        print(textoFalado)
        
        # Split the text into individual words
        quebra_frase = textoFalado.split(" ")
        
        # Check each word in the split text
        for palavra in quebra_frase:
            # If the word contains "chagas", stop the loop, start speech recognition, and resume the loop
            if "chagas" in palavra.lower():
                recognize_from_textDefinido("O que posso fazer por voce?")
                continue_speaking = False
                recognize_from_text()
                continue_speaking = True
            
            # If the word contains "osasco", call the recognize_from_textDefinido function with a specific message
            elif "sair" in palavra.lower():
                recognize_from_textDefinido("tchau tchau")
                return

def recognize_from_textDefinido(palavra):
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    speech_config.speech_synthesis_voice_name = 'pt-BR-JulioNeural'
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    text = palavra
    if text:
        speech_synthesizer.speak_text_async(text).get()

if __name__ == "__main__":
    # Iniciar a thread de monitoramento do microfone
    microphone_thread = threading.Thread(target=monitor_microphone)
    microphone_thread.start()
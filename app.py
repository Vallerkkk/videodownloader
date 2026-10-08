from flask import Flask, render_template, request, Response, stream_with_context
import requests

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/baixar', methods=['POST'])
def baixar():
    url = request.form.get('url')

    if not url:
        return "Erro: Nenhum link fornecido.", 400

    if 'x.com' not in url and 'twitter.com' not in url:
        return "Erro: Este sistema suporta apenas links do X (antigo Twitter).", 400

    try:
        # Limpa parâmetros extras da URL e converte para a API do vxtwitter
        url_limpa = url.split('?')[0]
        url_api = url_limpa.replace('https://x.com/', 'https://api.vxtwitter.com/').replace('https://twitter.com/', 'https://api.vxtwitter.com/')
        
        resposta = requests.get(url_api, timeout=10).json()
        
        if 'media_extended' in resposta:
            for media in resposta['media_extended']:
                if media['type'] == 'video':
                    link_video = media['url']
                    
                    # Faz o stream direto do ficheiro para o utilizador
                    r = requests.get(link_video, stream=True, timeout=10)
                    
                    def gerar_arquivo():
                        for pedaco in r.iter_content(chunk_size=1024 * 1024):
                            yield pedaco
                    
                    return Response(
                        stream_with_context(gerar_arquivo()),
                        content_type=r.headers.get('content-type', 'video/mp4'),
                        headers={'Content-Disposition': 'attachment; filename="video_x.mp4"'}
                    )
                    
        return "Erro: Nenhum vídeo encontrado neste post.", 404
        
    except Exception as e:
        return f"Erro ao processar o link: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, Response, stream_with_context
import yt_dlp
import requests

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/baixar', methods=['POST'])
def baixar():
    url = request.form.get('url')
    formato_escolhido = request.form.get('formato', 'video')

    if not url:
        return "Erro: Nenhum link fornecido.", 400

    # === TRUQUE ANTI-BLOQUEIO (STREAMING) PARA O X/TWITTER ===
    if 'x.com' in url or 'twitter.com' in url:
        try:
            url_limpa = url.split('?')[0]
            url_api = url_limpa.replace('https://x.com/', 'https://api.vxtwitter.com/').replace('https://twitter.com/', 'https://api.vxtwitter.com/')
            
            resposta = requests.get(url_api).json()
            
            if 'media_extended' in resposta:
                for media in resposta['media_extended']:
                    if media['type'] == 'video':
                        link_video = media['url']
                        
                        r = requests.get(link_video, stream=True)
                        
                        def gerar_arquivo():
                            for pedaco in r.iter_content(chunk_size=1024 * 1024):
                                yield pedaco
                        
                        return Response(
                            stream_with_context(gerar_arquivo()),
                            content_type=r.headers.get('content-type', 'video/mp4'),
                            headers={'Content-Disposition': 'attachment; filename="video_x.mp4"'}
                        )
                        
            return "Erro: Nenhum vídeo encontrado neste tweet.", 404
        except Exception as e:
            return f"Erro ao contornar o Twitter: {str(e)}", 500

    # === PARA TODAS AS OUTRAS REDES (YouTube, TikTok, Instagram, etc) ===
    formato_ydl = 'bestaudio/best' if formato_escolhido == 'audio' else 'best[ext=mp4]/best'

    ydl_opts = {
        'format': formato_ydl,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        
        # TRUQUE DEFINITIVO PARA O YOUTUBE NO RENDER:
        # Sem cookies e forçando apenas clientes mobile nativos (iOS e Android)
        'extractor_args': {
            'youtube': ['player_client=ios,android', 'player_skip=webpage']
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrai os dados em modo fantasma mobile
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                info = info['entries'][0]

            link_direto = info.get('url')
            
            if link_direto:
                return redirect(link_direto)
            else:
                return "Erro: Não foi possível extrair o link direto.", 404
                
    except Exception as e:
        return f"Erro ao processar a extração da mídia: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
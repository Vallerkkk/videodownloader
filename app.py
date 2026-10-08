from flask import Flask, render_template, request, redirect, Response, stream_with_context
import yt_dlp
import requests
import re  # Biblioteca nativa para processar textos

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

    # === TRUQUE ANTI-BLOQUEIO PARA YOUTUBE (API PIPED) ===
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            # Extrai apenas o ID do vídeo (ex: dQw4w9WgXcQ) mesmo de links sujos
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
            if not match:
                return "Erro: Link do YouTube inválido.", 400
                
            video_id = match.group(1)
            
            # Lista de servidores Piped (Open Source, sem bloqueio de Cloudflare e com Proxy)
            servidores_piped = [
                "https://pipedapi.kavin.rocks",
                "https://api.piped.projectsegfau.lt",
                "https://piped-api.lunar.icu",
                "https://pipedapi.smnz.de"
            ]
            
            link_direto = None
            
            # Tenta baixar usando os servidores da lista. Se um falhar, tenta o próximo silenciosamente.
            for servidor in servidores_piped:
                try:
                    r = requests.get(f"{servidor}/streams/{video_id}", timeout=8)
                    if r.status_code == 200:
                        dados = r.json()
                        
                        if formato_escolhido == 'audio':
                            # Pega a melhor qualidade de áudio
                            audios = dados.get('audioStreams', [])
                            if audios:
                                melhor_audio = max(audios, key=lambda x: x.get('bitrate', 0))
                                link_direto = melhor_audio.get('url')
                        else:
                            # Pega o melhor vídeo que já tem áudio embutido (videoOnly = False)
                            videos = [v for v in dados.get('videoStreams', []) if not v.get('videoOnly')]
                            if videos:
                                # O último item da lista costuma ser a resolução mais alta (720p)
                                link_direto = videos[-1].get('url')
                                
                        if link_direto:
                            break # Encontrou o link com sucesso, sai do loop de tentativas
                except:
                    continue # Servidor atual caiu, tenta o próximo da lista
                    
            if link_direto:
                # O usuário é redirecionado para o proxy seguro do Piped, evitando o Erro 403
                return redirect(link_direto)
            else:
                return "Erro: Todos os servidores alternativos falharam ao tentar extrair o vídeo do YouTube.", 500
                
        except Exception as e:
            return f"Erro ao contornar o YouTube: {str(e)}", 500


    # === TRUQUE ANTI-BLOQUEIO PARA O X/TWITTER (API VXTWITTER) ===
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


    # === PARA TODAS AS OUTRAS REDES (TikTok, Instagram, Facebook, etc) ===
    formato_ydl = 'bestaudio/best' if formato_escolhido == 'audio' else 'best[ext=mp4]/best'

    ydl_opts = {
        'format': formato_ydl,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
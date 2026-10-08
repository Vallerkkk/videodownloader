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

    # === TRUQUE ANTI-BLOQUEIO DE SEGURANÇA (YOUTUBE) ===
    # Se o script Javascript falhar, este código assume o controle
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            servidores_cobalt = [
                "https://co.wuk.sh/api/json",
                "https://cobalt.api.timelessnesses.me/api/json",
                "https://api.cobalt.tools/api/json"
            ]
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
            payload = {
                'url': url,
                'vCodec': 'h264',
                'videoQuality': '1080',
                'isAudioOnly': True if formato_escolhido == 'audio' else False,
                'downloadMode': 'audio' if formato_escolhido == 'audio' else 'auto'
            }
            
            # Tenta usar a API no Backend (Isso evita erros de CORS completamente)
            for api_url in servidores_cobalt:
                try:
                    r = requests.post(api_url, json=payload, headers=headers, timeout=6)
                    if r.status_code == 200:
                        dados = r.json()
                        if 'url' in dados:
                            return redirect(dados['url'])
                        elif 'picker' in dados and len(dados['picker']) > 0:
                            return redirect(dados['picker'][0]['url'])
                except:
                    continue
                    
            # A ÚLTIMA CARTADA: Se todas as APIs falharem, usa o yt-dlp disfarçado de Android
            formato_ydl = 'bestaudio/best' if formato_escolhido == 'audio' else 'best[ext=mp4]/best'
            ydl_opts = {
                'format': formato_ydl,
                'quiet': True,
                'no_warnings': True,
                'geo_bypass': True,
                'extractor_args': {'youtube': ['player_client=android']}
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                link_direto = info.get('url')
                if link_direto:
                    return redirect(link_direto)
                    
            return "Erro: Todas as defesas do servidor foram bloqueadas. Tente novamente.", 500
        except Exception as e:
            return f"Erro profundo no processamento do YouTube: {str(e)}", 500


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
        return f"Erro ao processar a extração com yt-dlp: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
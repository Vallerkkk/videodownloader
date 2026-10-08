from flask import Flask, render_template, request, redirect, Response, stream_with_context, jsonify
import yt_dlp
import requests

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

# ================= TÚNEL PROXY PARA O YOUTUBE =================
# Funciona como o 'api.azk.com.pl'. Processa a extração remotamente.
@app.route('/proxy/iniciar', methods=['POST'])
def proxy_iniciar():
    dados = request.json
    url_video = dados.get('url')
    formato = dados.get('formato') # 'mp3' ou '720'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # API Principal: O motor do Y2Mate
    try:
        url_api1 = f"https://p.oceansaver.in/ajax/download.php?format={formato}&url={url_video}&api=dfcb6d76f2f6a9894gjkege8a4ab232222"
        r1 = requests.get(url_api1, headers=headers, timeout=8)
        d1 = r1.json()
        if str(d1.get('success')) == '1' and 'id' in d1:
            return jsonify({"success": True, "id": d1['id'], "provedor": "oceansaver"})
    except:
        pass

    # API Secundária: Loader.to
    try:
        url_api2 = f"https://loader.to/ajax/download.php?format={formato}&url={url_video}"
        r2 = requests.get(url_api2, headers=headers, timeout=8)
        d2 = r2.json()
        if d2.get('success') and 'id' in d2:
            return jsonify({"success": True, "id": d2['id'], "provedor": "loader"})
    except:
        pass

    return jsonify({"success": False, "error": "Todos os motores de conversão falharam"}), 500

@app.route('/proxy/progresso', methods=['GET'])
def proxy_progresso():
    id_tarefa = request.args.get('id')
    provedor = request.args.get('provedor')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        if provedor == "oceansaver":
            r = requests.get(f"https://p.oceansaver.in/ajax/progress.php?id={id_tarefa}", headers=headers, timeout=8)
            d = r.json()
            if str(d.get('success')) == '1':
                progresso = min(100, int(d.get('progress', 0) / 10))
                return jsonify({"success": True, "progress": progresso, "download_url": d.get('download_url')})
            else:
                return jsonify({"success": False, "text": d.get('text', 'O vídeo pode estar restrito.')})
        
        elif provedor == "loader":
            r = requests.get(f"https://loader.to/ajax/progress.php?id={id_tarefa}", headers=headers, timeout=8)
            d = r.json()
            if d.get('success') == True:
                return jsonify({"success": True, "progress": int(d.get('progress', 0)), "download_url": d.get('download_url')})
            else:
                return jsonify({"success": False, "text": "Falha na conversão."})
                
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ================= RESTANTES REDES SOCIAIS =================
@app.route('/baixar', methods=['POST'])
def baixar():
    url = request.form.get('url')
    formato_escolhido = request.form.get('formato', 'video')

    if not url:
        return "Erro: Nenhum link fornecido.", 400

    if 'youtube.com' in url or 'youtu.be' in url:
        return "Erro: O YouTube deve ser processado pela interface web.", 400

    # Para o X/Twitter (Streaming direto via vxtwitter)
    if 'x.com' in url or 'twitter.com' in url:
        try:
            url_limpa = url.split('?')[0]
            url_api = url_limpa.replace('https://x.com/', 'https://api.vxtwitter.com/').replace('https://twitter.com/', 'https://api.vxtwitter.com/')
            resposta = requests.get(url_api).json()
            if 'media_extended' in resposta:
                for media in resposta['media_extended']:
                    if media['type'] == 'video':
                        r = requests.get(media['url'], stream=True)
                        def gerar_arquivo():
                            for pedaco in r.iter_content(chunk_size=1024 * 1024):
                                yield pedaco
                        return Response(stream_with_context(gerar_arquivo()), content_type=r.headers.get('content-type', 'video/mp4'), headers={'Content-Disposition': 'attachment; filename="video_x.mp4"'})
            return "Erro: Nenhum vídeo encontrado neste tweet.", 404
        except Exception as e:
            return f"Erro ao contornar o Twitter: {str(e)}", 500

    # Para TikTok, Instagram, etc
    formato_ydl = 'bestaudio/best' if formato_escolhido == 'audio' else 'best[ext=mp4]/best'
    ydl_opts = {'format': formato_ydl, 'quiet': True, 'no_warnings': True, 'geo_bypass': True}
    
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

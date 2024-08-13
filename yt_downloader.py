import yt_dlp as ytdlp
from pathlib import Path
import sys
import re

def download_video(url, video_index=None, audio=False, resolution='720p'):
    try:
        if getattr(sys, 'frozen', False):
            project_path = Path(sys.executable).parent
        else:
            project_path = Path(__file__).parent

        ffmpeg_path = project_path / 'ffmpeg' / 'ffmpeg.exe'
        
        if not ffmpeg_path.exists():
            raise FileNotFoundError(f"ffmpeg.exe no se encuentra en {ffmpeg_path}")

        ydl_opts = {
            'outtmpl': str(project_path / '%(title)s.%(ext)s'),
            'ffmpeg_location': str(project_path / 'ffmpeg'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],  # Hook para mostrar la barra de progreso
        }

        if audio:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            ydl_opts['format'] = f'bestvideo[height<={resolution}]+bestaudio/best' if resolution else 'bestvideo+bestaudio/best'

        if video_index is not None:
            ydl_opts['noplaylist'] = True
        else:
            ydl_opts['noplaylist'] = False

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if 'entries' in info_dict:
                if video_index is not None and len(info_dict['entries']) > video_index:
                    video_url = info_dict['entries'][video_index]['url']
                    ydl.download([video_url])
                else:
                    ydl.download([url])
            else:
                ydl.download([url])

            return f"Descargado: {info_dict['title']}"
    except Exception as e:
        return f'Ocurrió un error: {e}'

def validate_youtube_url(url):
    regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(regex, url)

def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total:
            downloaded = d.get('downloaded_bytes', 0)
            percentage = downloaded / total * 100
            bar_length = 40
            filled_length = int(bar_length * downloaded // total)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            sys.stdout.write(f'\r|{bar}| {percentage:.1f}% completado')
            sys.stdout.flush()
    elif d['status'] == 'finished':
        print("\nDescarga completada, convirtiendo...")

def main():
    while True:
        try:
            url = input("Ingrese la URL de YouTube: ")

            if not validate_youtube_url(url):
                print('URL no válida. Asegúrate de que sea una URL de YouTube.')
                input("Presiona Enter para salir...")
                return

            formato_elegido = input("Descargar como (1) MP4 o (2) MP3: ")

            if formato_elegido == "1":
                resolucion_elegida = input("Ingrese la resolución (ej., 720p, 1080p) o presione Enter para la resolución predeterminada (720p): ")
                if not resolucion_elegida:
                    resolucion_elegida = '720p'
                video_index = input("Ingrese el índice del video en la playlist o mix (o presione Enter si no es una playlist o mix): ")
                video_index = int(video_index) if video_index else None
                resultado = download_video(url, video_index=video_index, audio=False, resolution=resolucion_elegida)
                print(f"\033[92m{resultado}\033[0m")  # Verde para éxito
            elif formato_elegido == "2":
                video_index = input("Ingrese el índice del video en la playlist o mix (o presione Enter si no es una playlist o mix): ")
                video_index = int(video_index) if video_index else None
                resultado = download_video(url, video_index=video_index, audio=True)
                print(f"\033[92m{resultado}\033[0m")  # Verde para éxito
            else:
                print("Opción inválida.")
                continue

            seguir = input("¿Desea descargar otra canción? (s/n): ").strip().lower()
            if seguir != 's':
                break

        except Exception as e:
            print(f'\033[91mOcurrió un error inesperado: {e}\033[0m')  # Rojo para error
        finally:
            input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()
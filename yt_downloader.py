import ctypes
import re
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from urllib.parse import parse_qs, urlparse

import yt_dlp as ytdlp


def download_video(url, video_index=None, audio=False, resolution='720p',
                   cookies_browser=None, confirm_callback=None,
                   status_callback=None, progress_callback=None,
                   folder_created_callback=None):
    temporary_directory = None

    def report_status(message):
        if status_callback:
            status_callback(message)
        else:
            print(message)

    try:
        if getattr(sys, 'frozen', False):
            project_path = Path(sys.executable).parent
        else:
            project_path = Path(__file__).parent

        ffmpeg_path = project_path / 'ffmpeg' / 'ffmpeg.exe'
        
        if not ffmpeg_path.exists():
            raise FileNotFoundError(f"ffmpeg.exe no se encuentra en {ffmpeg_path}")

        temporary_directory = tempfile.TemporaryDirectory(
            prefix='yt_downloader_'
        )
        ydl_opts = {
            'outtmpl': str(get_download_directory() / '%(title)s.%(ext)s'),
            'paths': {
                'home': str(get_download_directory()),
                'temp': temporary_directory.name,
            },
            'ffmpeg_location': str(project_path / 'ffmpeg'),
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [
                lambda data: progress_hook(data, progress_callback)
            ],
        }

        if cookies_browser:
            ydl_opts['cookiesfrombrowser'] = (cookies_browser,)

        if video_index is not None:
            if video_index < 1:
                return 'El índice debe ser un número mayor que 0.'

        if audio:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            height_filter = f'[height<={resolution}]' if resolution else ''
            ydl_opts['format'] = (
                f'bestvideo[ext=mp4][vcodec^=avc1]{height_filter}+'
                f'bestaudio[ext=m4a][acodec^=mp4a]'
                f'/best[ext=mp4][vcodec^=avc1][acodec^=mp4a]{height_filter}'
            )
            ydl_opts['merge_output_format'] = 'mp4'

        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            linked_video_url = (
                get_playlist_video_url(url, video_index)
                if video_index is not None
                else None
            )
            if linked_video_url:
                ydl.params['noplaylist'] = True
                selected_info = ydl.extract_info(
                    linked_video_url,
                    download=False,
                )
                title = selected_info.get('title')
                selection_label = f'Índice {video_index} del mix'
                report_status(f'{selection_label}: {title or linked_video_url}')
                if not confirm_video(
                    title or linked_video_url,
                    video_index,
                    confirm_callback,
                ):
                    return 'Descarga cancelada; no se descargó ningún archivo.'
                download_to_desktop(
                    ydl,
                    [linked_video_url],
                    status_callback=status_callback,
                    folder_created_callback=folder_created_callback,
                )
                return f"Descargado: {title or 'video'}"

            info_dict = ydl.extract_info(
                url,
                download=False,
                process=video_index is None,
            )
            if video_index is not None:
                entries = info_dict.get('entries')
                if entries is None:
                    if video_index != 1 or info_dict.get('_type') == 'playlist':
                        return 'No se encontró esa posición en la playlist o mix.'
                    video_id = info_dict.get('id')
                    if not video_id or video_id.startswith('RD'):
                        return (
                            f'No se pudo identificar el video de la posición '
                            f'{video_index}; no se inició la descarga.'
                        )
                    video_url = f'https://www.youtube.com/watch?v={video_id}'
                    title = info_dict.get('title')
                else:
                    playlist_entries = list(entries)
                    report_status(
                        f'Mix detectado: {len(playlist_entries)} posiciones.'
                    )

                    while True:
                        if video_index < 1 or video_index > len(playlist_entries):
                            if confirm_callback:
                                return (
                                    f'Índice fuera de rango. El mix tiene '
                                    f'{len(playlist_entries)} posiciones.'
                                )
                            print(
                                f'Índice fuera de rango. El mix tiene '
                                f'{len(playlist_entries)} posiciones.'
                            )
                            choice = input('Elige un índice de la lista: ').strip()
                            if not choice.isdecimal():
                                print('Ingresa un índice numérico.')
                                continue
                            video_index = int(choice)
                            continue

                        selected_entry = playlist_entries[video_index - 1]
                        if not selected_entry:
                            if confirm_callback:
                                return (
                                    f'No se encontró un video disponible en la '
                                    f'posición {video_index}.'
                                )
                            print(f'La posición {video_index} no está disponible.')
                            choice = input('Elige otro índice: ').strip()
                            if not choice.isdecimal():
                                print('Ingresa un índice numérico.')
                                continue
                            video_index = int(choice)
                            continue

                        video_id = selected_entry.get('id')
                        if not video_id or video_id.startswith('RD'):
                            return (
                                f'No se pudo identificar el video de la posición '
                                f'{video_index}; no se inició la descarga.'
                            )
                        title = selected_entry.get('title') or 'título no disponible'
                        report_status(f'Selección actual: {video_index}. {title}')
                        if confirm_video(title, video_index, confirm_callback):
                            video_url = (
                                f'https://www.youtube.com/watch?v={video_id}'
                            )
                            break
                        if confirm_callback:
                            return 'Descarga cancelada; no se descargó ningún archivo.'
                        choice = input(
                            'Ingresa el índice correcto de la lista mostrada: '
                        ).strip()
                        if not choice.isdecimal():
                            print('Ingresa un índice numérico.')
                            continue
                        video_index = int(choice)

                if entries is None:
                    report_status(f'Video seleccionado: {title or video_url}')
                else:
                    report_status(
                        f'Índice {video_index} seleccionado: {title or video_url}'
                    )
                ydl.params['noplaylist'] = True
                download_to_desktop(
                    ydl,
                    [video_url],
                    status_callback=status_callback,
                    folder_created_callback=folder_created_callback,
                )
                title = title or f'video en la posición {video_index} del mix'
            else:
                download_to_desktop(
                    ydl,
                    [url],
                    status_callback=status_callback,
                    folder_created_callback=folder_created_callback,
                )
                title = info_dict.get('title')

            return f"Descargado: {title or 'video'}"
    except ytdlp.utils.DownloadError:
        raise
    except AttributeError as e:
        if cookies_browser and is_cookie_decode_error(str(e)):
            raise
        return f'Ocurrió un error: {e}'
    except Exception as e:
        return f'Ocurrió un error: {e}'
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()


def confirm_video(title, video_index, confirm_callback=None):
    if confirm_callback:
        return confirm_callback(title, video_index)
    return input(
        f'¿Descargar "{title}" (índice {video_index})? (s/n): '
    ).strip().lower() == 's'


def get_download_directory():
    if sys.platform == 'win32':
        desktop_path = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.shell32.SHGetFolderPathW(
            None,
            0x10,
            None,
            0,
            desktop_path,
        )
        if result != 0 or not desktop_path.value:
            raise OSError(
                f'Windows no pudo localizar la carpeta Escritorio (HRESULT {result}).'
            )
        return Path(desktop_path.value) / 'YT_Downloader'

    return Path.home() / 'Desktop' / 'YT_Downloader'


def download_to_desktop(
    ydl,
    urls,
    status_callback=None,
    folder_created_callback=None,
):
    download_directory = get_download_directory()
    folder_will_be_created = not download_directory.exists()
    download_directory.mkdir(parents=True, exist_ok=True)
    if folder_will_be_created:
        message = (
            f'\nSe creó la carpeta de descargas: {download_directory}\n'
            'Desde ahora, los archivos finales se guardarán ahí.'
        )
        if folder_created_callback:
            folder_created_callback(message)
        elif status_callback:
            status_callback(message)
        else:
            print(message)
    ydl.download(urls)


def get_playlist_details(url):
    query = parse_qs(urlparse(url).query)
    playlist_id = query.get('list', [None])[0]
    if not playlist_id:
        return False, None

    if query.get('start_radio', [None])[0] == '1':
        return True, 1

    index_value = query.get('index', [None])[0]
    try:
        video_index = int(index_value) if index_value else None
    except ValueError:
        video_index = None

    return True, video_index


def get_playlist_video_url(url, video_index):
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    if not query.get('list'):
        return None

    url_index = query.get('index', [None])[0]
    is_radio_start = query.get('start_radio', [None])[0] == '1'
    if url_index != str(video_index) and not (is_radio_start and video_index == 1):
        return None

    video_id = query.get('v', [None])[0]
    if not video_id and parsed_url.hostname in {'youtu.be', 'www.youtu.be'}:
        video_id = parsed_url.path.strip('/').split('/')[0]
    if not video_id or not re.fullmatch(r'[\w-]{11}', video_id, flags=re.ASCII):
        return None

    return f'https://www.youtube.com/watch?v={video_id}'


def is_youtube_bot_check_error(message):
    normalized_message = message.lower().replace('’', "'")
    return 'sign in to confirm' in normalized_message and 'not a bot' in normalized_message


def is_youtube_403_error(message):
    normalized_message = message.lower()
    return 'http error 403' in normalized_message or (
        '403' in normalized_message and 'forbidden' in normalized_message
    )


def is_cookie_database_error(message):
    normalized_message = message.lower()
    return 'could not copy' in normalized_message and 'cookie database' in normalized_message


def is_cookie_decode_error(message):
    return "'NoneType' object has no attribute 'decode'" in message


def download_with_bot_check_retry(
    url,
    video_index,
    audio,
    resolution,
    confirm_callback=None,
    status_callback=None,
    progress_callback=None,
    browser_callback=None,
    folder_created_callback=None,
):
    def attempt_download(cookies_browser=None):
        return download_video(
            url,
            video_index=video_index,
            audio=audio,
            resolution=resolution,
            cookies_browser=cookies_browser,
            confirm_callback=confirm_callback,
            status_callback=status_callback,
            progress_callback=progress_callback,
            folder_created_callback=folder_created_callback,
        )

    try:
        return attempt_download()
    except ytdlp.utils.DownloadError as error:
        error_message = str(error)
        bot_check_error = is_youtube_bot_check_error(error_message)
        forbidden_error = is_youtube_403_error(error_message)
        if not (bot_check_error or forbidden_error):
            return f'Ocurrió un error: {error_message}'

        if bot_check_error:
            message = (
                '\nYouTube requiere confirmar que la solicitud no es automatizada. '
                'Puedes reintentar usando las cookies de una sesión iniciada en tu navegador.'
            )
        else:
            message = (
                '\nYouTube rechazó la descarga con HTTP 403. Puedes reintentar '
                'con las cookies de una sesión iniciada en tu navegador. Si '
                'continúa, actualiza yt-dlp y vuelve a compilar el ejecutable.'
            )
        message += (
            '\nCierra completamente el navegador elegido antes de continuar. '
            'Asegúrate también de que no siga ejecutándose en segundo plano.'
        )
        if status_callback:
            status_callback(message)
        else:
            print(message)
        browser_choices = {
            '1': 'chrome',
            '2': 'edge',
            '3': 'firefox',
            '4': 'brave',
        }
        last_error_message = error_message
        while True:
            if browser_callback:
                cookies_browser = browser_callback(last_error_message)
            else:
                print(
                    'Navegador: (1) Chrome (2) Edge (3) Firefox '
                    '(4) Brave (0) Cancelar'
                )
                choice = input('Selecciona una opción: ').strip()
                if choice == '0':
                    cookies_browser = None
                else:
                    cookies_browser = browser_choices.get(choice)

            if not cookies_browser:
                return f'Ocurrió un error: {last_error_message}'

            try:
                return attempt_download(cookies_browser)
            except ytdlp.utils.DownloadError as cookie_error:
                cookie_error_message = str(cookie_error)
                if not is_cookie_database_error(cookie_error_message):
                    return f'Ocurrió un error: {cookie_error_message}'

                last_error_message = cookie_error_message
                message = (
                    f'No se pudo copiar la base de cookies de '
                    f'{cookies_browser.capitalize()}. Cierra el navegador por '
                    'completo y prueba de nuevo, o selecciona otro navegador. '
                    f'Detalle: {cookie_error_message}'
                )
                if status_callback:
                    status_callback(message)
                else:
                    print(message)
            except AttributeError as cookie_error:
                cookie_error_message = str(cookie_error)
                if not is_cookie_decode_error(cookie_error_message):
                    raise

                last_error_message = cookie_error_message
                message = (
                    f'yt-dlp no pudo descifrar las cookies de '
                    f'{cookies_browser.capitalize()}. Actualiza yt-dlp o '
                    'prueba otro navegador con YouTube iniciado. '
                    f'Detalle: {cookie_error_message}'
                )
                if status_callback:
                    status_callback(message)
                else:
                    print(message)


def validate_youtube_url(url):
    regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(regex, url)

def progress_hook(d, progress_callback=None):
    if progress_callback:
        progress_callback(d)
        return

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

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.is_downloading = False
        self.root.title('YT Downloader')
        self.root.geometry('700x470')
        self.root.minsize(620, 430)
        self.root.configure(bg='#f3f6fb')
        self.root.protocol('WM_DELETE_WINDOW', self.close)

        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('App.TFrame', background='#f3f6fb')
        style.configure(
            'Title.TLabel',
            background='#f3f6fb',
            foreground='#152238',
            font=('Segoe UI', 23, 'bold'),
        )
        style.configure(
            'Subtitle.TLabel',
            background='#f3f6fb',
            foreground='#5c6b80',
            font=('Segoe UI', 10),
        )
        style.configure(
            'Section.TLabel',
            background='#f3f6fb',
            foreground='#23344d',
            font=('Segoe UI', 10, 'bold'),
        )
        style.configure('App.TRadiobutton', background='#f3f6fb')
        style.configure(
            'Accent.TButton',
            font=('Segoe UI', 10, 'bold'),
            padding=(14, 9),
            foreground='white',
            background='#d92344',
        )
        style.map(
            'Accent.TButton',
            background=[('active', '#b81d38'), ('disabled', '#aab4c2')],
        )

        frame = ttk.Frame(root, style='App.TFrame', padding=(28, 24))
        frame.pack(fill='both', expand=True)

        ttk.Label(
            frame,
            text='YT Downloader',
            style='Title.TLabel',
            anchor='center',
            justify='center',
        ).pack(fill='x', pady=(0, 28))

        ttk.Label(frame, text='Enlace de YouTube', style='Section.TLabel').pack(
            anchor='w'
        )
        link_row = ttk.Frame(frame, style='App.TFrame')
        link_row.pack(fill='x', pady=(7, 18))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(link_row, textvariable=self.url_var)
        self.url_entry.pack(side='left', fill='x', expand=True, ipady=7)
        ttk.Button(link_row, text='Pegar', command=self.paste_url).pack(
            side='left', padx=(8, 0), ipady=3
        )
        self.url_entry.bind('<Return>', lambda _event: self.start_download())

        options = ttk.Frame(frame, style='App.TFrame')
        options.pack(fill='x')
        self.format_var = tk.StringVar(value='mp4')
        format_row = ttk.Frame(options, style='App.TFrame')
        format_row.pack(fill='x', pady=(0, 20))
        ttk.Radiobutton(
            format_row,
            text='Audio MP3',
            variable=self.format_var,
            value='mp3',
            style='App.TRadiobutton',
            command=self.update_resolution_state,
        ).pack(side='left', padx=(0, 18))
        ttk.Radiobutton(
            format_row,
            text='Video MP4 (H.264)',
            variable=self.format_var,
            value='mp4',
            style='App.TRadiobutton',
            command=self.update_resolution_state,
        ).pack(side='left', padx=(0, 18))
        ttk.Label(
            format_row,
            text='Resolución:',
            style='Section.TLabel',
        ).pack(side='left', padx=(0, 7))
        self.resolution_var = tk.StringVar(value='720p')
        self.resolution_box = ttk.Combobox(
            format_row,
            textvariable=self.resolution_var,
            values=('360p', '480p', '720p', '1080p', '1440p', '2160p'),
            state='readonly',
            width=12,
        )
        self.resolution_box.pack(side='left')
        self.update_resolution_state()

        folder_row = ttk.Frame(frame, style='App.TFrame')
        folder_row.pack(fill='x', pady=(2, 16))
        ttk.Label(
            folder_row,
            text=f'Los archivos finales se guardarán en: {get_download_directory()}',
            style='Subtitle.TLabel',
        ).pack(side='left', fill='x', expand=True, anchor='w')
        ttk.Button(
            folder_row,
            text='Abrir carpeta',
            command=self.open_download_folder,
        ).pack(side='right')

        self.progress = ttk.Progressbar(
            frame,
            mode='determinate',
            maximum=100,
        )
        self.progress.pack(fill='x', pady=(4, 8))
        self.status_var = tk.StringVar(value='Listo para descargar.')
        self.status_label = ttk.Label(
            frame,
            textvariable=self.status_var,
            style='Subtitle.TLabel',
            wraplength=640,
        )
        self.status_label.pack(anchor='w', pady=(0, 14))

        self.download_button = ttk.Button(
            frame,
            text='Descargar',
            style='Accent.TButton',
            command=self.start_download,
        )
        self.download_button.pack(anchor='center')
        self.url_entry.focus_set()

    def paste_url(self):
        try:
            clipboard_text = self.root.clipboard_get()
        except tk.TclError:
            self.set_status('No hay texto disponible en el portapapeles.', error=True)
            return
        self.url_var.set(clipboard_text.strip())
        self.url_entry.icursor('end')

    def update_resolution_state(self):
        self.resolution_box.configure(
            state='readonly' if self.format_var.get() == 'mp4' else 'disabled'
        )

    def open_download_folder(self):
        folder = get_download_directory()
        folder_will_be_created = not folder.exists()
        folder.mkdir(parents=True, exist_ok=True)
        if folder_will_be_created:
            messagebox.showinfo(
                'Carpeta creada',
                f'Se creó la carpeta de descargas: {folder}.\n'
                'Desde ahora, los archivos finales se guardarán ahí.',
                parent=self.root,
            )
        if sys.platform == 'win32':
            import os
            os.startfile(folder)
        else:
            messagebox.showinfo('Carpeta de descargas', str(folder), parent=self.root)

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        if not validate_youtube_url(url):
            messagebox.showerror(
                'Enlace no válido',
                'Ingresa una URL válida de YouTube.',
                parent=self.root,
            )
            self.url_entry.focus_set()
            return

        is_playlist, video_index = get_playlist_details(url)
        if is_playlist and video_index is None:
            video_index = simpledialog.askinteger(
                'Índice del mix',
                'La URL es una playlist o un mix. ¿Qué índice quieres descargar?',
                minvalue=1,
                parent=self.root,
            )
            if video_index is None:
                return

        audio = self.format_var.get() == 'mp3'
        resolution = self.resolution_var.get() if not audio else '720p'
        if is_playlist and video_index is not None:
            query = parse_qs(urlparse(url).query)
            if query.get('start_radio', [None])[0] == '1':
                selection_status = 'Mix de radio; se usará el índice 1.'
            else:
                selection_status = f'Mix detectado; se usará el índice {video_index}.'
        else:
            selection_status = 'Video individual detectado.'

        self.is_downloading = True
        self.download_button.configure(state='disabled', text='Descargando…')
        self.progress.configure(value=0)
        self.set_status(f'Preparando descarga… {selection_status}')
        threading.Thread(
            target=self.download_worker,
            args=(url, video_index, audio, resolution),
            daemon=True,
        ).start()

    def download_worker(self, url, video_index, audio, resolution):
        try:
            result = download_with_bot_check_retry(
                url,
                video_index=video_index,
                audio=audio,
                resolution=resolution,
                confirm_callback=self.confirm_selection,
                status_callback=self.report_status,
                progress_callback=self.report_progress,
                browser_callback=self.choose_browser,
                folder_created_callback=self.report_folder_created,
            )
        except Exception as error:
            result = f'Ocurrió un error: {error}'
        self.root.after(0, self.finish_download, result)

    def ask_on_ui_thread(self, callback):
        response = []
        completed = threading.Event()

        def run_callback():
            try:
                response.append(callback())
            finally:
                completed.set()

        self.root.after(0, run_callback)
        completed.wait()
        return response[0] if response else None

    def confirm_selection(self, title, video_index):
        return self.ask_on_ui_thread(
            lambda: messagebox.askyesno(
                'Confirmar video',
                f'Índice {video_index}:\n\n{title}\n\n¿Quieres descargar este video?',
                parent=self.root,
            )
        )

    def choose_browser(self, last_error):
        return self.ask_on_ui_thread(lambda: self.show_browser_dialog(last_error))

    def report_folder_created(self, message):
        self.ask_on_ui_thread(
            lambda: messagebox.showinfo(
                'Carpeta creada',
                message.strip(),
                parent=self.root,
            )
        )

    def show_browser_dialog(self, last_error):
        dialog = tk.Toplevel(self.root)
        dialog.title('Reintentar con cookies')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        result = {'browser': None}

        body = ttk.Frame(dialog, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(
            body,
            text=(
                'YouTube rechazó la descarga. Puedes reintentar usando las '
                'cookies de un navegador con sesión iniciada. Cierra ese '
                'navegador antes de seleccionarlo.\n\n'
                f'Detalle: {last_error}'
            ),
            wraplength=420,
            justify='left',
        ).pack(anchor='w', pady=(0, 14))
        buttons = ttk.Frame(body)
        buttons.pack(fill='x')

        def select(browser):
            result['browser'] = browser
            dialog.destroy()

        for browser in ('chrome', 'edge', 'firefox', 'brave'):
            ttk.Button(
                buttons,
                text=browser.capitalize(),
                command=lambda selected=browser: select(selected),
            ).pack(side='left', padx=(0, 6))
        ttk.Button(
            buttons,
            text='Cancelar',
            command=lambda: select(None),
        ).pack(side='right')
        dialog.protocol('WM_DELETE_WINDOW', lambda: select(None))
        dialog.wait_window()
        return result['browser']

    def report_status(self, message):
        self.root.after(0, self.set_status, message.strip())

    def report_progress(self, data):
        if data.get('status') == 'downloading':
            total = data.get('total_bytes') or data.get('total_bytes_estimate')
            downloaded = data.get('downloaded_bytes', 0)
            if total:
                percentage = downloaded / total * 100
                self.root.after(
                    0,
                    lambda value=percentage: self.progress.configure(value=value),
                )
                self.report_status(f'Descargando… {percentage:.1f}%')
        elif data.get('status') == 'finished':
            self.root.after(0, lambda: self.progress.configure(value=100))
            self.report_status('Descarga recibida; finalizando conversión…')

    def set_status(self, message, error=False, success=False):
        self.status_var.set(message)
        foreground = '#b4233d' if error else '#167548' if success else '#5c6b80'
        self.status_label.configure(foreground=foreground)

    def finish_download(self, result):
        self.is_downloading = False
        self.download_button.configure(state='normal', text='Descargar')
        is_success = result.startswith('Descargado:')
        was_cancelled = result.startswith('Descarga cancelada')
        self.set_status(
            result,
            error=not is_success and not was_cancelled,
            success=is_success,
        )
        if is_success:
            self.progress.configure(value=100)
            self.url_var.set('')
            self.url_entry.focus_set()
        else:
            self.progress.configure(value=0)

    def close(self):
        if self.is_downloading:
            messagebox.showinfo(
                'Descarga en curso',
                'Espera a que termine la descarga antes de cerrar la aplicación.',
                parent=self.root,
            )
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
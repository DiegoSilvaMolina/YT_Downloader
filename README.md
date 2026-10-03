# YT_Downloader V1.2
Script para descargar videos/musica de youtube (playlist, mix y videos individuales) en formatos MP3 y MP4 asignando la resolución deseada 

## Características

- Descarga de audio en formato MP3 (HD).
- Descarga de video en formato MP4 (720p prederminado).
- Interfaz fácil de usar.
- Mensajes de estado y errores claros.
- permite descargas desde playlist o mix generados por youtube

## Clona el repositorio

```
git clone https://github.com/DiegoSilvaMolina/YT_downloader.git
cd YT_downloader
```

## Ruta
En la ruta dist/ se encuentra el archivo ".exe" donde podrá ejecutar el script

## Uso

Abre `yt_downloader.exe`, pega la URL de YouTube y selecciona video MP4 o audio
MP3. Para playlists y mixes se usa el índice de la URL o se solicita uno si no
está presente; antes de descargar, la aplicación muestra el título para
confirmarlo. Para un video individual no se solicita índice.

Al terminar, la ventana queda abierta y el campo del enlace se limpia para que
puedas pegar el siguiente video y pulsar **Descargar**. La interfaz muestra el
progreso y el estado sin pedir que presiones Enter.

> [!NOTA]
> Los videos y audios se descargaran en alta definición (HD)

## Carpeta de descargas

Al comenzar la primera descarga, el programa detecta la ubicación Escritorio de
Windows para el usuario actual y crea allí `YT_Downloader`. Esto respeta
ubicaciones redirigidas, por ejemplo a otra unidad o OneDrive. Los archivos
finales se guardan ahí; los temporales y las conversiones intermedias se
procesan en una carpeta temporal del sistema, que se limpia al terminar. Las
descargas que ya existían no se mueven. Al crear la carpeta por primera vez, el
programa muestra su ruta y avisa que las descargas futuras se guardarán ahí.

## Detección de videos y mixes

El programa detecta las URL con parámetro `list` como playlist o mix. Si la URL
incluye `index`, utiliza ese índice automáticamente; si no, pregunta cuál video
descargar. En URL que contienen `list` y `start_radio=1`, el programa interpreta
el índice como 1 y usa el ID `v` de esa URL, aunque también haya un parámetro
`index` distinto. Muestra el título y pide confirmación antes de descargar. Las
URL de videos individuales no solicitan índice y comienzan directamente la
descarga.

## Error "Sign in to confirm you're not a bot"

YouTube puede requerir una sesión iniciada para algunas descargas. Si aparece ese
error, el programa permite reintentar usando las cookies de Chrome, Edge, Firefox
o Brave. Inicia sesión en YouTube en el navegador elegido y ciérralo antes de
seleccionarlo en el programa. Si aparece `Could not copy Chrome cookie database`,
cierra también los procesos en segundo plano desde el Administrador de tareas y
vuelve a elegir el navegador; también puedes probar otro navegador donde tengas
sesión iniciada. Las cookies se leen localmente desde tu equipo.
Si aparece `'NoneType' object has no attribute 'decode'`, actualiza yt-dlp; si
persiste, prueba Edge, Firefox o Brave con la sesión de YouTube iniciada.
Si la descarga falla con `HTTP Error 403: Forbidden`, el programa también
permite reintentar con cookies del navegador. Si no se resuelve, actualiza yt-dlp
y recompila el ejecutable para incluir la versión nueva.
Al indicar un índice del mix, el programa descarga únicamente el video
seleccionado, no la playlist completa. Si la URL incluye `list` e `index` y el
índice ingresado coincide con `index`, se usa el ID de video contenido en esa
misma URL. Para otros enlaces, se muestra la lista que yt-dlp encontró; confirma
el título antes de descargar.
La opción MP4 elige video H.264/AVC y audio AAC para evitar AV1, que algunos
reproductores requieren instalar aparte. Si YouTube no ofrece una combinación
compatible, yt-dlp mostrará un error en vez de guardar un archivo AV1 como MP4.

Al seleccionar un índice, usa numeración desde 1 (1 corresponde al primer video
del mix). Si ejecutas el `.exe` de `dist/`, debes regenerarlo para incluir los
cambios. En Windows, actualiza yt-dlp y vuelve a empaquetar desde la raíz del
repositorio:

```powershell
python -m pip install --upgrade yt-dlp pyinstaller
pyinstaller --clean yt_downloader.spec
```

PyInstaller genera automáticamente `build/` y `dist/` durante la compilación.
La carpeta `build/` es temporal y está excluida del repositorio por `.gitignore`.

## Contribuciones
Las contribuciones son bienvenidas. Si encuentras algún error, siéntete libre de abrir un issue o pull request para mejorarlo.

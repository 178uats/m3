import os
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView, FileChooserIconView
from kivy.uix.spinner import Spinner
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

CONFIG_FILE = "config_mp3.json"

class MP3Player(BoxLayout):
    def __init__(self, **kwargs):
        super(MP3Player, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 8

        self.sound = None
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.is_looping = False
        self.selected_folder = self.load_saved_folder()

        # Título
        self.title_label = Label(
            text="Reproductor MP3 Local", 
            size_hint_y=0.07, 
            font_size='18sp', 
            bold=True
        )
        self.add_widget(self.title_label)

        # Estado / Canción actual
        self.status_label = Label(
            text="Selecciona una carpeta" if not self.selected_folder else f"Carpeta: {self.selected_folder}", 
            size_hint_y=0.08, 
            font_size='13sp'
        )
        self.add_widget(self.status_label)

        # Barra Superior: Cambiar Carpeta y Ordenar
        top_bar = BoxLayout(size_hint_y=0.09, spacing=5)
        
        self.btn_change_folder = Button(
            text="📁 Cambiar Carpeta", 
            on_press=self.open_folder_selector,
            size_hint_x=0.5
        )
        
        # Selector para ordenar
        self.sort_spinner = Spinner(
            text="Ordenar por...",
            values=("Nombre (A-Z)", "Más Recientes", "Mayor Tamaño"),
            size_hint_x=0.5
        )
        self.sort_spinner.bind(text=self.on_sort_change)

        top_bar.add_widget(self.btn_change_folder)
        top_bar.add_widget(self.sort_spinner)
        self.add_widget(top_bar)

        # Visor de archivos / Seleccionador
        initial_path = self.selected_folder if self.selected_folder else os.path.expanduser('~')
        self.file_chooser = FileChooserListView(
            path=initial_path,
            filters=['*.mp3', '*.wav', '*.ogg'],
            size_hint_y=0.52
        )
        self.file_chooser.bind(on_submit=self.on_file_selected)
        self.add_widget(self.file_chooser)

        # Controles de Reproducción
        controls_layout = BoxLayout(size_hint_y=0.12, spacing=5)

        self.btn_prev = Button(text="<< Ant", on_press=self.play_previous)
        self.btn_play = Button(text="Play / Pausa", on_press=self.toggle_play)
        self.btn_stop = Button(text="Stop", on_press=self.stop)
        self.btn_next = Button(text="Sig >>", on_press=self.play_next)

        controls_layout.add_widget(self.btn_prev)
        controls_layout.add_widget(self.btn_play)
        controls_layout.add_widget(self.btn_stop)
        controls_layout.add_widget(self.btn_next)

        self.add_widget(controls_layout)

        # Opciones extra (Bucle)
        options_layout = BoxLayout(size_hint_y=0.12, spacing=5)
        self.btn_loop = Button(
            text="Bucle: DESACTIVADO", 
            on_press=self.toggle_loop,
            background_color=(0.3, 0.3, 0.3, 1)
        )
        options_layout.add_widget(self.btn_loop)
        self.add_widget(options_layout)

        # Guardar lista inicial si ya existe carpeta
        if self.selected_folder and os.path.exists(self.selected_folder):
            self.refresh_playlist()

        Clock.schedule_interval(self.check_sound_status, 0.5)

    # --- Gestión de Configuración (Persistencia de Carpeta) ---
    def load_saved_folder(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    folder = data.get("folder", "")
                    if os.path.exists(folder):
                        return folder
            except Exception:
                pass
        return ""

    def save_folder(self, folder_path):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"folder": folder_path}, f)

    def open_folder_selector(self, instance):
        # Permite seleccionar directorio
        self.file_chooser.dirselect = True
        self.file_chooser.filters = []
        self.status_label.text = "Haz doble clic en una carpeta para guardarla"
        self.file_chooser.bind(on_submit=self.confirm_folder_selection)

    def confirm_folder_selection(self, chooser, selection, touch):
        if selection:
            path = selection[0]
            if os.path.isdir(path):
                self.selected_folder = path
                self.save_folder(path)
                self.file_chooser.dirselect = False
                self.file_chooser.filters = ['*.mp3', '*.wav', '*.ogg']
                self.file_chooser.path = path
                self.status_label.text = f"Carpeta guardada: {os.path.basename(path)}"
                self.refresh_playlist()
                self.file_chooser.unbind(on_submit=self.confirm_folder_selection)

    # --- Ordenamiento y Lista de Reproducción ---
    def refresh_playlist(self):
        if not self.selected_folder or not os.path.exists(self.selected_folder):
            return

        valid_exts = ('.mp3', '.wav', '.ogg')
        files = [
            os.path.join(self.selected_folder, f) 
            for f in os.listdir(self.selected_folder) 
            if f.lower().endswith(valid_exts)
        ]

        sort_type = self.sort_spinner.text
        if sort_type == "Más Recientes":
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        elif sort_type == "Mayor Tamaño":
            files.sort(key=lambda x: os.path.getsize(x), reverse=True)
        else:  # Nombre (A-Z)
            files.sort(key=lambda x: os.path.basename(x).lower())

        self.playlist = files

    def on_sort_change(self, spinner, text):
        self.refresh_playlist()
        self.status_label.text = f"Ordenado por: {text}"

    # --- Métodos de Audio y Reproducción ---
    def load_audio(self, filepath):
        if self.sound:
            self.sound.stop()
            self.sound.unload()

        self.sound = SoundLoader.load(filepath)
        if self.sound:
            self.sound.loop = self.is_looping
            filename = os.path.basename(filepath)
            self.status_label.text = f"Sonando: {filename}"
            self.sound.play()
            self.is_playing = True
        else:
            self.status_label.text = "Error al cargar audio"

    def on_file_selected(self, chooser, selection, touch):
        if selection and not chooser.dirselect:
            selected_file = selection[0]
            if selected_file in self.playlist:
                self.current_index = self.playlist.index(selected_file)
            self.load_audio(selected_file)

    def toggle_loop(self, instance):
        self.is_looping = not self.is_looping
        if self.is_looping:
            self.btn_loop.text = "Bucle: ACTIVADO 🔂"
            self.btn_loop.background_color = (0.2, 0.7, 0.3, 1)
        else:
            self.btn_loop.text = "Bucle: DESACTIVADO"
            self.btn_loop.background_color = (0.3, 0.3, 0.3, 1)

        if self.sound:
            self.sound.loop = self.is_looping

    def check_sound_status(self, dt):
        if self.sound and self.sound.state == 'stop' and self.is_playing and not self.is_looping:
            self.play_next(None)

    def toggle_play(self, instance):
        if not self.sound and self.file_chooser.selection:
            self.on_file_selected(self.file_chooser, self.file_chooser.selection, None)
            return

        if self.sound:
            if self.sound.state == 'play':
                self.sound.stop()
                self.is_playing = False
                self.status_label.text = "Pausado"
            else:
                self.sound.play()
                self.is_playing = True
                filename = os.path.basename(self.file_chooser.selection[0] if self.file_chooser.selection else "")
                self.status_label.text = f"Sonando: {filename}"

    def stop(self, instance):
        if self.sound:
            self.sound.stop()
            self.is_playing = False
            self.status_label.text = "Detenido"

    def play_next(self, instance):
        if self.playlist and self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.load_audio(self.playlist[self.current_index])

    def play_previous(self, instance):
        if self.playlist and self.current_index > 0:
            self.current_index -= 1
            self.load_audio(self.playlist[self.current_index])

class LocalPlayerApp(App):
    def build(self):
        self.title = "Reproductor MP3 Local"
        return MP3Player()

if __name__ == '__main__':
    LocalPlayerApp().run()
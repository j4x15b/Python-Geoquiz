"""
Das Programm lässt den Benutzer Hauptstädte auf der Weltkarte finden.

Dieses Programm liest eine (vorbereitete) json-Datei mit Hauptstädten der Welt, deren Koordinaten,
sowie die Länder und Kontinente ein. Die Liste entstand aus einem Abgleich von mehreren Wikipedia-Listen,
sowie von einer Liste des CIA und einer GitHub-Seite und
wurde mithilfe von ChatGpt überprüft und ins .json-Format gewandelt:

(Stand: 30.04.2025
    https://en.wikipedia.org/wiki/List_of_national_capitals,
    https://de.wikipedia.org/wiki/Liste_der_Hauptst%C3%A4dte_der_Erde,
    https://www.cia.gov/the-world-factbook/field/capital/,
    sowie https://gist.github.com/ofou/df09a6834a8421b4f376c875194915c9
)
Programmablauf und Features:
Die Benutzer werden mit Punktestand aus einer weiteren Datei geladen (und wenn mit Quit beendet wird, wird gespeichert).
Der Benutzer gibt einen Namen an, sucht sich die Kontinente aus und soll dann immer eine Hauptstadt finden,
dazu klickt er auf die projizierte Weltkarte und versucht, so nahe wie möglich an die Stadt zu klicken.
Es ist möglich, mithilfe des Mausrads zu zoomen.
Der Klick auf die Weltkarte wird über ein button-press-event registriert und ausgewertet,
der Abstand zwischen Klickpunkt und Stadt wird berechnet.
Wenn der Klickpunkt weniger als 1000km entfernt ist, war die Antwort richtig, der Spieler bekommt einen Punkt.
Bei drei erfolglosen Versuchen gilt die Antwort als falsch beantwortet.
Nach 10 Runden wird eine Auswertung der Antworten eingeblendet und das Spiel beginnt von vorn.

Achtung, ich habe cartopy verwendet, das muss erst installiert werden.
Es gibt eine Alternativversion mit matplotlib und einem Hintergrundbild, die funktioniert aber nicht so gut.
Dafür müssen beim import, bei der Initialisierung der Klasse Hauptstadtplotter und bei der Methode plot_world
ein paar Zeilen auskommentiert werden. Einfach nach "cartopy" suchen
"""

#Datenverarbeitung
import json
import random

#Abstandsberechnung
from math import radians, sin, cos, sqrt, atan2
#from geopy.distance import geodesic

#Kartenprojektion
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
#import matplotlib.image as mpimg #für Weltkarte mit Matplotlib
import cartopy.crs as ccrs #für Weltkarte mit cartopy
import cartopy.feature as cfeature #für Weltkarte mit cartopy

"""Auslesen der Spieldateien: Hauptstadtliste und Spielerliste"""
with open('./capital_continent_country_data.json', 'r') as staedte:
    capitals = json.load(staedte)
with open('./spieler_score.json', 'r') as spieler_logbuch:
    spieler = json.load(spieler_logbuch)
kontinent_liste = []
for eintrag in capitals:
    if eintrag["Kontinent"] not in kontinent_liste:
        kontinent_liste.append(eintrag["Kontinent"])


class Hauptstadtplotter():
    """Diese Klasse plottet eine Weltkarte und zeigt darauf Städte an."""
    def __init__(self, master, main_window):

        self.master = master
        self.main_window = main_window
        self.fig = plt.Figure(figsize=(16, 10))

        # mit cartopy:
        self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree()) #mit cartopy
        #ohne cartopy:
        #self.ax = self.fig.add_subplot(1, 1, 1) #ohne cartopy

        self.fig.tight_layout()
        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.fig.canvas.mpl_connect('scroll_event', self.zoom)

        #Label im Hauptfenster, die durch die Klasse angesteuert werden
        self.label_kontinente = self.main_window.label_kontinente
        self.label_stadt = self.main_window.label_stadt
        self.label_counter =self.main_window.label_counter
        self.label_runde = self.main_window.label_runde

        #Auswertungslisten
        self.abgehakt = []
        self.ergebnisse = []

        #Spielvariablen
        self.gewonnen = False
        self.verloren = False
        self.all_capitals_on_screen = False
        self.cityName = ""
        self.runde = 0
        self.index = -1
        self.x = 0
        self.y = 0
        self.x_click = None
        self.y_click = None
        self.klickPoint = (self.y_click, self.x_click)
        self.klick_liste = []
        self.counter = 3

    def start_spiel(self):
        self.runde = 1
        self.random_capital()
        self.plot_world()

    def zufallszahl(self, minzahl, maxzahl):
        z = random.randint(minzahl, maxzahl)
        return z


    def random_capital(self):
        """Sucht eine zufällige Stadt aus.

            Eine zufällige indexzahl wird erstellt, geprüft, ob sie schon dran war und dann werden die Stadt-Eigenschaften
            aus der nach Kontinent gefilterten Liste zugewiesen: Koordinaten, Stadtname, Kontinentname und die dazugehörigen Labels werden aktualisiert
        """
        #print("neue Stadt, bisherige Städte", self.abgehakt)
        self.index = self.zufallszahl(0, len(self.main_window.filtered_capitals)-1)
        while(self.index in self.abgehakt):
            self.index = self.zufallszahl(0,len(self.main_window.filtered_capitals))

        self.x = self.main_window.filtered_capitals[self.index]['Längengrad']
        self.y = self.main_window.filtered_capitals[self.index]['Breitengrad']
        self.cityName = self.main_window.filtered_capitals[self.index]['Hauptstadt']
        self.kontinentName = self.main_window.filtered_capitals[self.index]['Kontinent']
        self.label_stadt.config(text = self.cityName)
        self.label_kontinente.config(text=self.kontinentName)
        plt.title(capitals[self.index]["Hauptstadt"])

    """Hier beginnen die Plot-Methoden: 
    Weltkarte, Klickpunkt, Linie zwischen Klickpunkt und Stadt, sowie alle Hauptstädte der ausgewählten Kontinente
    Sie sind jeweils einzeln als Methode ansteuerbar.    
    Für plot_world gibt es eine Version mit Cartopy-Features und eine mit einem Hintergrundbild
    Aktiviert ist die für cartopy, da sie stabiler läuft, genauer die Koordinaten darstellt und man besser heranzoomen kann.
    """
    def plot_world(self):
        """plottet die Weltkarte"""
        self.ax.clear()
        """diese Zeilen sind für die Worldmap MIT cartopy"""
        self.ax.add_feature(cfeature.BORDERS)
        self.ax.add_feature(cfeature.COASTLINE)
        self.ax.add_feature(cfeature.OCEAN)
        self.ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())
        """
        #diese Zeilen sind für die Worldmap OHNE cartopy:
        #img = mpimg.imread('world_map_300.png') #ebenfalls mitgeliefert: "world_map_600.png"
        #self.ax.axis('off')
        #self.ax.imshow(img, extent=[-180, 180, -90, 90], aspect='auto')
        """
        self.fig.canvas.draw()

    def plot_click_point(self):
        """plottet den Mausklick-Punkte"""
        if (self.x_click and self.y_click):
            city_click_x = [self.x, self.x_click]
            city_click_y = [self.y, self.y_click]
            self.ax.plot(self.x_click, self.y_click, '^')
        self.fig.canvas.draw()

    def plot_city_point(self):
        """plottet die Stadt"""
        self.ax.plot(self.x,self.y, 'o')
        self.ax.set_xlim(-180, 180)
        self.ax.set_ylim(-90, 90)
        self.fig.canvas.draw()

    def plot_line(self):
        """plottet eine Linie zwischen Klickpunkt und Stadt"""
        if (self.x_click and self.y_click):
            self.ax.plot(self.x_click, self.y_click, '^')
            city_click_x = [self.x, self.x_click]
            city_click_y = [self.y, self.y_click]
            self.ax.plot(city_click_x, city_click_y, linestyle="dotted")
        self.fig.canvas.draw()

    def plot_capitals(self):
        """Plottet die Positionen aller Hauptstädte der ausgewählten Kontinente"""
        if self.all_capitals_on_screen == False:
            self.all_capitals_on_screen = True
            self.plot_world()
            capital_list_x = []
            capital_list_y = []
            capital_name_list = []
            for i in range (len(self.main_window.filtered_capitals)):
                capital_list_x.append(self.main_window.filtered_capitals[i]['Längengrad'])
                capital_list_y.append(self.main_window.filtered_capitals[i]['Breitengrad'])
                capital_name_list.append(self.main_window.filtered_capitals[i]['Hauptstadt'])
            self.ax.scatter(capital_list_x, capital_list_y)
            self.fig.canvas.draw()
        else:
            self.all_capitals_on_screen = False
            self.plot_world()

    def counter_update(self):
        """Der Counter wird nach jeder Klickauswertung aktualisiert und gibt ein kurzes farbliches Feedback"""
        self.label_counter.config(text=f"Noch {self.counter} Versuche")
        if self.gewonnen == True:
            self.master.after(500, lambda: self.label_counter.config(background='green'))
        elif self.counter == 3:
            self.label_counter.config(background='red')
            self.master.after(500, lambda: self.label_counter.config(background='white'))
        elif self.counter == 2:
            self.label_counter.config(background='red')
            self.master.after(500, lambda: self.label_counter.config(background='white'))
            #self.label_counter.config(bg='green')
        elif self.counter == 1:
            self.label_counter.config(background='red')
            self.master.after(500, lambda: self.label_counter.config(background='yellow'))
        elif self.counter == 0:
            self.label_counter.config(background='red')


    def unlock(self):
        """Klicks auf die Karte sind am Ende der Runde gesperrt und werden hier wieder aufgehoben"""
        if self.gewonnen == True:
            self.gewonnen = False
        self.verloren = False

    def next_round(self):
        self.runde += 1
        self.main_window.label_runde.config(text=f"Runde: {self.runde} / 10")
        print("Runde:", self.runde)
        self.abgehakt.append(self.index)
        self.ergebnisse.append(self.gewonnen)
        self.klick_liste.clear()
        self.counter = 3

        self.master.after(1000, lambda: self.label_counter.config(text=f"Neue Runde in 5"))
        self.master.after(2000, lambda: self.label_counter.config(text=f"Neue Runde in 4"))
        self.master.after(3000, lambda: self.label_counter.config(text=f"Neue Runde in 3"))
        self.master.after(4000, lambda: self.label_counter.config(text=f"Neue Runde in 2"))
        self.master.after(5000, lambda: self.label_counter.config(text=f"Neue Runde in 1"))
        self.master.after(6000, self.random_capital)
        self.master.after(6000, self.counter_update)
        self.master.after(6000, self.unlock)
        self.master.after(6000, self.plot_world)

    def auswertung(self):
        """Öffnet ein Fenster mit einer Spielauswertung

        Hier werden die Städte der Runde gesammelt, inklusive Erfolg oder Misserfolg.
        Die Städte werden noch mal auf der Karte geplottet
        """
        auswertungsfenster = tk.Toplevel()
        auswertungsfenster.title("Spielauswertung")
        auswertungsfenster.geometry(f"{self.main_window.setze_fenster(400, 300)}")
        auswertungsfenster.attributes('-topmost', True)
        lbl_staedte = tk.Label(auswertungsfenster)
        lbl_staedte.pack()
        self.plot_world()

        auswertungstext= "\n\nRUNDE BEENDET - SPIELAUSWERTUNG\n\n"
        auswertungstext += f"Runde #{' ':>2} {'Hauptstadt':<24} {'Land':<27} {'Ergebnis':<8}\n"
        auswertungstext += f"{'-' * 8}-{'-' * 24}-{'-' * 27}-{'-' * 8}\n"
        for i in range (len(self.abgehakt)):
            auswertungstext += f"Runde {i+1:>2}  {self.main_window.filtered_capitals[self.abgehakt[i]]["Hauptstadt"]:<24} {self.main_window.filtered_capitals[self.abgehakt[i]]["Land"]:<27} "
            if self.ergebnisse[i] == True:
                auswertungstext += f"Richtig\n"
            elif self.ergebnisse[i] == False:
                auswertungstext += f"Falsch\n"
            else:
                print("FEHLER in AUSWERTUNG")
            if self.runde >= 10:
                x_plot = self.main_window.filtered_capitals[self.abgehakt[i]]["Längengrad"]
                y_plot = self.main_window.filtered_capitals[self.abgehakt[i]]["Breitengrad"]
                self.ax.plot(x_plot, y_plot, 'o')
                self.fig.canvas.draw()


        lbl_staedte.config(text = auswertungstext, justify='left')

        def start_und_quit():
            auswertungsfenster.destroy()
            self.main_window.reset_game()
            self.start_spiel()

        if self.runde > 9:
            button_new = tk.Button(auswertungsfenster, text="Neues Spiel", command=start_und_quit)
            button_new.pack()

    def abstand_berechnen(self,p1,p2):
        """
        Der Abstand wird mithilfe der Haversine-Formel berechnet, ie den Abstand zwischen zwei Punkten auf einer Kugel angibt.
        Dazu werden die Koordinaten in Bogenmaß umgerechnet, die Haversine-Formel angewendet und der Erdradius multipliziert
        Ich habe zuerst geopy.distance benutzt, das muss aber installiert werden - für das Spiel ist diese Annäherung gut genug.
        """
        lat1, lon1 = map(radians, p1)
        lat2, lon2 = map(radians, p2)

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        r = 6371.0 #Erdradius in km
        abstand = r * c
        return abstand

    def check(self):
        """Überprüft den Abstand zwischen Klick und Stadt und ob die Runde gewonnen wurde"""
        cityPoint = (self.y, self.x)
        #hier mit geopy:
        #abst = geodesic(cityPoint, self.klickPoint)
        #print(abst, type(abst))
        #hier ohne geopy:
        abst = self.abstand_berechnen(cityPoint, self.klickPoint)
        print(f"Abstand: {abst:.2f}, max: {self.main_window.schwierigkeitsgrad}")

        self.counter -= 1
        self.counter_update()

        if abst <= self.main_window.schwierigkeitsgrad: #Gewonnen
            self.gewonnen = True
            self.main_window.spielstand_aktualisieren()
            self.counter_update()
            print("Treffer")
            self.plot_city_point()
            self.plot_line()
            haken_x = [-34, 12, 55]
            haken_y = [4, -46, 37]
            self.ax.plot(haken_x, haken_y, linestyle="-", color="g", linewidth='10', alpha=0.5)
            self.fig.canvas.draw()
            if self.runde >= 10:
                self.auswertung()
            else:
                self.next_round()

        elif self.counter < 1: #Verloren
            print("Daneben")
            self.verloren = True
            self.plot_city_point()
            self.plot_line()
            kreuz_x = [-38, 38]
            kreuz_y = [31, -31]
            kreuz2_x = [38, -38]
            kreuz2_y = [31, -31]
            self.ax.plot(kreuz_x, kreuz_y, linestyle="-", color="r", linewidth='10', alpha=0.5)
            self.ax.plot(kreuz2_x, kreuz2_y, linestyle="-", color="r", linewidth='10', alpha=0.5)
            self.fig.canvas.draw()
            self.next_round()

        elif abst > self.main_window.schwierigkeitsgrad: #Falsch geraten
            print("Daneben")
            self.plot_click_point()
            self.master.after(500, self.fig.canvas.draw)

        else:
            print("Fehler im CHECK")

    def zoom(self, event):
        """Zoom-Funktion auf die Weltkarte.
            Per Mausrad-Scrolling wird an den Punkt herangezoomt, auf dem sich die Maus gerade befindet.
            Dazu wird der Punkt registriert, die Achsen mit einem Scale_factor multipliziert und um die Stelle der
            Mausposition verschoben und neu gesetzt.
            Diese Funktion habe ich mir von ChatGPT generieren lassen und leicht angepasst."""
        # Aktuelle Achsenlimits abrufen
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        try:
            scale_factor = 1.5
            if event.button == 'up':
                scale_factor = 1 / scale_factor
            elif event.button == 'down':
                scale_factor = scale_factor
            #Mausposition registrieren
            x_center = event.xdata
            y_center = event.ydata

            new_xlim = [x_center - (x_center - xlim[0]) * scale_factor, x_center + (xlim[1] - x_center) * scale_factor]
            new_ylim = [y_center - (y_center - ylim[0]) * scale_factor, y_center + (ylim[1] - y_center) * scale_factor]
            #Maximalzoom festlegen
            if abs(new_xlim[0]) > 180 or abs(new_xlim[1]) > 180 or abs(new_ylim[0]) > 90 or abs(new_ylim[1]) > 90:
                new_xlim = [-180, 180]
                new_ylim = [-90, 90]

            # Achsenlimits aktualisieren
            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
            self.fig.canvas.draw()
        except:
            """Manchmal kommt es hier zu Fehlern, dann wird die Karte einfach zurückgesetzt"""
            print("Zoom zurückgesetzt")
            new_xlim = [-180, 180]
            new_ylim = [-90, 90]
            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
            self.fig.canvas.draw()

    def onclick(self, event):
        """Hier wird der Mausklick auf die Weltkarte ausgewertet"""
        if event.button == 1:
            if self.gewonnen == False and self.verloren == False:
                if event.xdata!=None and event.ydata!=None:
                    try:
                        self.x_click = float(event.xdata)
                        self.y_click = float(event.ydata)
                        self.klickPoint = (self.y_click, self.x_click)
                        self.klick_liste.append(self.klickPoint)
                        self.check()
                    except:
                        pass
                else:
                    print("Click out of border.")
################################################################################
#Main Window Class
################################################################################
class Hauptfenster:
    """Diese Klasse instanziiert alle Unterklassen und befüllt das Hauptfenster"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.geometry(f"{self.setze_fenster(1280, 720)}")
        self.root.title("Finde die Stadt")

        self.spielername = ""
        self.spieler = spieler
        self.schwierigkeitsgrad = 500
        #Frames
        self.f1 = tk.Frame(self.root)
        self.f1.grid(row=0, column=0, sticky="ew")
        self.f2 = tk.Frame(self.root)
        self.f2.grid(row=1, column=0, sticky="nsew")
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.f1.grid_rowconfigure(0, weight=1)
        self.f1.grid_columnconfigure(0, weight=1)
        self.f1.grid_columnconfigure(1, weight=1)
        self.f1.grid_columnconfigure(2, minsize=20)
        self.f2.grid_rowconfigure(0, weight=2)
        self.f2.grid_columnconfigure(0, weight=2)

        #Widgets
        self.lbl_name = tk.Label(self.f1)
        self.lbl_name.grid(sticky="w", row=0, column=0, padx=10)
        self.lbl_punkte = tk.Label(self.f1, text="Aktueller Punktestand:")
        self.lbl_punkte.grid(sticky="w", row=0, column=1, padx=10)
        self.label_runde = tk.Label(self.f1, text="Runde: 1 / 10")
        self.label_runde.grid(sticky="w", row=0, column=2, padx=10)
        self.label_stadt = tk.Label(self.f1, text="Stadt")
        self.label_stadt.grid(sticky="e", row=0, column=3, padx=10)
        self.label_kontinente = tk.Label(self.f1, text="Kontinent")
        self.label_kontinente.grid(sticky="e", row=0, column=4, padx=10)
        self.label_counter = tk.Label(self.f1, text="Noch 3 Versuche")
        self.label_counter.grid(sticky="e", row=0, column=5, padx=10)

        #instanziiere die anderen Klassen
        self.spieleinstellungen = Spieleinstellungen(self)
        self.plotter = Hauptstadtplotter(self.root, self)
        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.f2)

        self.filtered_capitals = []
        print(self.filtered_capitals)
        #mehr widgets
        self.button_print_all = tk.Button(master=self.f1, text="Alle Hauptstädte anzeigen",
                                          command=self.plotter.plot_capitals)
        self.button_print_all.grid(row=0, column=6, padx=10)
        self.button_auswertung = tk.Button(master=self.f1, text="Auswertung", command=self.plotter.auswertung)
        self.button_auswertung.grid(row=0, column=7, padx=10)
        self.button_reset = tk.Button(master=self.f1, text="Reset Game", command=self.reset_game)
        self.button_reset.grid(row=0, column=9, padx=10)
        self.button_spieleinstellungen = tk.Button(master=self.f1, text="Spieleinstellungen", command=self.oeffne_spieleinstellungen)
        self.button_spieleinstellungen.grid(row=0, column=10, padx=10)
        self.button_quit = tk.Button(master=self.f1, text="Quit", command=self.quit_and_safe)
        self.button_quit.grid(row=0, column=11, padx=10)
        self.spieleinstellungen.ent.focus_set()

        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")


    def setze_fenster(self, breite, hoehe):
        """Fenster werden in der Bildschirmmitte geöffnet."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = (screen_width // 2) - (breite // 2)
        center_y = (screen_height // 2) - (hoehe // 2)

        return f"{breite}x{hoehe}+{center_x}+{center_y}"

    def oeffne_spieleinstellungen(self):
        self.spieleinstellungen.spieleinstellungen.deiconify()
        self.root.withdraw()

    def reset_game(self):
        self.plotter.counter = 3
        self.plotter.gewonnen = False
        self.plotter.abgehakt.clear()
        self.plotter.ergebnisse.clear()
        self.plotter.ax.clear()

        if self.spieleinstellungen.punkte_vorher != -1:
            self.spieler["Spielername"] = self.spieleinstellungen.punkte_vorher
        self.plotter.start_spiel()

    def spielstand_aktualisieren(self):
        """Aktualisieren und anzeigen den Punktestand des Spielers"""
        if self.plotter.gewonnen==True:
            self.spieler[self.spielername] += 1
        self.lbl_punkte.config(text=f"Aktueller Punktestand: {self.spieler[self.spielername]}")

    def run(self):
        self.root.mainloop()

    def quit_and_safe(self):
        with open('./spieler_score.json', 'w') as spieler_score:
            json.dump(self.spieler, spieler_score)
        self.root.quit()

################################################################################
################################################################################
# Spieleinstellungen-Klasse
################################################################################
################################################################################
class Spieleinstellungen:
    """Diese Klasse ist für die Spielerverwaltung verantwortlich.

    Man kann einen Spielernamen eintippen, der wird mit den vorhandenen abgeglichen,
    oder einen aus der Liste auswählen. Außerdem kann man hier Spieler zurücksetzen oder löschen.
    Weiterhin wird hier der Schwierigkeitsgrad und die Kontinentauswahl gesetzt.
    Hier ist noch ein Bug: Es muss zuerst der Spieler und dann der Kontinent ausgewählt werden,
    sonst wird die Kontinentauswahl zurückgesetzt. Alternativ: Spielername eintippen.
    """

    def __init__(self, main_window):
        self.main_window = main_window
        self.spieleinstellungen = tk.Toplevel()
        self.spieleinstellungen.title("Spielermenü")
        self.spieleinstellungen.geometry(f"{self.main_window.setze_fenster(800, 400)}")
        self.spieleinstellungen.attributes('-topmost', True)
        self.name = tk.StringVar()
        self.name.trace_add("write", self.entry_watch)
        self.punkte_vorher = -1
        self.ausgewaehlte_kontinente = []

        #Frames - einer oben, drei in der Mitte, einer unten
        self.f0 = tk.Frame(self.spieleinstellungen, width=400, height=100, borderwidth=2, relief="groove")
        self.f0.grid(row=0, column=0, sticky="ew")
        self.f1 = tk.Frame(self.spieleinstellungen, width=400, height=100, borderwidth=2, relief="groove")
        self.f1.grid(row=0, column=1, sticky="ew")
        self.f2 = tk.Frame(self.spieleinstellungen, width=100, height=300, borderwidth=2, relief="groove")
        self.f2.grid(row=1, column=0, sticky="nsew", padx=(5,0))
        self.f3 = tk.Frame(self.spieleinstellungen, width=200, height=300, borderwidth=3, relief="groove")
        self.f3.grid(row=1, column=1, sticky="nsew")
        self.f4 = tk.Frame(self.spieleinstellungen, width=200, height=300, borderwidth=2, relief="groove")
        self.f4.grid(row=1, column=2, sticky="nsew", padx=(0,5))
        self.f5 = tk.Frame(self.spieleinstellungen, width=400, height=50, borderwidth=2, relief="groove")
        self.f5.grid(row=2, column=1, sticky="ew")

        self.spieleinstellungen.grid_columnconfigure(0, weight=1)  # f2
        self.spieleinstellungen.grid_columnconfigure(1, weight=1)  # f3
        self.spieleinstellungen.grid_columnconfigure(2, weight=1)  # f4

        self.f1.grid_columnconfigure(0, weight=1)
        self.f1.grid_columnconfigure(1, weight=1)
        self.f2.grid_columnconfigure(0, weight=1)
        self.f3.grid_columnconfigure(0, weight=1)
        self.f3.grid_columnconfigure(1, weight=1)
        self.f5.grid_columnconfigure(0, weight=1)
        self.f5.grid_columnconfigure(1, weight=1)

        # Widgets
        self.anmerkung = tk.Label(self.f0, text="Bitter erst Spieler auswählen, dann Kontinent", justify='center')
        self.anmerkung.grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.nf_label = tk.Label(self.f1, text="Namen eingeben oder Spieler auswählen:", justify='center')
        self.nf_label.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.spieler_label = tk.Label(self.f1, text="Spieler:", justify='center')
        self.spieler_label.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.button_enter = tk.Button(self.f5, text="Enter", command=self.quit_and_copy)
        self.button_enter.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        self.button_reset = tk.Button(self.f3, text="Reset Points", command=self.reset_points)
        self.button_reset.grid(sticky='ew', row=2, column=0, columnspan=2)
        self.button_delete = tk.Button(self.f3, text="Delete User", command=self.delete_user)
        self.button_delete.grid(sticky='ew', row=3, column=0, columnspan=2)
        self.schwieriegkeit_label = tk.Label(self.f3, text="Schwierigkeitsgrad: Abstand Mausklick <-> Stadt ", justify='center')
        self.schwieriegkeit_label.grid(row=4, column=0, columnspan=2, sticky='ew')
        self.difficulty_var = tk.IntVar(value=500)

        self.radio_500 = tk.Radiobutton(self.f3, text="250 km", variable=self.difficulty_var, value=250,
                                   command=lambda: self.set_schwierigkeitsgrad(250))
        self.radio_500.grid(row=5, column=0, columnspan=2, sticky='ew')
        self.radio_1000 = tk.Radiobutton(self.f3, text="500 km", variable=self.difficulty_var, value=500,
                                    command=lambda: self.set_schwierigkeitsgrad(500))
        self.radio_1000.grid(row=6, column=0, columnspan=2, sticky='ew')
        self.radio_1500 = tk.Radiobutton(self.f3, text="1000 km", variable=self.difficulty_var, value=1000,
                                    command=lambda: self.set_schwierigkeitsgrad(1000))
        self.radio_1500.grid(row=7, column=0, columnspan=2, sticky='ew')
        self.set_schwierigkeitsgrad(self.difficulty_var.get())

        self.ent = tk.Entry(self.f3, textvariable=self.name)
        self.ent.grid(sticky='new', row=0, column=0, columnspan=2)
        self.ent.bind('<Return>', self.on_enter)

        self.spielerauswahl_label = tk.Label(self.f2, text="Vorhandene Spieler:", justify='center')
        self.spielerauswahl_label.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.listbox = tk.Listbox(self.f2, exportselection=False, selectmode=tk.SINGLE, width=30, height=10)
        self.listbox.grid(sticky='nsw', row=1, column=0, padx=10, pady=10)
        self.listbox.bind('<<ListboxSelect>>', self.spieler_auswahl)
        self.spieler_anzeigen()

        self.label_kontinente = tk.Label(self.f4, text="Kontinente auswählen", justify='left')
        self.label_kontinente.grid(sticky='new', row=0, column=0)
        self.listbox_kontinente = tk.Listbox(self.f4, exportselection=False, selectmode=tk.MULTIPLE, height=7, width=20)
        for kontinent in sorted(kontinent_liste):
            self.listbox_kontinente.insert(tk.END, kontinent)
        self.listbox_kontinente.grid(sticky='ew', row=1, column=0, padx=10, pady=10)
        self.listbox_kontinente.bind('<<ListboxSelect>>', self.kontinente_auswahl)
        self.listbox_kontinente.select_set(3)
        self.kontinente_auswahl(None)

    def set_schwierigkeitsgrad(self, value):
        self.main_window.schwierigkeitsgrad = value
        print(f"Schwierigkeitsgrad gesetzt auf: {self.main_window.schwierigkeitsgrad} km")

    def on_enter(self, event):
        self.quit_and_copy()

    def entry_watch(self, *args):
        if self.name == "":
            self.ent.config(bg="red")
        else:
            self.ent.config(bg="white")
            self.main_window.lbl_name.config(text=f"Spieler: {self.name.get()}")
            self.spieler_label.config(text=f"Spieler: {self.name.get()}")

    def quit_and_copy(self):
        """Überprüft und übernimmt Spieleinstellungen und beendet das Fenster"""
        if self.ent.get():
            if self.name.get() in self.main_window.spieler:
                print("Schon vorhanden")
                self.punkte_vorher = self.main_window.spieler[self.name.get()]
                self.main_window.lbl_punkte.config(text=f"Punkte: {self.main_window.spieler[self.name.get()]}")
            else:
                self.main_window.spieler[self.name.get()] = 0
                self.main_window.lbl_punkte.config(text=f"Punkte: {self.main_window.spieler[self.name.get()]}")
                print(f"neu eingetragen: {self.name.get()}")
            self.main_window.spielername= self.name.get()
            if self.listbox_kontinente.curselection():
                self.main_window.filtered_capitals = [capital for capital in capitals if capital["Kontinent"] in self.ausgewaehlte_kontinente]
                print(self.main_window.filtered_capitals)
                self.spieleinstellungen.withdraw()
                self.main_window.plotter.start_spiel()
                self.main_window.root.deiconify()
            else:
                self.button_enter.config(text = "Kontinente auswählen")
                self.spieleinstellungen.after(1500, lambda: self.button_enter.config(text="Enter", bg='SystemButtonFace'))
        else:
            self.button_enter.config(text="Spieler auswählen")
            self.spieleinstellungen.after(1500, lambda: self.button_enter.config(text="Enter", bg='SystemButtonFace'))

    def kontinente_auswahl(self,event):
        """Index der Kontinente"""
        index_k = self.listbox_kontinente.curselection()
        print(index_k)
        if index_k:
            for i in index_k:
                listen_eintrag_k = self.listbox_kontinente.get(i)  # Hier ebenfalls die richtige Listbox verwenden
                if listen_eintrag_k not in self.ausgewaehlte_kontinente:
                    self.ausgewaehlte_kontinente.append(listen_eintrag_k)

    def spieler_auswahl(self,event):
        """Index des ausgewählten Spielers"""
        index_s = self.listbox.curselection()
        if index_s:
            listen_eintrag_s = self.listbox.get(index_s)
            self.main_window.spielername = listen_eintrag_s.split(":")[0].strip()
            self.ent.delete(0, tk.END)
            self.ent.insert(0, self.main_window.spielername)
            #messagebox.showinfo("Ausgewählter Spieler", f"Du hast {spieler_name} ausgewählt!")

    def spieler_anzeigen(self):
        """aktualisiert die Spieler-Listbox"""
        for name, values in self.main_window.spieler.items():
            anzeige = f"{name}: {values} Punkte"
            self.listbox.insert(tk.END, anzeige)

    def reset_points(self):
        """Punktestand zurücksetzen"""
        index = self.listbox.curselection()
        if index:
            spielerauswahl = self.listbox.get(index)
            spielerauswahl = spielerauswahl.split(":")[0].strip()
            if self.main_window.spieler[spielerauswahl] == 0:
                self.main_window.spieler[spielerauswahl] = 127
                print(self.main_window.spieler)
            if spielerauswahl in self.main_window.spieler:
                self.main_window.spieler[spielerauswahl] = 0
                self.listbox.delete(0, tk.END)
                self.spieler_anzeigen()
        else:
            self.button_reset.config (text = "Spieler auswählen", bg = 'red')
            self.spieleinstellungen.after(1000, lambda: self.button_reset.config(text = "Punkte zurücksetzen", bg = 'SystemButtonFace'))


    def delete_user(self):
        """Spieler löschen"""
        index = self.listbox.curselection()
        if index:
            loescheintrag = self.listbox.get(index)
            loescheintrag = loescheintrag.split(":")[0].strip()
            if loescheintrag in self.main_window.spieler:
                del self.main_window.spieler[loescheintrag]
                print("nachher", self.main_window.spieler)
                self.listbox.delete(0, tk.END)
                self.spieler_anzeigen()
        else:
            self.button_delete.config (text = "Spieler auswählen", bg = 'red')
            self.spieleinstellungen.after(1000, lambda: self.button_delete.config(text = "User löschen", bg = 'SystemButtonFace'))


def main():


    hauptfenster = Hauptfenster()
    hauptfenster.run()

if __name__ == "__main__":
    main()
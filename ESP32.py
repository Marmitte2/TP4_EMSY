
# ============================================================
#  TP4 – ESP-NOW  |  
# ============================================================

from machine import Pin, Timer
import neopixel
import network
import espnow
import time

# ── Constantes ──────────────────────────────────────────────
PASSWORD        = b"ESP_TP4_SECRET"   # même valeur sur les deux cartes
MSG_PAIR        = b"PAIR:"            # préfixe de demande de pairing
MSG_NEXT        = b"NEXT"             # commande : passe à la couleur suivante
MSG_HEARTBEAT   = b"HB"               # ping de maintien de connexion
DEBOUNCE_MAX    = 500                 # itérations avant validation appui
BLINK_PERIOD    = 500                 # ms  → 2 Hz  (on 250 ms / off 250 ms)
HB_SEND_INTERVAL   = 1000             # envoie un heartbeat toutes les 1 s
HB_TIMEOUT         = 4000             # déconnexion si rien reçu depuis 4 s

# ── GPIO ────────────────────────────────────────────────────
s1   = Pin(4,  Pin.IN,  Pin.PULL_UP)
s2   = Pin(5,  Pin.IN,  Pin.PULL_UP)
led1 = Pin(6,  Pin.OUT)
led1.value(0)
led2 = Pin(7,  Pin.OUT)
led2.value(1)

np   = neopixel.NeoPixel(Pin(48, Pin.OUT), 1)

# ── Couleurs RGB ─────────────────────────────────────────────
COULEURS = [
    (20, 0,  0 ),   # Rouge
    (0,  20, 0 ),   # Vert
    (0,  0,  20),   # Bleu
]
index_couleur = 0
np[0] = COULEURS[index_couleur]
np.write()

# ── Wi-Fi en mode STA  ───────────────────────────────────────
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()
MY_MAC = wlan.config("mac")
print("MAC:", ":".join("{:02x}".format(b) for b in MY_MAC))

# ── ESP-NOW ──────────────────────────────────────────────────
e = espnow.ESPNow()
e.active(True)
BROADCAST = b"\xff\xff\xff\xff\xff\xff"
e.add_peer(BROADCAST)

# ── État connexion ───────────────────────────────────────────
paired_mac      = None   # MAC de l'autre ESP une fois appairé
connected       = False
blink_state     = False  # état ON/OFF du clignotement

# ── Anti-rebond ──────────────────────────────────────────────
debounce_1 = 0
debounce_2 = 0

# ── Timers ──────────────────────────────────────────────────
last_blink_ms   = 0
last_pair_ms    = 0
last_hb_send_ms = 0
last_hb_recv_ms = time.ticks_ms()
PAIR_INTERVAL   = 2000   # re-broadcast toutes les 2 s si pas appairé

# ════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════

def set_rgb(couleur):
    """Allume la LED RGB locale avec la couleur donnée."""
    np[0] = couleur
    np.write()

def next_color():
    """Passe à la couleur suivante dans le tableau."""
    global index_couleur
    index_couleur = (index_couleur + 1) % len(COULEURS)
    set_rgb(COULEURS[index_couleur])

def send_to_peer(data: bytes):
    """Envoie un message au pair appairé (si disponible)."""
    if paired_mac:
        try:
            e.send(paired_mac, data)
        except Exception as ex:
            print("Erreur envoi:", ex)

def broadcast_pair():
    """Diffuse notre mot de passe pour trouver l'autre ESP."""
    try:
        e.send(BROADCAST, MSG_PAIR + PASSWORD)
    except Exception as ex:
        print("Erreur broadcast:", ex)

def handle_pairing(mac, msg):
    """Traite un message de pairing reçu."""
    global paired_mac, connected, last_hb_recv_ms
    pw = msg[len(MSG_PAIR):]
    if pw == PASSWORD and mac != MY_MAC:
        last_hb_recv_ms = time.ticks_ms()   # réinitialise le timeout dès le pairing
        if not connected:
            print("Pair trouvé :", ":".join("{:02x}".format(b) for b in mac))
            paired_mac = bytes(mac)
            try:
                e.add_peer(paired_mac)
            except Exception:
                pass  # déjà ajouté
            connected = True
            # Répondre pour que l'autre sache aussi qu'on est là
            e.send(paired_mac, MSG_PAIR + PASSWORD)

def handle_heartbeat():
    """Met à jour le timestamp du dernier message reçu."""
    global last_hb_recv_ms
    last_hb_recv_ms = time.ticks_ms()

def disconnect():
    """Réinitialise la connexion et revient en mode local."""
    global paired_mac, connected, blink_state
    print("Connexion perdue – retour mode local")
    connected   = False
    paired_mac  = None
    blink_state = False
    set_rgb(COULEURS[index_couleur])   # arrêt clignotement, couleur stable

def handle_next():
    """Passe à la couleur suivante sur commande de l'autre ESP."""
    next_color()

# ════════════════════════════════════════════════════════════
#  Boucle principale
# ════════════════════════════════════════════════════════════
while True:
    now = time.ticks_ms()

    # ── 1. Réception ESP-NOW  ───────────────────────────────
    host, msg = e.irecv(0)      # timeout = 0 → immédiat
    if msg:
        if connected and bytes(host) == paired_mac:
            last_hb_recv_ms = now   # tout message du pair réinitialise le timeout
        if msg.startswith(MSG_PAIR):
            handle_pairing(host, msg)
        elif msg == MSG_NEXT:
            handle_next()
        elif msg == MSG_HEARTBEAT:
            handle_heartbeat()

    # ── 2. Broadcast périodique si pas encore appairé ────────
    if not connected and time.ticks_diff(now, last_pair_ms) >= PAIR_INTERVAL:
        broadcast_pair()
        last_pair_ms = now

    # ── 3. Heartbeat + détection de déconnexion ──────────────
    if connected:
        # Envoie un ping périodique
        if time.ticks_diff(now, last_hb_send_ms) >= HB_SEND_INTERVAL:
            send_to_peer(MSG_HEARTBEAT)
            last_hb_send_ms = now
        # Vérifie si l'autre ESP répond encore
        if time.ticks_diff(now, last_hb_recv_ms) >= HB_TIMEOUT:
            disconnect()

    # ── 4. Clignotement 2 Hz si mode remote actif ────────────
    if connected and time.ticks_diff(now, last_blink_ms) >= BLINK_PERIOD // 2:
        last_blink_ms = now
        blink_state = not blink_state
        if blink_state:
            set_rgb(COULEURS[index_couleur])
        else:
            set_rgb((0, 0, 0))   # éteint

    # ── 5. Bouton S1 – toggle LED D1 (toujours local) ────────
    if s1.value() == 0:
        debounce_1 += 1
        if debounce_1 == DEBOUNCE_MAX:
            led1.value(not led1.value())
    else:
        debounce_1 = 0

    # ── 6. Bouton S2 ─────────────────────────────────────────
    if s2.value() == 0:
        debounce_2 += 1
        if debounce_2 == DEBOUNCE_MAX:
            if connected:
                # Mode remote : demande à l'autre ESP de passer à la couleur suivante
                send_to_peer(MSG_NEXT)
            else:
                # Mode local : change notre propre LED RGB
                next_color()
    else:
        debounce_2 = 0



from flask import Flask, render_template, request
import subprocess

app = Flask(__name__)


# -------- STABILITY CHECK --------
def check_stabilite():
    try:
        result = subprocess.run(
            ['ping', '-n', '4', '8.8.8.8'],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        output = result.stdout

        if "Lost = 0" in output or "perdus = 0" in output:
            return "Bonne"
        elif "Lost = 1" in output or "Lost = 2" in output or \
             "perdus = 1" in output or "perdus = 2" in output:
            return "Moyenne"
        else:
            return "Faible"
    except Exception:
        return "Inconnue"


# -------- WIFI SCAN --------
def get_networks():
    try:
        resultat = subprocess.run(
            ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
    except FileNotFoundError:
        return []  # not on Windows

    lignes = resultat.stdout.split('\n')
    reseaux = []
    reseau_actuel = {}

    stabilite = check_stabilite()

    for ligne in lignes:
        ligne = ligne.strip()

        if ligne.startswith('SSID') and 'BSSID' not in ligne:
            if reseau_actuel:
                reseaux.append(reseau_actuel)
            nom = ligne.split(':', 1)[1].strip()
            reseau_actuel = {'nom': nom, 'auth': '', 'signal': 0, 'stabilite': stabilite}

        elif 'Authentication' in ligne or 'Authentification' in ligne:
            reseau_actuel['auth'] = ligne.split(':', 1)[1].strip()

        elif 'Signal' in ligne:
            signal_str = ligne.split(':', 1)[1].strip().replace('%', '')
            if signal_str.isdigit():
                reseau_actuel['signal'] = int(signal_str)

    if reseau_actuel and reseau_actuel.get('nom'):
        reseaux.append(reseau_actuel)

    # -------- SCORING --------
    for r in reseaux:
        score = 0
        auth = r['auth']
        signal = r['signal']

        # Encryption score
        if 'WPA3' in auth:
            score += 40
            r['niveau_auth'] = 'WPA3'
            r['auth_color'] = 'green'
            r['ouvert'] = False
        elif 'WPA2' in auth:
            score += 30
            r['niveau_auth'] = 'WPA2'
            r['auth_color'] = 'blue'
            r['ouvert'] = False
        elif 'WPA' in auth:
            score += 10
            r['niveau_auth'] = 'WPA'
            r['auth_color'] = 'orange'
            r['ouvert'] = False
        elif 'WEP' in auth:
            score -= 20
            r['niveau_auth'] = 'WEP'
            r['auth_color'] = 'red'
            r['ouvert'] = False
        else:
            score -= 50
            r['niveau_auth'] = 'OUVERT'
            r['auth_color'] = 'red'
            r['ouvert'] = True

        # Signal score
        if signal >= 70:
            score += 30
            r['signal_niveau'] = 'Fort'
        elif signal >= 40:
            score += 15
            r['signal_niveau'] = 'Moyen'
        else:
            score += 5
            r['signal_niveau'] = 'Faible'

        # Stability score
        if r['stabilite'] == 'Bonne':
            score += 30
        elif r['stabilite'] == 'Moyenne':
            score += 15

        # Clamp score between 0 and 100
        score = max(0, min(100, score))
        r['score'] = score

        # Result label
        if score >= 70:
            r['resultat'] = 'Sécurisé'
        elif score >= 40:
            r['resultat'] = 'Moyen'
        else:
            r['resultat'] = 'Dangereux'

    return reseaux


# -------- ROUTES --------
@app.route('/', methods=['GET', 'POST'])
def index():
    reseaux = []
    scanned = False

    if request.method == 'POST':
        reseaux = get_networks()
        scanned = True

    # Sort for top 3
    top3 = sorted(reseaux, key=lambda x: x['score'], reverse=True)[:3]

    return render_template('index.html', reseaux=reseaux, top3=top3, scanned=scanned)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

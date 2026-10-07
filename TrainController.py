from pybricks import version
from pybricks.hubs import TechnicHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Button, Color
from pybricks.tools import wait, StopWatch

print("Pybricks Firmware Version:", version)

hub = TechnicHub()
watch = StopWatch()
drive_timer = StopWatch()

# Setup Motor on Port A
try:
    print("setup motor 1")
    m1 = Motor(Port.A)
    m1.reset_angle(0)
except Exception as e:
    print("setupMotor 1 failed:", e)
    m1 = None

print("m1: ", m1)

# Connect to Duplo Train
# Check if native pupdevices.DuploTrain is available (Pybricks v4+)
try:
    from pybricks.pupdevices import DuploTrain
    print("Natives pybricks.pupdevices.DuploTrain verfuegbar!")
    is_native = True
    train1 = DuploTrain()
except Exception as e:
    from duploTrain import DuploTrain
    print("Verwende custom duploTrain (LWP3)")
    is_native = False
    train1 = DuploTrain()
    train1.connect()

print("train1: ", train1)

# Configuration
MAX_DIAL_ANGLE = 70      # Maximum dial angle in degrees (clamped to prevent runaway rotation)
DEADZONE = 12            # Neutral zone around 0 degrees where the train stops
MIN_DRIVE_POWER = 35     # Minimum power to ensure smooth train start
REVERSAL_THRESHOLD = 15  # Turning wheel opposite by 15 deg triggers immediate auto-stop & zero reset

m1LastAngle = None
commanded_power = 0
peak_angle = 0

def is_train_connected(train):
    """Check if train is connected."""
    if hasattr(train, "isConnected"):
        return train.isConnected()
    return train is not None

def train_drive(train, power):
    """Send driving power to the train."""
    try:
        if power == 0:
            if hasattr(train, "stop_driving"):
                return train.stop_driving()
            elif hasattr(train, "drive"):
                return train.drive(0)
        if hasattr(train, "drive"):
            return train.drive(power)
        elif hasattr(train, "start_driving"):
            return train.start_driving(power)
    except Exception as e:
        print("train_drive Fehler:", e)

def reset_to_neutral(motor, train, reason=""):
    """Resets controller state and train to stopped / 0 degrees."""
    global m1LastAngle, commanded_power, peak_angle
    if reason:
        print(reason)
    train_drive(train, 0)
    if hasattr(train, "clear_action_brick"):
        train.clear_action_brick()
    if motor is not None:
        try:
            motor.reset_angle(0)
        except Exception as e:
            print("Motor reset_angle Fehler:", e)
    m1LastAngle = 0
    commanded_power = 0
    peak_angle = 0

headlights_active = False

def train_play_sound(train, sound):
    """Spielt einen Zug-Sound ab (unterstützt custom duploTrain und natives DuploTrain)."""
    try:
        if hasattr(train, "play_sound"):
            train.play_sound(sound)
        elif hasattr(train, "sound"):
            train.sound(sound)
    except Exception as e:
        print("train_play_sound Fehler:", e)

def train_set_light(train, color):
    """Schaltet den Zugscheinwerfer (unterstützt custom duploTrain und natives DuploTrain)."""
    try:
        if hasattr(train, "set_light"):
            train.set_light(color)
        elif hasattr(train, "headlights"):
            train.headlights(color)
    except Exception as e:
        print("train_set_light Fehler:", e)

def get_brick_type(color):
    """Ordnet Farb-IDs oder Pybricks Color-Objekte den Action-Bricks zu."""
    if color == 3 or color == 4 or color == Color.BLUE:
        return "BLUE"
    if color == 5 or color == 6 or color == Color.GREEN:
        return "GREEN"
    if color == 7 or color == 8 or color == Color.YELLOW or color == Color.ORANGE:
        return "YELLOW"
    if color == 9 or color == Color.RED:
        return "RED"
    if color == 10 or color == Color.WHITE:
        return "WHITE"
    return None

def handle_action_brick(brick_color, motor, train):
    """Führt die definierte Aktion für den erkannten Action-Brick aus."""
    global commanded_power, drive_timer, m1LastAngle, peak_angle, headlights_active

    brick_type = get_brick_type(brick_color)
    if brick_type is None:
        print("Action-Brick ohne definierte Aktion (Farb-ID):", brick_color)
        return

    # 1. Gelb: Hupen
    if brick_type == "YELLOW":
        print("Aktion: Gelber Brick -> Hupe ertönt")
        train_play_sound(train, "horn")

    # 2. Weiss: Licht umschalten (wenn aus -> an, wenn an -> aus)
    elif brick_type == "WHITE":
        headlights_active = not headlights_active
        if headlights_active:
            print("Aktion: Weisser Brick -> Scheinwerfer AN")
            train_set_light(train, Color.WHITE)
        else:
            print("Aktion: Weisser Brick -> Scheinwerfer AUS")
            train_set_light(train, Color.NONE)

    # 3. Rot: Stopp
    elif brick_type == "RED":
        print("Aktion: Roter Brick -> Stopp & Nullstellung")
        train_play_sound(train, "brake")
        reset_to_neutral(motor, train, "Roter Action-Brick")

    # 4. Blau: Stopp -> Tank-Geräusch für ca. 5s -> Weiterfahrt in gleiche Richtung
    elif brick_type == "BLUE":
        print("Aktion: Blauer Brick -> Tank-Stopp (ca. 5 Sekunden)...")
        previous_power = commanded_power

        # Zug anhalten
        train_drive(train, 0)
        train_play_sound(train, "water")

        # 5 Sekunden warten (Mitten-Taste kann vorzeitig abbrechen)
        tank_watch = StopWatch()
        sound_repeated = False
        while tank_watch.time() < 5000:
            if Button.CENTER in hub.buttons.pressed():
                reset_to_neutral(motor, train, "Mitten-Taste waehrend Tanken gedrueckt: Stopp")
                return
            if not sound_repeated and tank_watch.time() >= 2500:
                train_play_sound(train, "water")
                sound_repeated = True
            wait(50)

        # Weiterfahrt in die gleiche Richtung
        if previous_power != 0:
            print("Tanken abgeschlossen -> Weiterfahrt mit Leistung:", previous_power)
            drive_timer.reset()
            train_drive(train, previous_power)
        else:
            print("Tanken abgeschlossen (Zug stand vorher bereits).")

    # 5. Grün: Stopp -> In entgegengesetzte Richtung weiterfahren
    elif brick_type == "GREEN":
        print("Aktion: Gruener Brick -> Stopp & Richtungsumkehr")

        # Zug kurz anhalten
        train_drive(train, 0)
        train_play_sound(train, "brake")
        wait(500)

        # Neue Fahrtleistung in Gegenrichtung
        if commanded_power != 0:
            new_power = -commanded_power
        else:
            new_power = -MIN_DRIVE_POWER

        print("Richtungsumkehr: Neue Leistung:", new_power)

        # Steuerrad-Position umkehren
        if motor is not None:
            current_angle = motor.angle()
            target_angle = -current_angle
            target_angle = max(-MAX_DIAL_ANGLE, min(target_angle, MAX_DIAL_ANGLE))
            try:
                # Motorisiertes Drehen des Rades in die Gegenposition (ca. 250ms)
                motor.run_target(300, target_angle, wait=True)
            except Exception as e:
                # Fallback falls von Hand gehalten oder Schwergang
                motor.reset_angle(target_angle)
            m1LastAngle = target_angle
            peak_angle = target_angle

        # Weiterfahrt in entgegengesetzte Richtung
        commanded_power = new_power
        drive_timer.reset()
        train_drive(train, commanded_power)

def angle_to_power(angle):
    """Maps dial angle to train motor power (-100 to 100)."""
    if abs(angle) <= DEADZONE:
        return 0
    sign = 1 if angle > 0 else -1
    ratio = (abs(angle) - DEADZONE) / (MAX_DIAL_ANGLE - DEADZONE)
    power = int(MIN_DRIVE_POWER + ratio * (100 - MIN_DRIVE_POWER))
    return sign * min(power, 100)

def processTrain1(motor, train):
    global m1LastAngle, commanded_power, peak_angle

    if motor is None:
        return

    # 1. Read current angle and clamp to [-MAX_DIAL_ANGLE, MAX_DIAL_ANGLE]
    angle = motor.angle()
    if angle > MAX_DIAL_ANGLE:
        motor.reset_angle(MAX_DIAL_ANGLE)
        angle = MAX_DIAL_ANGLE
    elif angle < -MAX_DIAL_ANGLE:
        motor.reset_angle(-MAX_DIAL_ANGLE)
        angle = -MAX_DIAL_ANGLE

    # 2. Check for active direction reversal:
    # If driving forward, but user turns wheel back by >= REVERSAL_THRESHOLD:
    if commanded_power > 0:
        if angle > peak_angle:
            peak_angle = angle
        elif angle < (peak_angle - REVERSAL_THRESHOLD):
            reset_to_neutral(motor, train, "Richtungsumkehr erkannt -> Sofort-Stopp & Nullstellung")
            return

    # If driving reverse, but user turns wheel forward by >= REVERSAL_THRESHOLD:
    elif commanded_power < 0:
        if angle < peak_angle:
            peak_angle = angle
        elif angle > (peak_angle + REVERSAL_THRESHOLD):
            reset_to_neutral(motor, train, "Richtungsumkehr erkannt -> Sofort-Stopp & Nullstellung")
            return
    else:
        peak_angle = 0

    # 3. Check if dial has moved
    if m1LastAngle is None or abs(angle - m1LastAngle) >= 2:
        new_power = angle_to_power(angle)
        if new_power != commanded_power:
            commanded_power = new_power
            if commanded_power == 0:
                peak_angle = 0
            else:
                drive_timer.reset()
            train_drive(train, commanded_power)
            print("Winkel:", angle, "-> Leistung:", commanded_power)
        m1LastAngle = angle

print("start control loop - bereit zur Steuerung")
while True:
    try:
        # 1. Not-Stopp & Nullstellung per Technic Hub Mitten-Taste
        if Button.CENTER in hub.buttons.pressed():
            reset_to_neutral(m1, train1, "Mitten-Taste gedrueckt: Stopp & Nullstellung")
            wait(300)
            continue

        # 2. Steuerrad-Eingabe SOFORT verarbeiten (immer reaktiv, wird nie durch BLE blockiert)
        if m1 is not None and is_train_connected(train1):
            processTrain1(m1, train1)

        # 3. Automatische Hinderniserkennung ueber nativen Live-Tachosensor (Pybricks v4+)
        if is_native and abs(commanded_power) > 0 and drive_timer.time() > 1000:
            try:
                current_speed = train1.speed()
                if abs(current_speed) <= 2:
                    reset_to_neutral(m1, train1, "Hindernis erkannt (Zug-Tacho meldet Speed=0) -> Stopp & Nullstellung")
                    wait(200)
                    continue
            except Exception as e:
                print("Tacho-Abfrage Fehler:", e)

        # 4. Automatische Hinderniserkennung & Feedback ueber BLE LWP3
        # WICHTIG: Nur abfragen, wenn der Zug aktiv fährt (commanded_power != 0)!
        # Wenn der Zug steht, sendet er keine LWP3-Telegramme und read() könnte blockieren.
        if not is_native and is_train_connected(train1) and abs(commanded_power) > 0 and hasattr(train1, "check_stop_feedback"):
            try:
                if train1.check_stop_feedback():
                    reset_to_neutral(m1, train1, "Hindernis / Hand-Stopp erkannt -> Stopp & Nullstellung")
                    wait(100)
                    continue
            except Exception as e:
                print("check_stop_feedback Fehler:", e)

        # 5. Action Brick Erkennung (Farbsensor an der Unterseite des Zugs)
        # WICHTIG: Erkennung DARF NUR stattfinden, wenn der Zug aktiv fährt!
        if abs(commanded_power) > 0:
            action_brick = None
            if hasattr(train1, "pop_action_brick"):
                action_brick = train1.pop_action_brick()
            elif is_native and hasattr(train1, "color"):
                try:
                    col = train1.color()
                    if col not in (None, Color.NONE):
                        action_brick = col
                except Exception as e:
                    print("train1.color Fehler:", e)

            if action_brick is not None:
                handle_action_brick(action_brick, m1, train1)
                continue
        else:
            # Wenn der Zug steht: Etwaige im Stillstand aufgelaufene Bricks verwerfen
            if hasattr(train1, "clear_action_brick"):
                train1.clear_action_brick()

        # 6. Pruefen ob Fahrt befohlen wurde, Zug aber nach 2.5s noch blockiert ist
        if not is_native and is_train_connected(train1) and abs(commanded_power) > 0 and drive_timer.time() > 2500:
            if hasattr(train1, "is_moving") and not train1.is_moving:
                reset_to_neutral(m1, train1, "Zug blockiert (startet nicht) -> Stopp & Nullstellung")
                wait(200)
                continue

    except Exception as e:
        print("Schleifenfehler:", e)
    wait(50)
from pybricks.hubs import TechnicHub
from pybricks.pupdevices import Motor
#from allow_missing_motors import Motor
from pybricks.parameters import Button, Color, Direction, Port, Side, Stop
from pybricks.robotics import DriveBase
from pybricks.tools import wait, StopWatch, multitask, run_task
from duplo import DuploTrain
from duplo import start_driving, set_light, play_sound

hub = TechnicHub()
watch = StopWatch()
train1 = DuploTrain()
train2 = DuploTrain()
m1 = None
m2 = None
#m1.reset_angle(0)
#m1.run_angle(100, 0)
#m1.reset_angle(0)
#m2.reset_angle(0)
m1LastAngle = None
m2LastAngle = None

def processTrain(motor, train, angle, currentAngle):
    print("angle changed from: ", currentAngle, " to: ", angle)
    if -20 < angle < 20:
        print("stop driving")
        train.stop_driving()
    elif -40 < angle <= -20:
        print("start driving -40")
        train.start_driving(-40)
    elif 20 <= angle < 40:
        print("start driving 40")
        train.start_driving(40)
    else:
        print("start driving ", angle)
        train.start_driving(angle)

def processTrain1(motor, train):
    global m1LastAngle
    if motor is None:
        return
    angle = motor.angle()
    if m1LastAngle is None or m1LastAngle != angle:
        last = m1LastAngle
        m1LastAngle = angle
        processTrain(motor, train, angle, last)

def processTrain2(motor, train):
    global m2LastAngle
    if motor is None:
        return
    angle = motor.angle()
    if m2LastAngle is None or m2LastAngle != angle:
        last = m2LastAngle
        m2LastAngle = angle
        processTrain(motor, train, angle, last)

def connectTrain(train: DuploTrain):
    print("connectTrain: ", train)
    train.connect()

try:
    print("setup motor 1")
    m1 = Motor(Port.A)
    m1.reset_angle(0)
except:
    print("setupMotor 1 failed")
    m1 = None

try:
    print("setup motor 2")
    m2 = Motor(Port.B)
    m2.reset_angle(0)
except:
    print("setupMotor 2 failed")
    m2 = None


#setupMotor(m1, Port.A)
#setupMotor(m2, Port.B)

print("m1: ", m1)
print("m2: ", m2)

def connectTrain1():
    if not train1.isConnected():
        connectTrain(train1)
    else:
        processTrain1(m1, train1)

def connectTrain2():
    if not train2.isConnected():
        connectTrain(train2)
    else:
        processTrain2(m2, train2)

while True:
    try:
        if m1 != None:
            connectTrain1()
        if m2 != None:
            connectTrain2()
    except Exception as e:
        print("ups: ", e)
    print("time: ", watch.time())
    wait(200)
#----------------------------------------------------------#
#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE
# Module:     music.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
# For the CYD globe only, no speaker on the S3DEV  globe
# Toy only
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports

# Project Imports
import speaker

DUTY = 180

# OCTAVE 4
C4  = 262
CS4 = 277   # C# / Db
D4  = 294
DS4 = 311
E4  = 330
F4  = 349
FS4 = 370
G4  = 392
GS4 = 415
A4  = 440
AS4 = 466
B4  = 494

# OCTAVE 5
C5  = 523
CS5 = 554
D5  = 587
DS5 = 622
E5  = 659
F5  = 698
FS5 = 740
G5  = 784
GS5 = 831
A5  = 880
AS5 = 932
B5  = 988

# OCTAVE 6
C6  = 1047
CS6 = 1109
D6  = 1175
DS6 = 1245
E6  = 1319
F6  = 1397
FS6 = 1480
G6  = 1568
A6  = 1760

def welcome_to_my_world():
    # Welcome to my world
    speaker.chirp(E5, 280, DUTY)
    speaker.chirp(D5, 220, DUTY)
    speaker.chirp(C5, 180, DUTY)
    speaker.chirp(B4, 180, DUTY)
    speaker.chirp(A4, 420, DUTY)

    # short breath
    speaker.chirp(A4, 80, 0)

    # Won't you come on in
    speaker.chirp(D5, 240, DUTY)
    speaker.chirp(C5, 200, DUTY)
    speaker.chirp(B4, 180, DUTY)
    speaker.chirp(A4, 180, DUTY)
    speaker.chirp(G4, 480, DUTY)

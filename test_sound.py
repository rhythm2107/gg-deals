import pygame

# Initialize pygame mixer
pygame.mixer.init()

# Path to your sound file
sound_file = "notification_sound.mp3"

try:
    # Load and play the sound
    pygame.mixer.Sound(sound_file).play()

    print("Playing sound. If you don't hear anything, check the following:")
    print("1. Ensure the file exists and is accessible.")
    print("2. Ensure your system sound is on and working.")
    print("3. Ensure your audio drivers are functioning.")

    # Keep the script running for a while to allow the sound to play
    input("Press Enter after listening to the sound...")

except pygame.error as e:
    print(f"Failed to play sound: {e}")

from pymicro_wakeword import MicroWakeWord, MicroWakeWordFeatures, Model
from pymicro_vad import MicroVad

mww = MicroWakeWord.from_builtin(Model.OKAY_NABU) # searches for wakeword
feats = MicroWakeWordFeatures() # converts audio to spectogram
vad = MicroVad() # searches for any voice in sound


def reset():
    mww.reset() # needs to reset those 2 fuckwits to reset their probability
    feats.reset()
